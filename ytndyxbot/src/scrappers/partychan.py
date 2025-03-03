from urllib.parse import urlparse

from ..enums import RequestMethod, RequestReturn
from ..helpers import CookieManager
from ..utils import get_cookie_path, traverse_obj
from ..wrappers import AiohttpSG


class PartychanIE:
    _API_V1 = {
        "coomer.su": "https://coomer.su/api/v1",
        "kemono.su": "https://kemono.su/api/v1",
    }
    _API_DATA = {
        "coomer.su": "https://c5.coomer.su/data",
        "kemono.su": "https://c5.kemono.su/data",
    }
    _VIDEO_EXTS = (
        "avi",
        "divx",
        "flv",
        "m4v",
        "mkv",
        "mov",
        "mp4",
        "mpg",
        "wmv",
        "mts",
        "gif",
    )
    _IMAGE_EXTS = ("jpg", "jpeg", "png", "webp")

    def _get_headers(self, url: str) -> dict:
        return {
            "accept": "*/*",
            "accept-language": "es-419,es;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": url,
            "sec-ch-ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        }

    def _get_headers_video(self, netloc: str) -> dict:
        return {
            "accept": "*/*",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "i",
            "referer": "https://coomer.su/"
            if netloc == "coomer.su"
            else "https://kemono.su/",
            "sec-ch-ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "video",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        }

    def _get_headers_image(self) -> dict:
        return {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "sec-ch-ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        }

    def nearest_multiple_of_50(self, number) -> int:
        return (number // 50) * 50

    async def _get_cookies(self, cookie_path: str, netloc: str) -> dict:
        cookie_manager = CookieManager(cookie_path)
        return await cookie_manager.parse_netscape_cookies(netloc)

    async def profile(
        self,
        profile_url: str,
        limit_id: str = None,
        only_images: bool = False,
        **kwargs,
    ) -> list:
        dct = {}
        index = 0
        stop_search = False
        urlp = urlparse(profile_url)
        cookie_path = await get_cookie_path()
        cookies = await self._get_cookies(cookie_path, urlp.netloc)
        api_v1 = self._API_V1.get(urlp.netloc) + urlp.path

        response = await AiohttpSG.fetch(
            url=api_v1 + "/profile",
            request_method=RequestMethod.GET,
            request_return_type=RequestReturn.JSON,
            cookies=cookies,
            headers=self._get_headers(profile_url),
            raise_for_status=False,
        )
        if response.get("error"):
            raise Exception(response.get("error"))

        response = await AiohttpSG.fetch(
            url=api_v1 + "/posts-legacy",
            request_method=RequestMethod.GET,
            request_return_type=RequestReturn.JSON,
            cookies=cookies,
            headers=self._get_headers(profile_url),
        )
        response2 = await AiohttpSG.fetch(
            url=api_v1 + "/posts-legacy",
            request_method=RequestMethod.GET,
            request_return_type=RequestReturn.JSON,
            params={"o": "50"},
            cookies=cookies,
            headers=self._get_headers(profile_url),
            raise_for_status=False,
        )
        start_index = 0
        num_count = max(
            traverse_obj(response, ("props", "count")),
            traverse_obj(response2, ("props", "count")) or 0,
        )
        end_index = self.nearest_multiple_of_50(num_count)

        api_v1 = self._API_V1.get(urlp.netloc) + urlp.path + "?"
        api_data = self._API_DATA.get(urlp.netloc)
        for o in range(start_index, end_index + 1, 50):
            url = "{0}&o={1}".format(api_v1, o)
            response = await AiohttpSG.fetch(
                url=url,
                request_method=RequestMethod.GET,
                request_return_type=RequestReturn.JSON,
                cookies=cookies,
                headers=self._get_headers(url),
            )

            for post in response:
                images_url = []
                post_id = post.get("id")
                content = post.get("content")
                filepath = traverse_obj(post, ("file", "path"))
                if filepath:
                    file_url = api_data + filepath
                    filename = traverse_obj(post, ("file", "name")).split(".")[0]
                    if filepath.endswith(self._VIDEO_EXTS):
                        if not only_images:
                            dct[index] = {
                                "url": file_url,
                                "params": {
                                    "content": content,
                                    "filename": filename,
                                    "http_headers": self._get_headers_video(
                                        urlp.netloc
                                    ),
                                },
                            }
                        index += 1
                    if filepath.endswith(self._IMAGE_EXTS):
                        images_url.append(
                            {"url": file_url, "http_headers": self._get_headers_image()}
                        )

                attachments = post.get("attachments")
                if attachments:
                    for at in attachments:
                        if filepath == at.get("path"):
                            continue
                        filepath = at.get("path")
                        if filepath:
                            file_url = api_data + filepath
                            filename = at.get("name").split(".")[0]
                            if filepath.endswith(self._VIDEO_EXTS):
                                if not only_images:
                                    dct[index] = {
                                        "url": file_url,
                                        "params": {
                                            "content": content,
                                            "filename": filename,
                                            "http_headers": self._get_headers_video(
                                                urlp.netloc
                                            ),
                                        },
                                    }
                                index += 1
                            if filepath.endswith(self._IMAGE_EXTS):
                                images_url.append(
                                    {
                                        "url": file_url,
                                        "http_headers": self._get_headers_image(),
                                    }
                                )

                if images_url:
                    dct[index] = {"url": "", "params": {"images_url": images_url}}
                    index += 1

                if post_id == limit_id:
                    stop_search = True
                    break

            if stop_search:
                break

        return list(reversed(dct.values()))
