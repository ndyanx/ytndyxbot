import re

from ..enums import RequestMethod, RequestReturn
from ..wrappers import AiohttpSG


class HstreamIE:
    def _get_headers(self) -> dict:
        return {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            #'accept-language': 'es-419,es;q=0.9',
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Microsoft Edge";v="126"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
        }

    async def album(
        self,
        album_url: str,
        limit_id: str = None,
        **kwargs,
    ) -> list:
        text = await AiohttpSG.fetch(
            url=album_url,
            request_method=RequestMethod.GET,
            request_return_type=RequestReturn.TEXT,
            headers=self._get_headers(),
        )
        episodes_url = re.findall(r'<a class="hover:text-blue-600" href="(.*)">', text)
        if not episodes_url:
            raise Exception(f"<b>[HSTREAMMOE]</b> No videos found on {album_url}")

        return [{"url": episode_url} for episode_url in episodes_url]
