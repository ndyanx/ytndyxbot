import aiofiles

from ..enums import RequestMethod, RequestReturn
from ..wrappers import AiohttpSG
from ..utils import traverse_obj


class Camgirlfinder:
    def _get_headers(self) -> dict:
        return {
            "accept": "*/*",
            "accept-language": "es-419,es;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        }

    async def _get_data_predictions(self, predictions: dict) -> list:
        data = []
        for prediction in predictions:
            url_profile = traverse_obj(prediction, ("urls", "externalProfile"))
            url_image = traverse_obj(prediction, ("urls", "fullImage"))
            if not url_profile and not url_image:
                continue
            try:
                url_webcam = await self._get_original_url(url_profile)
            except Exception:
                continue
            data.append(
                {
                    "url_webcam": url_webcam,
                    "url_image": url_image,
                }
            )
        return data

    async def _get_original_url(self, url_profile: str) -> str:
        response = await AiohttpSG.fetch(
            url=url_profile,
            request_method=RequestMethod.GET,
            request_return_type=RequestReturn.RESPONSE,
            raise_for_status=False,
        )
        return str(response.url)

    async def search(self, image_path) -> list | None:
        async with aiofiles.open(image_path, "rb") as image_file:
            data = await image_file.read()
            try:
                response = await AiohttpSG.fetch(
                    "https://api.camgirlfinder.net/search",
                    request_method=RequestMethod.POST,
                    request_return_type=RequestReturn.JSON,
                    data=data,
                    headers=self._get_headers(),
                )
            except Exception:
                return None
        predictions = response.get("predictions")
        if not predictions:
            return None
        return await self._get_data_predictions(predictions)
