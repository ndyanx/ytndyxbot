import json

from .generic import GenericIE

from .common import InfoExtractor
from ..utils import ExtractorError, urlencode_postdata


class PorntnIE(InfoExtractor):
    _VALID_URL = r"https?://porntn\.(?:com)/videos/(?P<id>[0-9]+)/(?P<title>[\w-]+)"
    _MAIN_URL = "https://porntn.com/categories/all-new-hd-porn-videos/"

    def _real_extract(self, url):
        # if not self.get_param('username') and not self.get_param('password'):
        #     raise ExtractorError('Require username and password')
        video_id = self._match_id(url)
        self._download_webpage(self._MAIN_URL, video_id)
        formats = []
        while True:
            try:
                formats = []
                generic_ie = GenericIE(self._downloader)
                generic_ie.set_downloader(self._downloader)
                generic_result = generic_ie.extract(url)
                formats.extend(generic_result)
                break
            except:
                self._download_webpage(
                    "https://porntn.com/login/",
                    video_id,
                    headers={"Referer": self._MAIN_URL},
                )
                self._download_json(
                    "https://porntn.com/login/",
                    video_id,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                        "Referer": self._MAIN_URL,
                        "Sec-Fetch-Mode": "cors",
                    },
                    data=urlencode_postdata(
                        {
                            "username": "maceo1",  # maceo1@vancouvermx.com
                            "pass": "sandrocenturion",
                            "action": "login",
                            "email_link": "https://porntn.com/email/",
                            "format": "json",
                            "mode": "async",
                        }
                    ),
                )

        return {
            "id": video_id,
            **generic_result,
        }
