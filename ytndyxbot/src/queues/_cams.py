import asyncio
import logging
import random
import urllib.parse

from pyrogram import Client
from pyrogram.types import Message
from yt_dlp.utils import traverse_obj

from .. import utils
from ..enums import RequestMethod, RequestReturn, SiteIE
from ..manager import BaseMedia
from ..wrappers import AiohttpSG, CurlCffiSG


logger = logging.getLogger(__name__)


class CamsDownloadQueue:
    _instance = None
    _client = {
        "stripchat.com": AiohttpSG,
        "www.camsoda.com": CurlCffiSG,
        "chaturbate.com": CurlCffiSG,
    }
    _error_map_chaturbate = {
        "offline": "Room is currently offline",
        "private": "Room is currently in a private show",
        "away": "Performer is currently away",
        "password protected": "Room is password protected",
        "hidden": "Hidden session in progress",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CamsDownloadQueue, cls).__new__(cls)
            cls._instance.queue = []
            cls._instance.lives_max = 0
            cls._instance.tuple_live_available = []
            cls._instance.semaphore = asyncio.Semaphore(4)
            cls._instance.active_tasks = set()
        return cls._instance

    def add(self, client: Client, message: Message, url: str) -> None:
        if not any(url == item[2] for item in self.queue):
            self.queue.append([client, message, url])

    def remove(self, url: str) -> None:
        self.queue = [item for item in self.queue if item[2] != url]
        self.active_tasks.discard(url)

    def remove_all(self) -> None:
        self.queue = []
        self.active_tasks.clear()

    def stats_text(self) -> str:
        status = "MODELS:\n"
        status += (
            "".join([f"🔥{url}\n" for _, _, url in self.queue])
            if self.queue
            else "❌\n"
        )
        status += "ACTIVE NOW:\n"
        status += (
            "".join([f"✅{url}\n" for url in self.active_tasks])
            if self.active_tasks
            else "❌"
        )
        return status

    def _get_api(self, netloc) -> dict:
        api = {
            "stripchat.com": "https://stripchat.com/api/front/v2/models/username/{0}/cam",
            "www.camsoda.com": "https://camsoda.com/api/v1/video/vtoken/{0}",
            "chaturbate.com": "https://chaturbate.com/get_edge_hls_url_ajax/",
        }
        return api.get(netloc)

    def _get_params(self, netloc) -> dict:
        params = {
            "www.camsoda.com": {"username": f"guest_{random.randrange(10000, 99999)}"},
        }
        return params.get(netloc)

    def _get_data(self, netloc, basename) -> dict:
        data = {
            "chaturbate.com": {"room_slug": basename},
        }
        return data.get(netloc)

    def _get_headers(self, netloc) -> dict:
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "es-419,es;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Microsoft Edge";v="132"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
        }
        if netloc == "chaturbate.com":
            headers["X-Requested-With"] = "XMLHttpRequest"
        return headers

    def _get_request_task(self, url: str):
        netloc = urllib.parse.urlparse(url).netloc
        basename = utils.url_basename(url)
        return self._client.get(netloc).fetch(
            url=self._get_api(netloc).format(basename),
            request_method=RequestMethod.GET,
            request_return_type=RequestReturn.JSON,
            params=self._get_params(netloc),
            data=self._get_data(netloc, basename),
            headers=self._get_headers(netloc),
            raise_for_status=False,
        )

    async def _get_available_live(self) -> None:
        while True:
            while self.lives_max < 4:
                tasks = []
                cam_model_queue_copy = []

                for client, message, url in self.queue:
                    if url not in self.active_tasks:
                        tasks.append(self._get_request_task(url))
                        cam_model_queue_copy.append((client, message, url))

                if not tasks:
                    await asyncio.sleep(10)
                    continue

                try:
                    responses = await asyncio.gather(*tasks)
                except Exception as e:
                    logger.error(f"Error in requests: {e}")
                    continue

                for response, (client, message, url) in zip(
                    responses, cam_model_queue_copy
                ):
                    if url in self.active_tasks:
                        continue
                    if "stripchat.com" in url:
                        if traverse_obj(response, ("cam", "show", {dict})):
                            continue
                        if not traverse_obj(
                            response, ("user", "user", "isLive", {bool})
                        ):
                            continue
                    if "camsoda.com" in url:
                        if not response:
                            continue
                        if response.get("private_servers"):
                            continue
                        if not response.get("stream_name"):
                            continue
                    if "chaturbate.com" in url:
                        if not response.get("url") and self._error_map_chaturbate.get(
                            response.get("room_status")
                        ):
                            continue

                    self.tuple_live_available.append((client, message, url))
                    self.active_tasks.add(url)
                    self.lives_max += 1

                    if self.lives_max >= 4:
                        break

                await asyncio.sleep(5)

    async def _download_process(
        self, client: Client, message: Message, url: str
    ) -> None:
        try:
            sender_id = (message.from_user or message.chat).id
            process = await self._prepare_process(client, message, sender_id, url)
            async with utils.temp_directory(process.dir_sender) as dmain:
                async with utils.temp_directory(process.dir_sender_temp) as dtemp:
                    async with self.semaphore:
                        dl_data = await process._start_download(
                            url, dmain, dtemp, force_raise=True
                        )
                    self.lives_max -= 1
                    self.active_tasks.discard(url)
                    await process._post_download(dl_data, url)
        except Exception as e:
            self.lives_max -= 1
            self.active_tasks.discard(url)
            logger.error(f"Error in _start_download: {e}")

    async def _prepare_process(
        self, client: Client, message: Message, sender_id: int, url: str
    ) -> BaseMedia:
        process = BaseMedia(client, message, sender_id, SiteIE.ANY_URL, url)
        await process.before_starting()
        await process.check_client()
        return process

    async def start(self) -> None:
        asyncio.create_task(self._get_available_live())
        while True:
            if self.tuple_live_available:
                client, message, url = self.tuple_live_available.pop(0)
                asyncio.create_task(self._download_process(client, message, url))
            await asyncio.sleep(1)
