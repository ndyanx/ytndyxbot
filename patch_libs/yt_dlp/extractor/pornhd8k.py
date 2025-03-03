import hashlib
import random
import string
import time
import urllib.parse

from .common import (
    InfoExtractor,
    traverse_obj,
)


class Pornhd8kIE(InfoExtractor):
    _VALID_URL = r"https?://(?:.+)?(pornhd8k|javfun)\.me/movies/(?P<title>[a-z0-9-]+)"
    _END_HASH = {
        "en8.pornhd8k.me": "98126avrbi6m49vd7shxkn985",
        "en.javfun.me": "9826avrbi6m49vd7shxkn9815",
    }

    def generate_string(self):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

    def _real_extract(self, url):
        key_hash = self.generate_string()
        video_id = key_hash
        urlp = urllib.parse.urlparse(url)
        host = "https://" + urlp.netloc
        webpage = self._download_webpage(url, video_id)
        title = self._og_search_title(webpage) or self._html_extract_title(webpage)
        description = self._og_search_description(webpage)
        video_id = self._html_search_regex(
            r'<input id="uuid" type="hidden" value="(.+?)"/>', webpage, "search uuid"
        )
        str_hash = video_id + key_hash + self._END_HASH.get(urlp.netloc)
        md5_hash = hashlib.md5(str_hash.encode()).hexdigest()
        self._set_cookie(urlp.netloc, "domain-alert", "1")
        self._set_cookie(urlp.netloc, "subscribe", "1")
        self._set_cookie(
            urlp.netloc,
            f"826avrbi6m49vd7shxkn985m{video_id}k06twz87wwxtp3dqiicks2df",
            key_hash,
        )
        info = self._parse_json(
            self._download_webpage(
                f"{host}/ajax/get_sources/{video_id}/{md5_hash}",
                video_id,
                headers={
                    "referer": url,
                    "sec-fetch-mode": "cors",
                    "x-requested-with": "XMLHttpRequest",
                },
                query={
                    "count": "4",
                    "mobile": "false",
                    "t": str(round(time.time())),
                },
                tries=3,
            ).strip(),
            video_id,
        )

        thumbnail = traverse_obj(info, ("playlist", 0, "image"))
        if thumbnail:
            thumbnail = (
                f"{host}{thumbnail}"
                if thumbnail.startswith("/Cms_Data/")
                else thumbnail
            )
            thumbnail = (
                f"https:{thumbnail}" if thumbnail.startswith("//images") else thumbnail
            )
            if not self._is_valid_url(thumbnail, video_id):
                thumbnail = None
        else:
            path = self._search_regex(
                r'<div class="thumb mvic-thumb" style="background-image: url\((.+?)\);"></div>',
                webpage,
                "search thumbnail",
                fatal=False,
            )
            if path:
                thumbnail = host + path
                if not self._is_valid_url(thumbnail, video_id):
                    thumbnail = None

        formats = []
        for source in traverse_obj(info, ("playlist", 0, "sources"), default=[]):
            file_url = source.get("file")
            if file_url.endswith("m3u8"):
                formats.extend(
                    self._extract_m3u8_formats(
                        file_url,
                        video_id,
                        "mp4",
                        m3u8_id=source.get("label"),
                        headers={"origin": host, "referer": url},
                    )
                )
            else:
                formats.append(
                    {
                        "url": file_url,
                        "ext": source.get("type").split("/")[1],
                        "format_id": source.get("label"),
                    }
                )

        return {
            "id": video_id,
            "title": title,
            "description": description,
            "thumbnail": thumbnail,
            "formats": formats,
        }
