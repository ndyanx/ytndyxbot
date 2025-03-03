from ..enums import RequestMethod, RequestReturn
from ..utils import traverse_obj
from ..wrappers import AiohttpSG


class VkIE:
    def get_headers_web(self) -> dict:
        return {
            "accept": "*/*",
            "accept-language": "es-419,es;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://vk.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://vk.com/",
            "sec-ch-ua": '"Not)A;Brand";v="99", "Microsoft Edge";v="127", "Chromium";v="127"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
        }

    async def fetch_vk_data(self, url: str, data: dict) -> dict:
        return await AiohttpSG.fetch(
            url=url,
            request_method=RequestMethod.POST,
            request_return_type=RequestReturn.JSON,
            params={"v": "5.241", "client_id": "6287487"},
            data=data,
            headers=self.get_headers_web(),
        )

    async def profile(self, channel_url: str, limit_id: str = None, **kwargs) -> list:
        token_data = await self.fetch_vk_data(
            "https://login.vk.com/",
            {
                "act": "get_anonym_token",
                "client_secret": "QbYic1K3lEV5kTGiqlq2",
                "client_id": "6287487",
                "scopes": "audio_anonymous,video_anonymous,photos_anonymous,profile_anonymous",
                "version": "1",
                "app_id": "6287487",
            },
        )

        access_token = traverse_obj(token_data, ("data", "access_token"))
        if not access_token:
            raise ValueError("Failed to retrieve access token.")

        initial_data = await self.fetch_vk_data(
            "https://api.vk.com/method/catalog.getVideo",
            {
                "need_blocks": "1",
                "owner_id": "0",
                "url": channel_url,
                "access_token": access_token,
            },
        )

        section_id = traverse_obj(
            initial_data, ("response", "catalog", "default_section")
        )

        videos = {}
        while True:
            section = (
                traverse_obj(initial_data, ("response", "section"))
                or traverse_obj(initial_data, ("response", "catalog", "sections", -1))
                or {}
            )
            videos_ids = traverse_obj(section, ("blocks", -1, "videos_ids")) or []

            for video_id in videos_ids:
                videos[video_id] = {
                    "url": f"https://vk.com/video{video_id}",
                    "params": {},
                }
                if video_id == limit_id:
                    return list(reversed(videos.values()))

            if not section.get("next_from"):
                break

            initial_data = await self.fetch_vk_data(
                "https://api.vk.com/method/catalog.getSection",
                {
                    "section_id": section_id,
                    "start_from": section.get("next_from"),
                    "access_token": access_token,
                },
            )

        return list(reversed(videos.values()))
