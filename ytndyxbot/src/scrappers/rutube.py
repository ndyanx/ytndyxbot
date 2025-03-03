from json import loads
from re import search, sub

from ..enums import RequestMethod, RequestReturn
from ..utils import traverse_obj
from ..wrappers import AiohttpSG


class RutubeIE:
    def get_headers_web_1(self) -> dict:
        return {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "es-419,es;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "sec-ch-ua": '"Not)A;Brand";v="99", "Microsoft Edge";v="127", "Chromium";v="127"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
        }

    def get_headers_web_2(self, channel_url: str) -> dict:
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "es-419,es;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": channel_url,
            "sec-ch-ua": '"Not)A;Brand";v="99", "Microsoft Edge";v="127", "Chromium";v="127"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
            "x-trace-id": "93e24d6f-3359-40d8-8290-8db0e620717b",
        }

    def get_data(self, scripts) -> dict | None:
        for script in scripts:
            match = search(r"window\.reduxState = (.*?);", script.text.strip())
            if match:
                json_string = match.group(1).strip()
                cleaned_json_string = sub(r'\\[^"\\/bfnrtu]', "", json_string)
                return loads(cleaned_json_string)

        return None

    async def profile(self, channel_url: str, limit_id: str = None, **kwargs) -> list:
        path_parts = channel_url.split("/")
        origin_type = "rtb,rst,ifrm,rspa" if path_parts[-2] == "videos" else "rshorts"

        scripts = (
            await AiohttpSG.fetch(
                url=channel_url,
                request_method=RequestMethod.GET,
                request_return_type=RequestReturn.SOUP,
                headers=self.get_headers_web_1(),
            )
        ).find_all("script")

        data = self.get_data(scripts)
        channel_id = (
            traverse_obj(data, ("userChannel", "info", "id"))
            or traverse_obj(
                data,
                (
                    "api",
                    "queries",
                    'channelIdBySlug({"slug":"' + path_parts[-3] + '"})',
                    "data",
                    "channel_id",
                ),
            )
            or traverse_obj(
                data,
                (
                    "api",
                    "queries",
                    'channelInfo({"userChannelId":' + path_parts[-3] + "})",
                    "data",
                    "id",
                ),
            )
        )

        data = await AiohttpSG.fetch(
            url=f"https://rutube.ru/api/video/person/{channel_id}/",
            request_method=RequestMethod.GET,
            request_return_type=RequestReturn.JSON,
            params={"client": "wdp", "origin__type": origin_type, "page": 1},
            headers=self.get_headers_web_2(channel_url),
        )

        videos = {}
        while data.get("results"):
            for result in data["results"]:
                video_id = result["id"]
                videos[video_id] = {"url": result["video_url"], "params": {}}
                if video_id == limit_id:
                    return list(reversed(videos.values())), len(videos)

            if not data.get("has_next"):
                break

            data = await AiohttpSG.fetch(
                url=data["next"],
                request_method=RequestMethod.GET,
                request_return_type=RequestReturn.JSON,
                headers=self.get_headers_web_2(channel_url),
            )

        return list(reversed(videos.values()))
