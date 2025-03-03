import logging

from sys import platform

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession, Response

from ..enums import RequestReturn, RequestMethod

logger = logging.getLogger(__name__)


class SessionManagerCURLCFFI:
    _session = None

    @classmethod
    async def get_session(cls) -> AsyncSession:
        if cls._session is None:
            if platform in ("win32", "cygwin", "cli"):
                cls._session = AsyncSession(impersonate="chrome110", verify=False)
            else:
                cls._session = AsyncSession(impersonate="chrome110")
        return cls._session

    @classmethod
    def close_session(cls) -> None:
        if cls._session:
            try:
                cls._session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
            finally:
                cls._session = None


class CurlCffiSG:
    @classmethod
    async def fetch(
        cls,
        url: str,
        request_method: RequestMethod,
        request_return_type: RequestReturn,
        session: AsyncSession = None,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        cookies: dict = None,
        headers: dict = None,
        raise_for_status: bool = True,
    ) -> dict | str | BeautifulSoup:
        session = session or await SessionManagerCURLCFFI.get_session()
        response = await session.request(
            method=request_method.value,
            url=url,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            headers=headers,
        )

        if raise_for_status:
            response.raise_for_status()

        return cls._process_response(response, request_return_type)

    @staticmethod
    def _process_response(
        response: Response, request_return_type: RequestReturn
    ) -> dict | str | BeautifulSoup | None:
        match request_return_type:
            case RequestReturn.TEXT:
                return response.text
            case RequestReturn.JSON:
                try:
                    return response.json()
                except Exception:
                    return None
            case RequestReturn.SOUP:
                return BeautifulSoup(response.text, "html.parser")
            case RequestReturn.RESPONSE:
                return response
            case _:
                raise ValueError(
                    f"Unsupported request return type: {request_return_type}"
                )
