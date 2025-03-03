import re

from .generic import GenericIE
from .streamtape import StreamtapeIE
from .filemoon import FilemoonIE

from .common import InfoExtractor

from ..utils.networking import std_headers


class InternetChicksIE(InfoExtractor):
    _VALID_URL = r"https?://internetchicks\.com/(?P<title>[a-z0-9-]+)"

    def _real_extract(self, url):
        video_id = "1_internetchicks"  # self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = (
            self._html_extract_title(webpage)
            or self._og_search_title(webpage)
            or self._og_search_description(webpage)
            or self._html_search_meta("description", webpage)
        )
        embeds = re.findall(r"playEmbed\('([^']+)'\);", webpage)
        formats = []
        for embed_url in embeds:
            if "streamtape.com" in embed_url:
                std_headers["Referer"] = url
                streamtape_ie = StreamtapeIE(self._downloader)
                streamtape_ie.set_downloader(self._downloader)
                streamtape_result = streamtape_ie.extract(embed_url)
                formats.extend(streamtape_result["formats"])
            if "vidoza.net" in embed_url:
                std_headers["Referer"] = url
                generic_ie = GenericIE(self._downloader)
                generic_ie.set_downloader(self._downloader)
                generic_result = generic_ie.extract(
                    embed_url.replace("vidoza", "videzz")
                )
                formats.extend(generic_result["formats"])
            if "filemoon.to" in embed_url:
                std_headers["Referer"] = url
                filemoon_ie = FilemoonIE(self._downloader)
                filemoon_ie.set_downloader(self._downloader)
                filemoon_result = filemoon_ie.extract(embed_url)
                formats.extend(filemoon_result["formats"])

        return {
            "id": video_id,
            "title": title,
            "formats": formats,
        }
