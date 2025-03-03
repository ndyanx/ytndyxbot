import warnings

import aiomysql

from typing import Any

from .. import constants
from .. import utils
from ..enums import SenderStatus


warnings.filterwarnings("ignore", module=r"aiomysql")


class MysqlCP:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MysqlCP, cls).__new__(cls)
            cls._instance.pool = None  # cls.new_pool()
        return cls._instance

    async def new_pool(self) -> None:
        if not self.pool:
            self.pool: aiomysql.Pool = await aiomysql.create_pool(
                host=constants.DB_HOST,
                user=constants.DB_USER,
                password=constants.DB_PASSWORD,
                db=constants.DB_NAME,
            )

    async def close_pool(self) -> None:
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

    async def run_query(
        self, query: str, *params: Any, read: bool = False, one: bool = False
    ) -> Any:
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                await conn.commit()
                if read:
                    if one:
                        return await cursor.fetchone()
                    else:
                        return await cursor.fetchall()

    async def prepare_struct(self) -> None:
        query = """
        CREATE PROCEDURE IF NOT EXISTS `CreateTables`()
        BEGIN
            CREATE TABLE IF NOT EXISTS senders (
                sender_id BIGINT,
                date_insert DATETIME DEFAULT current_timestamp(),
                date_update DATETIME DEFAULT current_timestamp() ON UPDATE current_timestamp(),
                PRIMARY KEY (sender_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            CREATE TABLE IF NOT EXISTS activities (
                sender_id BIGINT,
                last_activity INT,
                date_insert DATETIME DEFAULT current_timestamp(),
                date_update DATETIME DEFAULT current_timestamp() ON UPDATE current_timestamp(),
                PRIMARY KEY (sender_id),
                FOREIGN KEY (sender_id) REFERENCES senders(sender_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

            CREATE TABLE IF NOT EXISTS senders_status (
                sender_id BIGINT,
                sender_status BOOLEAN DEFAULT false,
                date_insert DATETIME DEFAULT current_timestamp(),
                date_update DATETIME DEFAULT current_timestamp() ON UPDATE current_timestamp(),
                PRIMARY KEY (sender_id),
                FOREIGN KEY (sender_id) REFERENCES senders(sender_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        END
        """
        await self.run_query(query)
        await self.run_query("CALL CreateTables();")

        queries = [
            """
            CREATE PROCEDURE IF NOT EXISTS `AddSender`(IN _sender_id BIGINT)
            BEGIN
                INSERT IGNORE INTO senders(sender_id) VALUES (_sender_id);
                INSERT IGNORE INTO senders_status(sender_id, sender_status) VALUES (_sender_id, TRUE);
            END
            """,
            """
            CREATE PROCEDURE IF NOT EXISTS `AddSenderLastActivity`(IN _sender_id BIGINT, IN _int_time INT)
            BEGIN
                INSERT INTO activities(sender_id, last_activity) VALUES (_sender_id, _int_time)
                ON DUPLICATE KEY UPDATE last_activity = VALUES(last_activity);
            END
            """,
            """
            CREATE PROCEDURE IF NOT EXISTS `AddSenderStatus`(IN _sender_id BIGINT, IN _sender_status BOOLEAN)
            BEGIN
                INSERT INTO senders_status(sender_id, sender_status) VALUES (_sender_id, _sender_status)
                ON DUPLICATE KEY UPDATE sender_status = VALUES(sender_status);
            END
            """,
            """
            CREATE PROCEDURE IF NOT EXISTS `GetSenderStatus`(IN _sender_id BIGINT)
            BEGIN
                SELECT sender_status FROM senders_status WHERE sender_id = _sender_id;
            END
            """,
            """
            CREATE PROCEDURE IF NOT EXISTS `ResetSenderStatus`(IN _sender_status BOOLEAN)
            BEGIN
                UPDATE senders_status SET sender_status = _sender_status;
            END
            """,
        ]
        for query in queries:
            await self.run_query(query)

        query = """
        CREATE PROCEDURE IF NOT EXISTS `GetSenderStats`(OUT _total INT, OUT _last24h INT, OUT _last7d INT)
        BEGIN
            DECLARE total_local INT;
            DECLARE last24h_local INT;
            DECLARE last7d_local INT;

            SELECT COUNT(DISTINCT sender_id) INTO total_local FROM senders;

            SET @interval24h = UNIX_TIMESTAMP(NOW()) - 60*60*24;
            SELECT COUNT(DISTINCT u.sender_id) INTO last24h_local
            FROM senders u
            JOIN activities a ON u.sender_id = a.sender_id
            WHERE a.last_activity > @interval24h;

            SET @interval7d = UNIX_TIMESTAMP(NOW()) - 60*60*24*7;
            SELECT COUNT(DISTINCT u.sender_id) INTO last7d_local
            FROM senders u
            JOIN activities a ON u.sender_id = a.sender_id
            WHERE a.last_activity > @interval7d;

            SET _total = total_local;
            SET _last24h = last24h_local;
            SET _last7d = last7d_local;
        END
        """
        await self.run_query(query)

    async def add_sender(self, sender_id: int) -> None:
        await self.run_query("CALL AddSender(%s);", sender_id)

    async def update_last_activity_sender(self, sender_id: int, int_time: int) -> None:
        await self.run_query("CALL AddSenderLastActivity(%s, %s);", sender_id, int_time)

    async def update_status_sender(
        self, sender_id: int, sender_status: SenderStatus
    ) -> None:
        await self.run_query(
            "CALL AddSenderStatus(%s, %s);", sender_id, sender_status.value
        )

    async def is_available_sender(self, sender_id: int) -> bool:
        result = await self.run_query(
            "CALL GetSenderStatus(%s);", sender_id, read=True, one=True
        )
        return bool(result[0])

    async def reset_status_sender(self) -> None:
        await self.run_query(
            "CALL ResetSenderStatus(%s);", SenderStatus.AVAILABLE.value
        )

    async def stats_text(self) -> str:
        query = "CALL GetSenderStats(@total, @last24h, @last7d);"
        await self.run_query(query)
        query = "SELECT @total, @last24h, @last7d"
        result = await self.run_query(query, read=True)
        total, last24h, last7d = result[0] if result else (0, 0, 0)
        text = f"<b>Total senders:</b> {utils.sep(total)}\n<b>Last 24 hours:</b> {utils.sep(last24h)}\n<b>Last 7 days:</b> {utils.sep(last7d)}"
        return text
