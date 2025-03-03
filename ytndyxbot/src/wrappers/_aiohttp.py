import logging

import aiohttp

from sys import platform

from bs4 import BeautifulSoup
from ..enums import RequestReturn, RequestMethod


logger = logging.getLogger(__name__)


class SessionManagerAIOHTTP:
    _session = None

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None:
            if platform in ("win32", "cygwin", "cli"):
                cls._session = aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(ssl=False)
                )
            else:
                cls._session = aiohttp.ClientSession()
        return cls._session

    @classmethod
    async def close_session(cls) -> None:
        if cls._session:
            try:
                await cls._session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
            finally:
                cls._session = None


class AiohttpSG:
    @classmethod
    async def fetch(
        cls,
        url: str,
        request_method: RequestMethod,
        request_return_type: RequestReturn,
        session: aiohttp.ClientSession = None,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        cookies: dict = None,
        headers: dict = None,
        raise_for_status: bool = True,
    ) -> dict | str | BeautifulSoup:
        session = session or await SessionManagerAIOHTTP.get_session()
        async with session.request(
            method=request_method.value,
            url=url,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            headers=headers,
            raise_for_status=raise_for_status,
        ) as response:
            return await cls._process_response(response, request_return_type)

    @staticmethod
    async def _process_response(
        response: aiohttp.ClientResponse, request_return_type: RequestReturn
    ) -> dict | str | BeautifulSoup | None:
        match request_return_type:
            case RequestReturn.TEXT:
                return await response.text()
            case RequestReturn.JSON:
                try:
                    return await response.json()
                except Exception:
                    return None
            case RequestReturn.SOUP:
                return BeautifulSoup(await response.text(), "html.parser")
            case RequestReturn.RESPONSE:
                return response
            case _:
                raise ValueError(
                    f"Unsupported request return type: {request_return_type}"
                )
