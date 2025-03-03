import asyncio
import logging

import aiofiles

from json import dumps
from os import path

from ._base import Base
from ..enums import SiteIE, StorageOption
from ..exceptions import CancelledDownload, InvalidPlaylist
from ..helpers import _message
from ..scrappers import (
    BunkrIE,
    HstreamIE,
    PartychanIE,
    RutubeIE,
    VkIE,
    YoutubeIE,
)
from .. import utils


logger = logging.getLogger(__name__)


SITE_FUNCTIONS = {
    SiteIE.RUTUBE_PROFILE: RutubeIE().profile,
    SiteIE.VK_PROFILE: VkIE().profile,
    SiteIE.YOUTUBE_PROFILE: YoutubeIE().profile,
    SiteIE.COOMER_PROFILE: PartychanIE().profile,
    SiteIE.KEMONO_PROFILE: PartychanIE().profile,
    SiteIE.BUNKR_ALBUM: BunkrIE().album,
    SiteIE.HSTREAM_ALBUM: HstreamIE().album,
}


async def get_site_elements(site_ie: SiteIE, url: str, params_scraper: dict) -> list:
    func = SITE_FUNCTIONS.get(site_ie)
    if not func:
        raise ValueError(f"Unsupported site: {site_ie}")
    return await func(url, **params_scraper)


class BaseMedia(Base):
    async def _send_json(self) -> None:
        name = utils.url_to_filename(self.url)
        async with utils.temp_directory(self.dir_sender) as dmain:
            json_path = path.join(dmain, f"{name}.json")
            json_data = dumps({"url": self.url, "result": self._elements}, indent=4)

            async with aiofiles.open(json_path, mode="wb") as f:
                await f.write(json_data.encode())

            await _message.reply_document(self.message, json_path)

    async def _simulation(self) -> None:
        videos = sum(1 for data in self._elements if data.get("url"))
        images = sum(
            len(utils.traverse_obj(data, ("params", "images_url")) or [])
            for data in self._elements
        )

        await _message.reply_text(
            self.message, f"[Simulation]\nVideos: {videos}\nImages: {images}"
        )

    async def _send_videos(self) -> None:
        quantity = len(self._elements)
        await _message.reply_text(
            self.message, f"✅ Getting data from - {quantity} elements."
        )

        for index, data in enumerate(self._elements, 1):
            msg = await _message.reply_text(
                self.message, f"🚀 Downloading item {index} of {quantity}"
            )
            self.dl.params = data.get("params", {})
            await self._process(data.get("url"))
            await msg.delete()

    async def check_client(self) -> None:
        client = await self.client.get_me()

        if self.is_sender_premium:
            self.dl.limit_size = (
                StorageOption.PREMIUM.value
                if client.is_premium
                else StorageOption.FREE.value
            )
        else:
            self.dl.limit_size = StorageOption.LIMIT.value

        self.after_dl.client_name = client.username

    async def _check_filesizes(self, dl_data: dict) -> bool:
        await self.check_client()
        results = await asyncio.gather(
            utils.is_valid_filesize(
                dl_data.get("video_path"), self.dl.limit_size["int"]
            ),
            utils.is_valid_filesize(
                dl_data.get("audio_path"), self.dl.limit_size["int"]
            ),
            utils.is_valid_filesize(
                dl_data.get("thumb_path"), self.dl.limit_size["int"]
            ),
        )
        valid_results = [r for r in results if r is not None]
        return all(valid_results) if valid_results else True

    async def _start_download(
        self, url: str, dmain: str, dtemp: str, force_raise: bool = False
    ) -> dict | None:
        self.dl.sender_path = dmain
        self.dl.sender_temp_path = dtemp
        await self.check_client()

        future_result = await self.dl_queue.add(
            message=self.message,
            priority=self.sender_priority,
            task=self.dl.start(url),
            url=url,
        )
        dl_data = await future_result

        if dl_data.get("error"):
            if force_raise:
                raise Exception(dl_data["error"])
            else:
                await _message.reply_text(self.message, dl_data["error"])
                return None

        return dl_data

    async def _post_download(self, dl_data: dict, url: str) -> None:
        if not await self._check_filesizes(dl_data):
            return

        if dl_data.get("video_path") or dl_data.get("audio_path"):
            future_result = await self.after_dl_queue.add(
                message=self.message,
                priority=self.sender_priority,
                task=self.after_dl.start(**dl_data),
                url=url,
            )
            dl_data |= await future_result

        future_result = await self.sender_media_queue.add(
            priority=self.sender_priority,
            task=_message.send_dl_media(self.message, dl_data),
        )
        await future_result

    async def _process(self, url: str) -> None:
        try:
            async with utils.temp_directory(self.dir_sender) as dmain:
                async with utils.temp_directory(self.dir_sender_temp) as dtemp:
                    dl_data = await self._start_download(url, dmain, dtemp)
                    if dl_data:
                        await self._post_download(dl_data, url)
        except CancelledDownload as e:
            raise CancelledDownload(e)
        except Exception as e:
            logger.error(f"Error in _process: {e}")

    async def before_starting(self) -> None:
        self.sender_priority = utils.get_sender_priority(self.sender_id)
        self.is_sender_premium = not bool(self.sender_priority)
        result = await utils.prepare_paths(self.sender_id)
        self.dir_sender, self.dir_sender_temp = result
        self.dl.cookie_path = await utils.get_cookie_path()
        self.after_dl.font_path = await utils.get_font_path()

    async def start(self) -> None:
        if self.site_ie == SiteIE.ANY_URL:
            return await self._process(self.url)

        if not self.is_sender_premium:
            raise InvalidPlaylist("⚠️ Playlist download disabled for you")

        self._elements = await get_site_elements(
            self.site_ie, self.url, self.params_scraper
        )

        await self._send_json()
        if self.is_simulation:
            await self._simulation()
        else:
            await self._send_videos()
