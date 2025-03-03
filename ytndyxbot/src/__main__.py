import asyncio
import logging

import aiofiles.os

from sys import platform

from pyrogram import Client, filters, idle
from pyrogram.types import Message

from . import commands
from . import config
from . import constants
from . import messages
from .database import BaseDB
from .enums import SiteIE
from .queues import (
    DownloadQueue,
    AfterDownloadQueue,
    SenderMediaQueue,
    CamsDownloadQueue,
)
from .wrappers import (
    SessionManagerAIOHTTP,
    SessionManagerCURLCFFI,
)


if platform in ("win32", "cygwin", "cli"):
    import winloop

    winloop.install()
else:
    import uvloop

    uvloop.install()


def setup_logging() -> logging.Logger:
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(__name__)


logger = setup_logging()


def setup_constants() -> None:
    constants.SESSION_PATH = config.SESSION_PATH
    constants.COOKIES_PATH = config.COOKIES_PATH
    constants.DOWNLOADS_PATH = config.DOWNLOADS_PATH
    constants.DOWNLOADS_TEMP_PATH = config.DOWNLOADS_TEMP_PATH
    constants.FONTS_PATH = config.FONTS_PATH
    constants.SQLITE_DB_PATH = config.SQLITE_DB_PATH
    constants.MYSQL_DB_HOST = config.MYSQL_DB_HOST
    constants.MYSQL_DB_USER = config.MYSQL_DB_USER
    constants.MYSQL_DB_PASSWORD = config.MYSQL_DB_PASSWORD
    constants.MYSQL_DB_NAME = config.MYSQL_DB_NAME
    constants.MAX_INTENT_DL = config.MAX_INTENT_DOWNLOAD


setup_constants()


PATTERNS = [
    (constants.RGX_RUTUBE_PROFILE, SiteIE.RUTUBE_PROFILE),
    (constants.RGX_VK_PROFILE, SiteIE.VK_PROFILE),
    (constants.RGX_YOUTUBE_PROFILE, SiteIE.YOUTUBE_PROFILE),
    (constants.RGX_YOUTUBE_PLAYLIST, SiteIE.YOUTUBE_PLAYLIST),
    (constants.RGX_COOMER_PROFILE, SiteIE.COOMER_PROFILE),
    (constants.RGX_KEMONO_PROFILE, SiteIE.KEMONO_PROFILE),
    (constants.RGX_BUNKR_ALBUM, SiteIE.BUNKR_ALBUM),
    (constants.RGX_HSTREAM_ALBUM, SiteIE.HSTREAM_ALBUM),
]

CUSTOM_FILTER_DL_URLS = (
    filters.me & filters.text & ~filters.channel & filters.regex(r"^https?://")
)


def read_session() -> str | None:
    try:
        with open(constants.SESSION_PATH, mode="r") as f:
            return f.read()
    except FileNotFoundError:
        return None


string_session = read_session()

client = Client(
    name=config.CLIENT_NAME,
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    in_memory=True,
    session_string=string_session,
    phone_number=config.PHONE_NUMBER,
    password=config.PASSWORD,
)


async def start_queues() -> None:
    asyncio.create_task(DownloadQueue().start())
    asyncio.create_task(AfterDownloadQueue().start())
    asyncio.create_task(CamsDownloadQueue().start())
    asyncio.create_task(SenderMediaQueue().start())
    logger.info(
        "Starting DownloadQueue & AfterDownloadQueue & CamsDownloadQueue & SenderMediaQueue"
    )


async def before_serving() -> None:
    await asyncio.gather(
        aiofiles.os.makedirs(constants.DOWNLOADS_PATH, exist_ok=True),
        aiofiles.os.makedirs(constants.DOWNLOADS_TEMP_PATH, exist_ok=True),
        BaseDB().start(),
    )
    logger.info("Creating DOWNLOADS_PATH & DOWNLOADS_TEMP_PATH")
    logger.info("Starting DB")

    await start_queues()


async def after_serving() -> None:
    constants.CLIENT_ID = (await client.get_me()).id
    session_string = await client.export_session_string()
    async with aiofiles.open(constants.SESSION_PATH, mode="wb") as f:
        await f.write(session_string.encode())


def setup_handlers(client) -> None:
    @client.on_message(filters.private & filters.command("start"))
    async def guide(client: Client, message: Message):
        await commands.start(client, message)

    @client.on_message(filters.me & filters.command("stats"))
    async def stats(client: Client, message: Message):
        await commands.stats(client, message)

    @client.on_message(filters.me & filters.command("addmodel"))
    async def add_model(client: Client, message: Message):
        await commands.add_model(client, message)

    @client.on_message(filters.me & filters.command("delmodel"))
    async def del_model(client: Client, message: Message):
        await commands.del_model(client, message)

    @client.on_message(filters.me & filters.command("delallmodels"))
    async def del_all_models(client: Client, message: Message):
        await commands.del_all_models(client, message)

    @client.on_message(filters.me & filters.command("statsmodels"))
    async def status_models(client: Client, message: Message):
        await commands.status_models(client, message)

    @client.on_message(filters.reply & filters.me & filters.command("searchx"))
    async def camgirlfinder_search(client: Client, message: Message):
        await commands.camgirlfinder_search(client, message)

    @client.on_message((filters.me | filters.private) & filters.command("canceldl"))
    async def cancel_tasks(client: Client, message: Message):
        await commands.cancel_tasks(client, message)

    @client.on_message(CUSTOM_FILTER_DL_URLS)
    async def before_processing(client: Client, message: Message):
        await messages.before_processing(client, message)

    @client.on_message(CUSTOM_FILTER_DL_URLS)
    async def process_dl(client: Client, message: Message):
        await messages.process_dl(client, message, PATTERNS)


async def main() -> None:
    await before_serving()
    setup_handlers(client)
    await client.start()
    await after_serving()
    await idle()
    await SessionManagerAIOHTTP.close_session()
    SessionManagerCURLCFFI.close_session()
    await BaseDB().stop()
    await client.stop()


if __name__ == "__main__":
    client.run(main())
