from ..enums import RequestMethod, RequestReturn
from ..wrappers import AiohttpSG

from ..utils import url_basename


class BunkrIE:
    async def album(
        self,
        album_url: str,
        limit_id: str = None,
        solo_images: bool = False,
        **kwargs,
    ) -> list:
        dct = {}
        all_a = (
            await AiohttpSG.fetch(
                url=album_url,
                request_method=RequestMethod.GET,
                request_return_type=RequestReturn.SOUP,
            )
        ).find_all("a", {"aria-label": "download"})

        for a in all_a:
            post_url = a["href"]
            if not any(part in post_url for part in ("/v/", "/i/")):
                continue
            if "/v/" in post_url and solo_images:
                continue
            post_id = url_basename(post_url)
            dct[post_id] = {"url": post_url, "params": {}}
            if post_id == limit_id:
                break

        return list(reversed(dct.values()))
