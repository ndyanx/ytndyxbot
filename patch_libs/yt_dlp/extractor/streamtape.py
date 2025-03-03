import re

from .common import InfoExtractor


class StreamtapeIE(InfoExtractor):
    _VALID_URL = r"https?://streamtape\.com/e/(?P<id>[a-zA-Z0-9-]+)"

    def _real_extract(self, url):
        video_id = "1_streamtape"
        formats = []
        while True:
            try:
                webpage = self._download_webpage(url, video_id)
                result = re.findall(r"\('([^']+)'\)", webpage)
                embeds = list(filter(lambda x: "get_video" in x, result))
                formats = [
                    {
                        "url": "https://watchadsontape.com/get_video?"
                        + embeds[0].split("get_video?")[-1],
                        "ext": "mp4",
                    }
                ]
                break
            except:
                pass

        return {
            "id": video_id,
            "formats": formats,
            "http_headers": {"Referer": url},
        }
