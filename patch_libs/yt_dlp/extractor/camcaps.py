import jsbeautifier.unpackers.packer as packer

from .common import InfoExtractor
from ..utils import ExtractorError


class CamcapsIE(InfoExtractor):
    _VALID_URL = (
        r"https?://(?:www\.)?camcaps\.(.+)/video/(?P<id>[0-9]+)/?(?P<title>[a-z0-9-]+)"
    )
    _HTTP_HEADERS = {"Origin": "https://vidello.net", "Referer": "https://vidello.net/"}

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._og_search_title(webpage) or self._html_extract_title(webpage)
        description = self._og_search_description(webpage)

        # Extract iframe URL
        iframe_url = self._html_search_regex(
            r'<iframe width="100%" height="100%" src="(.+?)"', webpage, "IFRAME URL"
        )
        webpage = self._download_webpage(iframe_url, video_id, headers={"referer": url})

        # Search and unpack JavaScript code
        some_packed_code = self._html_search_regex(
            r"<script type='text/javascript'>eval\((.+?)\)\n</script>",
            webpage,
            "JS CODE",
            fatal=False,
        )
        if not some_packed_code:
            new_iframe_url = self._html_search_regex(
                r'<iframe width="100%" height="100%" src="(.+?)"',
                webpage,
                "NEW IFRAME URL",
            )
            if new_iframe_url:
                raise ExtractorError("Video unavailable")

        unpacked_code = packer.unpack(some_packed_code)

        # Extract m3u8 URL
        m3u8_url = self._search_regex(r'src:"(.+?)",type', unpacked_code, "search m3u8")
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, "mp4", m3u8_id="hls", headers=self._HTTP_HEADERS
        )

        # Extract thumbnails
        thumbnails = []
        thumb1 = self._search_regex(
            r";player\.spriteThumbnails\({url:'(.+?)',width",
            unpacked_code,
            "search thumbnail",
            fatal=False,
        )
        thumb2 = self._search_regex(
            r'poster:"(.+?)",controlBar', unpacked_code, "search thumbnail", fatal=False
        )
        if not thumb1 and not thumb2:
            thumbnails = None
        else:
            for thumb in [thumb1, thumb2]:
                if self._is_valid_url(thumb, video_id, "thumbnail"):
                    thumbnails.append({"url": thumb})

        return {
            "id": video_id,
            "title": title,
            "description": description,
            "thumbnails": thumbnails,
            "formats": formats,
            "http_headers": self._HTTP_HEADERS,
        }
