import json

from .common import InfoExtractor
from ..utils import (
    url_basename,
    traverse_obj,
)


class BunkrIE(InfoExtractor):
    _VALID_URL = (
        r"https://bunkr?([0-9a-z]+)\.(?P<ext>[0-9A-Za-z-]+)/[vfi]/(?P<id>[\w\W-]+)"
    )

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._html_extract_title(webpage)
        thumbnail = self._search_regex(
            r'var videoCoverUrl = "(.*)";', webpage, "thumbnail", fatal=False
        )
        response = self._download_json(
            "https://bunkr.site/api/cached_url",
            video_id,
            "API GIMMEURL",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"slug": url_basename(url)}).encode(),
        )
        new_url = traverse_obj(response, ("data", "newUrl"))
        formats = [
            {
                "url": new_url,
                "format_id": "original",
                "format_note": "Original",
            }
        ]

        return {
            "id": video_id,
            "title": title,
            "formats": formats,
            "thumbnail": thumbnail.replace("\\", "") if thumbnail else None,
            "http_headers": {"Referer": url},
        }
