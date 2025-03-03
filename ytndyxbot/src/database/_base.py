from ._mysql import MysqlCP
from ._sqlite import SQLiteCP

from ..enums import SenderStatus


class BaseDB:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BaseDB, cls).__new__(cls)
        return cls._instance

    async def start(self) -> None:
        try:
            self._client = MysqlCP()
            await self._client.new_pool()
        except Exception:
            self._client = SQLiteCP()
            await self._client.new_connection()
        await self._client.prepare_struct()
        await self._client.reset_status_sender()

    async def stop(self) -> None:
        if isinstance(self._client, MysqlCP):
            await self._client.close_pool()
        else:
            await self._client.close_connection()

    async def prepare_struct(self) -> None:
        await self._client.prepare_struct()

    async def add_sender(self, sender_id: int) -> None:
        await self._client.add_sender(sender_id)

    async def update_last_activity_sender(self, sender_id: int, int_time: int) -> None:
        await self._client.update_last_activity_sender(sender_id, int_time)

    async def update_status_sender(
        self, sender_id: int, sender_status: SenderStatus
    ) -> None:
        await self._client.update_status_sender(sender_id, sender_status)

    async def is_available_sender(self, sender_id: int) -> bool:
        return await self._client.is_available_sender(sender_id)

    async def reset_status_sender(self) -> None:
        await self._client.reset_status_sender()

    async def stats_text(self) -> str:
        return await self._client.stats_text()
