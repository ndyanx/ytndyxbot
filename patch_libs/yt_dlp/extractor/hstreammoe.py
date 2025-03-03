import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    try_get,
)


class HstreammoeIE(InfoExtractor):
    _VALID_URL = r"https?://hstream\.moe/hentai/(?P<id>[a-z0-9-]+)"
    _DOMAIN = "https://hstream.moe"
    _RESOLUTIONS = {
        "2160": (3840, 2160),
        "1080i": (1920, 1080),
        "1080": (1920, 1080),
        "720": (1280, 720),
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_id = self._search_regex(
            r'<input id="e_id" type="hidden" value="(.*)" />', webpage, "episode_id"
        )
        description = self._html_search_meta(
            ["description", "og:description"], webpage, "description", default=None
        )

        xsrf_token = self._get_cookies(self._DOMAIN).get("XSRF-TOKEN")
        if not xsrf_token:
            raise ExtractorError("XSRF-TOKEN Not found.")

        json_data = self._download_json(
            "https://hstream.moe/player/api",
            video_id,
            "Downloading PLAYER API",
            data=json.dumps({"episode_id": video_id}).encode("utf8"),
            headers={
                "content-type": "application/json",
                "origin": self._DOMAIN,
                "referer": url,
                "x-requested-with": "XMLHttpRequest",
                "x-xsrf-token": xsrf_token.value.replace("%3D", "="),
            },
        )

        title = try_get(json_data, lambda x: x["title"], str) or video_id
        thumbnail = self._DOMAIN + try_get(json_data, lambda x: x["poster"], str)
        if not thumbnail.endswith(".webp"):
            self._html_search_meta("og:image", webpage, "thumbnail", default=None)
        stream_url = try_get(json_data, lambda x: x["stream_url"], str)
        stream_domains = try_get(json_data, lambda x: x["stream_domains"], list)
        extra_subtitles = try_get(json_data, lambda x: x["extra_subtitles"], dict)

        if not stream_domains:
            raise ExtractorError("No stream domains available.")

        formats = []

        for res_key, res_value in self._RESOLUTIONS.items():
            for domain in stream_domains:
                manifest_url = f"{domain}/{stream_url}/{res_key}/manifest.mpd"
                if self._is_valid_url(manifest_url, video_id, ".MPD"):
                    mpd_formats = self._extract_mpd_formats(
                        manifest_url, video_id, mpd_id="dash", fatal=False
                    )
                    width, height = res_value
                    for f in mpd_formats:
                        f["width"] = width
                        f["height"] = height
                    formats.extend(mpd_formats)
                    break

        if not formats:
            raise ExtractorError("No video formats available.")

        for domain in stream_domains:
            url = f"{domain}/{stream_url}/eng.ass"
            if self._is_valid_url(manifest_url, video_id, ".ASS English"):
                subtitles = {"en": [{"url": url}]}
                break

        if extra_subtitles:
            for lang_code, lang_name in extra_subtitles.items():
                for domain in stream_domains:
                    lang_url = f"{domain}/{stream_url}/autotrans/{lang_code}.ass"
                    if self._is_valid_url(lang_url, video_id, f".ASS {lang_name}"):
                        subtitles.setdefault(lang_code.lower(), []).append(
                            {"url": lang_url}
                        )
                        break

        return {
            "id": video_id,
            "title": title,
            "description": description,
            "thumbnail": thumbnail,
            "formats": formats,
            "subtitles": subtitles,
        }
