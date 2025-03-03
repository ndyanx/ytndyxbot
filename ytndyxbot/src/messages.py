import logging
import time
import traceback

from re import search

from pyrogram import Client
from pyrogram.types import Message

from . import utils
from .cache import cancel_cache
from .database import BaseDB
from .enums import SiteIE, SenderStatus
from .helpers import _message
from .manager import BaseMedia


logger = logging.getLogger(__name__)


async def send_message(client: Client, message: Message, text: str) -> None:
    try:
        chat_id = message.from_user.id if message.from_user else message.chat.id
        if utils.is_client_message(message):
            chat_id = "me"
        await client.send_message(chat_id=chat_id, text=text)
    except Exception:
        await client.send_message(chat_id=message.chat.id, text=text)


async def before_processing(client: Client, message: Message) -> None:
    sender_id = (message.from_user or message.chat).id
    await BaseDB().add_sender(sender_id)
    await BaseDB().update_last_activity_sender(
        sender_id, int(time.mktime(message.date.timetuple()))
    )

    if not await BaseDB().is_available_sender(sender_id):
        await send_message(
            client, message, "⚠️ Please wait while we are processing your request..."
        )
        return await message.stop_propagation()

    await message.continue_propagation()


async def update_sender_status(sender_id: int, status: SenderStatus) -> None:
    await BaseDB().update_status_sender(sender_id, status)


async def _process_dl(client: Client, message: Message, site_ie: SiteIE) -> None:
    sender_id = (message.from_user or message.chat).id
    try:
        await update_sender_status(sender_id, SenderStatus.NOT_AVAILABLE)
        process = BaseMedia(client, message, sender_id, site_ie)
        await process.before_starting()
        await process.start()
    except Exception as e:
        logger.error(f"Error in _process_dl: {e}\n{traceback.format_exc()}")
        await _message.reply_text(message, str(e))
    finally:
        await update_sender_status(sender_id, SenderStatus.AVAILABLE)


async def process_dl(client: Client, message: Message, patterns: list) -> None:
    sender_id = str((message.from_user or message.chat).id)
    cancel_cache.setdefault(sender_id, {"state": False})

    msg = message.text.strip()
    for pattern, site in patterns:
        if search(pattern, msg):
            return await _process_dl(client, message, site)

    await _process_dl(client, message, SiteIE.ANY_URL)
