import warnings

import aiosqlite

from typing import Any

from .. import constants
from .. import utils
from ..enums import SenderStatus


warnings.filterwarnings("ignore", module=r"aiosqlite")


class SQLiteCP:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SQLiteCP, cls).__new__(cls)
            cls._instance.db = None
        return cls._instance

    async def new_connection(self) -> None:
        if not self.db:
            self.db = await aiosqlite.connect(constants.SQLITE_DB_PATH)

    async def close_connection(self) -> None:
        if self.db:
            await self.db.close()
            self.db = None

    async def run_query(
        self, query: str, params: tuple = (), read: bool = False, one: bool = False
    ) -> Any:
        async with self.db.execute(query, params) as cursor:
            if read:
                if one:
                    return await cursor.fetchone()
                return await cursor.fetchall()
            await self.db.commit()

    async def prepare_struct(self) -> None:
        queries = [
            """
            CREATE TABLE IF NOT EXISTS senders (
                sender_id INTEGER PRIMARY KEY,
                date_insert DATETIME DEFAULT CURRENT_TIMESTAMP,
                date_update DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS activities (
                sender_id INTEGER,
                last_activity INTEGER,
                date_insert DATETIME DEFAULT CURRENT_TIMESTAMP,
                date_update DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (sender_id),
                FOREIGN KEY (sender_id) REFERENCES senders(sender_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS senders_status (
                sender_id INTEGER,
                sender_status BOOLEAN DEFAULT false,
                date_insert DATETIME DEFAULT CURRENT_TIMESTAMP,
                date_update DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (sender_id),
                FOREIGN KEY (sender_id) REFERENCES senders(sender_id)
            );
            """,
        ]

        for query in queries:
            await self.run_query(query)

    async def add_sender(self, sender_id: int) -> None:
        await self.run_query(
            "INSERT OR IGNORE INTO senders(sender_id) VALUES (?);", (sender_id,)
        )
        await self.run_query(
            "INSERT OR IGNORE INTO senders_status(sender_id, sender_status) VALUES (?, TRUE);",
            (sender_id,),
        )

    async def update_last_activity_sender(self, sender_id: int, int_time: int) -> None:
        await self.run_query(
            "INSERT INTO activities(sender_id, last_activity) VALUES (?, ?) ON CONFLICT(sender_id) DO UPDATE SET last_activity = ?;",
            (sender_id, int_time, int_time),
        )

    async def update_status_sender(
        self, sender_id: int, sender_status: SenderStatus
    ) -> None:
        await self.run_query(
            "INSERT INTO senders_status(sender_id, sender_status) VALUES (?, ?) ON CONFLICT(sender_id) DO UPDATE SET sender_status = ?;",
            (sender_id, sender_status.value, sender_status.value),
        )

    async def is_available_sender(self, sender_id: int) -> bool:
        result = await self.run_query(
            "SELECT sender_status FROM senders_status WHERE sender_id = ?;",
            (sender_id,),
            read=True,
            one=True,
        )
        return bool(result[0])

    async def reset_status_sender(self) -> None:
        await self.run_query(
            "UPDATE senders_status SET sender_status = ?;",
            (SenderStatus.AVAILABLE.value,),
        )

    async def stats_text(self) -> str:
        total = await self.run_query(
            "SELECT COUNT(DISTINCT sender_id) FROM senders;", read=True
        )

        last24h = await self.run_query(
            'SELECT COUNT(DISTINCT u.sender_id) FROM senders u JOIN activities a ON u.sender_id = a.sender_id WHERE a.last_activity > datetime("now", "-24 hours");',
            read=True,
        )

        last7d = await self.run_query(
            'SELECT COUNT(DISTINCT u.sender_id) FROM senders u JOIN activities a ON u.sender_id = a.sender_id WHERE a.last_activity > datetime("now", "-7 days");',
            read=True,
        )

        text = (
            f"<b>Total senders:</b> {utils.sep(total[0][0])}\n"
            f"<b>Last 24 hours:</b> {utils.sep(last24h[0][0])}\n"
            f"<b>Last 7 days:</b> {utils.sep(last7d[0][0])}"
        )
        return text
