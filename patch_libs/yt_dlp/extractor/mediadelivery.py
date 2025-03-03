import re
import requests

from hashlib import md5
from random import random
from urllib.parse import urlparse

from .common import InfoExtractor
from .generic import GenericIE
from ..utils import ExtractorError
from ..utils.networking import std_headers


class MediaDeliveryIE(InfoExtractor):
    _VALID_URL = r"https://iframe\.mediadelivery\.net/(embed|play)/(?P<id>[0-9A-Za-z-]+)/(?P<id_path>[0-9A-Za-z-]+)"
    _RESOLUTION = {
        "2160p": (3840, 2160),
        "1080p": (1920, 1080),
        "720p": (1280, 720),
        "480p": (842, 480),
        "360p": (640, 360),
        "240p": (352, 240),
    }
    user_agent = {
        "sec-ch-ua": '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
    }
    session = requests.session()
    session.headers.update(user_agent)

    def start(self, referer="https://127.0.0.1/", embed_url=""):
        self.referer = referer if referer else None
        self.embed_url = embed_url if embed_url else None
        self.guid = urlparse(embed_url).path.split("/")[-1]
        self.headers = {
            "embed": {
                "authority": "iframe.mediadelivery.net",
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "referer": referer,
                "sec-fetch-dest": "iframe",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "cross-site",
                "upgrade-insecure-requests": "1",
            },
            "ping|activate": {
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "origin": "https://iframe.mediadelivery.net",
                "pragma": "no-cache",
                "referer": "https://iframe.mediadelivery.net/",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
            },
            "playlist": {
                "authority": "iframe.mediadelivery.net",
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "referer": embed_url,
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
            },
        }
        embed_response = self.session.get(embed_url, headers=self.headers["embed"])
        embed_page = embed_response.text

        try:
            self.server_id = re.search(
                r"https://video-(.*?)\.mediadelivery\.net", embed_page
            ).group(1)
        except AttributeError as e:
            raise ExtractorError(e)
        self.headers["ping|activate"].update(
            {"authority": f"video-{self.server_id}.mediadelivery.net"}
        )
        search = re.search(r'contextId=(.*?)&secret=(.*?)"', embed_page)
        self.context_id, self.secret = search.group(1), search.group(2)

    def prepare_dl(self) -> list:
        def ping(time: int, paused: str, res: str):
            md5_hash = md5(
                f"{self.secret}_{self.context_id}_{time}_{paused}_{res}".encode("utf8")
            ).hexdigest()
            params = {
                "hash": md5_hash,
                "time": time,
                "paused": paused,
                "chosen_res": res,
            }
            self.session.get(
                f"https://video-{self.server_id}.mediadelivery.net/.drm/{self.context_id}/ping",
                params=params,
                headers=self.headers["ping|activate"],
            )

        def activate():
            self.session.get(
                f"https://video-{self.server_id}.mediadelivery.net/.drm/{self.context_id}/activate",
                headers=self.headers["ping|activate"],
            )

        def main_playlist():
            params = {"contextId": self.context_id, "secret": self.secret}
            response = self.session.get(
                f"https://iframe.mediadelivery.net/{self.guid}/playlist.drm",
                params=params,
                headers=self.headers["playlist"],
            )
            resolutions = re.findall(r"\s*(.*?)\s*/video\.drm", response.text)[::-1]
            if not resolutions:
                raise ExtractorError("Resolutions unavailable")
            else:
                return resolutions

        def video_playlist(resolution):
            params = {"contextId": self.context_id}
            self.session.get(
                f"https://iframe.mediadelivery.net/{self.guid}/{resolution}/video.drm",
                params=params,
                headers=self.headers["playlist"],
            )

        ping(time=0, paused="true", res="0")
        activate()
        resolutions = main_playlist()
        for resolution in resolutions:
            video_playlist(resolution)
            for i in range(0, 29, 4):  # first 28 seconds, arbitrary (check issue#11)
                ping(
                    time=i + round(random(), 6),
                    paused="false",
                    res=resolution.split("x")[-1],
                )
        self.session.close()
        return resolutions

    def get_data(self):
        resolutions = self.prepare_dl()
        urls = [
            f"https://iframe.mediadelivery.net/{self.guid}/{resolution}/video.drm?contextId={self.context_id}"
            for resolution in resolutions
        ]
        http_headers = {
            "Referer": self.embed_url,
            "User-Agent": self.user_agent["user-agent"],
        }
        return resolutions, urls, http_headers

    def _real_extract(self, url):
        video_id = self._match_id(url)
        if "/play/" in url:
            url = url.replace("/play/", "/embed/")
        webpage = self._download_webpage(url, video_id)
        title = self._og_search_title(webpage) or self._html_extract_title(webpage)
        secure_url = self._og_search_property("video:secure_url", webpage)
        ext = ""
        if secure_url:
            if "/embed/" in secure_url:
                ext = title.split(".")[-1]
            else:
                ext = secure_url.split(".")[-1]
        thumbnail = (
            self._og_search_property("image", webpage)
            or self._og_search_property("image:secure_url", webpage)
            or self._html_search_meta("twitter:image", webpage)
        )
        formats = []
        try:
            self.start(referer="https://patreon.com", embed_url=url)
            resolutions, urls, http_headers = self.get_data()
            for index, url in enumerate(urls):
                m3u8_formats = self._extract_m3u8_formats(
                    url, video_id, ext, m3u8_id=resolutions[index], headers=http_headers
                )
                for format in m3u8_formats:
                    if self._RESOLUTION.get(resolutions[index]):
                        format["width"], format["height"] = self._RESOLUTION.get(
                            resolutions[index]
                        )
                    else:
                        width, height = map(int, resolutions[index].split("x"))
                        format["width"], format["height"] = (width, height)
                formats.extend(m3u8_formats)
            return {
                "id": video_id,
                "title": title,
                "formats": formats,
                "http_headers": http_headers,
                "thumbnail": thumbnail,
            }
        except:
            std_headers["Referer"] = "https://patreon.com"
            generic_ie = GenericIE(self._downloader)
            generic_ie.set_downloader(self._downloader)
            generic_result = generic_ie.extract(url)
            return {
                "id": video_id,
                "title": title,
                "formats": generic_result["formats"],
                "thumbnail": generic_result.get("thumbnail"),
            }
