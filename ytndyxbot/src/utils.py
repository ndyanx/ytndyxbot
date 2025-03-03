import asyncio
import urllib.parse

import aiofiles.os
import validators

from contextlib import asynccontextmanager
from os import path
from re import search

# from aioshutil import rmtree
from aiopath import AsyncPath
from pyrogram.types import Message

from . import constants


def sep(num, none_is_zero=False) -> str:
    if num is None:
        return 0 if none_is_zero is True else None
    return "{:,}".format(num)


def traverse_obj(obj, keys):
    try:
        for key in keys:
            obj = obj[key]
        return obj
    except (KeyError, IndexError, TypeError):
        return None


def split_list_groups(listx, rangex):
    for i in range(0, len(listx), rangex):
        yield listx[i : i + rangex]


def is_valid_url(url: str):
    validators.url(url)


def extract_value(text: str, key: str) -> str | None:
    xsearch = search(f"(.*){key}:(.*)", text)
    return xsearch.group(2).split()[0].strip() if xsearch else None


def url_basename(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    return path.strip("/").split("/")[-1]


def url_to_filename(url: str) -> str:
    url_list = list(urllib.parse.urlparse(url))
    return "".join([x.replace("/", "-") for x in url_list[1:]])


def is_client_message(message: Message) -> bool:
    return message.from_user and constants.CLIENT_ID == message.from_user.id


def get_valid_qualitys() -> list:
    return ["1440", "1080", "720", "480", "360", "240"]


def get_max_intent_dl() -> int:
    return constants.MAX_INTENT_DL


def get_sender_priority(sender_id: str) -> int:
    return 0 if sender_id == str(constants.CLIENT_ID) else 1


@asynccontextmanager
async def temp_directory(base_dir: str):
    temp_dir = await aiofiles.tempfile.TemporaryDirectory(dir=base_dir)
    try:
        yield temp_dir.name
    finally:
        asyncio.create_task(clear_folder(temp_dir.name, delete_folder=True))


async def search_dict(partial: dict, search_key: str):
    stack = [partial]
    while stack:
        current_item = stack.pop(0)
        if isinstance(current_item, dict):
            for key, value in current_item.items():
                if key == search_key:
                    yield value
                else:
                    stack.append(value)
        elif isinstance(current_item, list):
            for value in current_item:
                stack.append(value)


async def prepare_paths(sender_id: str) -> tuple:
    dir_sender = path.join(constants.DOWNLOADS_PATH, sender_id)
    dir_sender_temp = path.join(constants.DOWNLOADS_TEMP_PATH, sender_id)
    await aiofiles.os.makedirs(dir_sender, exist_ok=True)
    await aiofiles.os.makedirs(dir_sender_temp, exist_ok=True)
    return dir_sender, dir_sender_temp


async def get_font_path() -> str | None:
    all_files = await aiofiles.os.listdir(constants.FONTS_PATH)
    ttf_files = [file for file in all_files if file.endswith(".ttf")]
    font_path = path.join(constants.FONTS_PATH, ttf_files[0]) if ttf_files else None
    return font_path


async def get_cookie_path() -> str | None:
    all_files = await aiofiles.os.listdir(constants.COOKIES_PATH)
    txt_files = [file for file in all_files if file.endswith(".txt")]
    cookie_path = path.join(constants.COOKIES_PATH, txt_files[0]) if txt_files else None
    return cookie_path


async def is_valid_filesize(file_path: str, limit_size: int) -> bool | None:
    if not file_path:
        return None
    file_size = await aiofiles.os.stat(file_path)
    return file_size.st_size <= limit_size


async def clear_folder(
    folder_path: str, retries: int = 1, delete_folder: bool = False
) -> None:
    if not await aiofiles.os.path.exists(folder_path):
        return
    intent = 0
    exists_nfs_files = False
    while True:
        try:
            # await rmtree(folder_path)
            temp_path = AsyncPath(folder_path)
            files = temp_path.rglob("*")
            async for file in files:
                file_path = file.as_posix()
                if await file.is_dir():
                    dir_content = await aiofiles.os.listdir(file_path)
                    if not dir_content:
                        await aiofiles.os.rmdir(file_path)
                    continue
                if ".nfs" in file_path:
                    exists_nfs_files = True
                    continue
                await aiofiles.os.remove(file_path)
            if delete_folder and not exists_nfs_files:
                await aiofiles.os.rmdir(folder_path)
            break
        except PermissionError:
            await asyncio.sleep(5)
            continue
        except Exception:
            if intent <= retries:
                intent += 1
                await asyncio.sleep(10)
