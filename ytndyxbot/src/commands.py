from re import search

from pyrogram import Client
from pyrogram.types import Message

from . import constants
from . import utils
from .cache import cancel_cache
from .database import BaseDB
from .helpers import _message
from .queues import CamsDownloadQueue
from .scrappers import Camgirlfinder


async def start(client: Client, message: Message) -> None:
    await _message.reply_text(message, constants.WELCOME_MESSAGE)


async def stats(client: Client, message: Message) -> None:
    await _message.reply_text(message, await BaseDB().stats_text())


async def extract_url(message: Message) -> str | None:
    try:
        url = utils.extract_value(message.text, "url")
        utils.is_valid_url(url)
        if any(search(pattern, url) for pattern in constants.SITES_LIVE):
            return url
        await _message.reply_text(
            message, "This site is not available for downloading cam models"
        )
    except Exception as e:
        await _message.reply_text(message, str(e))
    return None


async def handle_model_action(client: Client, message: Message, action: str) -> None:
    if action == "remove_all":
        return CamsDownloadQueue().remove_all()
    elif action == "status":
        return await _message.reply_text(message, CamsDownloadQueue().stats_text())

    url = await extract_url(message)
    if not url:
        return

    if action == "add":
        CamsDownloadQueue().add(client, message, url)
    elif action == "remove":
        CamsDownloadQueue().remove(url)


async def add_model(client: Client, message: Message) -> None:
    await handle_model_action(client, message, "add")


async def del_model(client: Client, message: Message) -> None:
    await handle_model_action(client, message, "remove")


async def del_all_models(client: Client, message: Message) -> None:
    await handle_model_action(client, message, "remove_all")


async def status_models(client: Client, message: Message) -> None:
    await handle_model_action(client, message, "status")


async def camgirlfinder_search(client: Client, message: Message) -> None:
    msg_guide = await _message.reply_text(message, "🚀 Searching...")
    sender_id = str(message.from_user.id)
    dir_sender, _ = await utils.prepare_paths(sender_id)
    async with utils.temp_directory(dir_sender) as dmain:
        photo_path = await _message.download(message.reply_to_message, dmain)
        data = await Camgirlfinder().search(photo_path)

    if not data:
        await _message.reply_text(message, "No results found")
        return await msg_guide.delete()

    await _message.edit_text(msg_guide, "🚀 Sending results...")
    for profile in data:
        try:
            await _message.reply_photo(
                message, photo=profile["url_image"], caption=profile["url_webcam"]
            )
        except Exception:
            await _message.reply_text(message, profile["url_webcam"])
    await msg_guide.delete()


async def cancel_tasks(client: Client, message: Message) -> None:
    sender_id = str((message.from_user or message.chat).id)
    if sender_id in cancel_cache and not cancel_cache[sender_id]["state"]:
        cancel_cache[sender_id]["state"] = True
    else:
        await _message.reply_text(
            message, "<b>No pending tasks were found to cancel.</b>"
        )
