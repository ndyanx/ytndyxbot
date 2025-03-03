import logging

from asyncio import sleep

from pyrogram.enums import ParseMode
from pyrogram.enums import ChatAction
from pyrogram.errors import BadRequest, FloodWait
from pyrogram.types import InputMediaPhoto, InputMediaVideo, Message

from ..utils import split_list_groups


logger = logging.getLogger(__name__)


def get_InputMediaPhoto(
    media: str,
    caption: str = "",
) -> InputMediaPhoto:
    return InputMediaPhoto(
        media=media,
        caption=caption[:1024] if caption else None,
        parse_mode=ParseMode.HTML,
    )


def get_InputMediaVideo(
    media: str,
    thumb: str = None,
    caption: str = "",
    width: int = 0,
    height: int = 0,
    duration: int = 0,
) -> InputMediaVideo:
    return InputMediaVideo(
        media=media,
        thumb=thumb,
        caption=caption[:1024] if caption else None,
        parse_mode=ParseMode.HTML,
        width=width,
        height=height,
        duration=duration,
        supports_streaming=True,
    )


async def reply_text(
    message: Message,
    text: str,
) -> Message:
    while True:
        try:
            return await message.reply_text(
                text=text[:4096],
                quote=False,
                parse_mode=ParseMode.HTML,
            )
        except (BadRequest, UnicodeEncodeError):
            return
        except FloodWait as e:
            await sleep(e.value)
        except Exception as e:
            logger.info(e)


async def edit_text(
    message: Message,
    text: str,
) -> Message:
    while True:
        try:
            return await message.edit_text(
                text=text[:4096],
                parse_mode=ParseMode.HTML,
            )
        except (BadRequest, UnicodeEncodeError):
            return
        except FloodWait as e:
            await sleep(e.value)
        except Exception as e:
            logger.info(e)


async def reply_media_group(
    message: Message,
    list_of_media: list,
) -> list:
    msg_guide = await reply_text(message, "🚀 Sending album...")
    del_msg_guide = False
    while True:
        try:
            msgs_list = await message.reply_media_group(
                media=list_of_media,
                quote=False,
            )
            if len(msgs_list) < 2:
                for msg in msgs_list:
                    await msg.delete()
                continue
            del_msg_guide = True
            return msgs_list
        except BadRequest as e:
            del_msg_guide = True
            raise Exception(e)
        except FloodWait as e:
            await sleep(e.value)
        except (AttributeError, UnicodeEncodeError):
            del_msg_guide = True
            return
        except Exception as e:
            if "empty" in str(e):
                del_msg_guide = True
                return
            logger.info(e)
        finally:
            if del_msg_guide:
                await msg_guide.delete()


async def reply_photo(
    message: Message,
    photo: str,
    caption: str = "",
) -> Message:
    while True:
        try:
            await message.reply_chat_action(action=ChatAction.UPLOAD_PHOTO)
            return await message.reply_photo(
                photo=photo,
                quote=False,
                caption=caption[:1024] if caption else None,
                parse_mode=ParseMode.HTML,
            )
        except BadRequest:
            return await reply_document(message, document=photo, caption=caption)
        except FloodWait as e:
            await sleep(e.value)
        except (AttributeError, UnicodeEncodeError):
            return
        except Exception as e:
            if "empty" in str(e):
                return
            logger.info(e)


async def reply_animation(
    message: Message,
    animation: str,
    caption: str = "",
    duration: int = 0,
    width: int = "",
    height: int = 0,
    thumb: str = None,
) -> Message:
    msg_guide = await reply_text(message, "🚀 Sending animation...")
    del_msg_guide = False
    while True:
        try:
            await message.reply_chat_action(action=ChatAction.UPLOAD_VIDEO)
            msg = await message.reply_animation(
                animation=animation,
                quote=False,
                caption=caption,
                parse_mode=ParseMode.HTML,
                duration=duration,
                width=width,
                height=height,
                thumb=thumb,
            )
            del_msg_guide = True
            return msg
        except BadRequest:
            del_msg_guide = True
            return await reply_document(
                message, document=animation, thumb=thumb, caption=caption
            )
        except FloodWait as e:
            await sleep(e.value)
        except (AttributeError, UnicodeEncodeError):
            del_msg_guide = True
            return
        except Exception as e:
            if "empty" in str(e):
                del_msg_guide = True
                return
            logger.info(e)
        finally:
            if del_msg_guide:
                await msg_guide.delete()


async def reply_video(
    message: Message,
    video: str,
    caption: str = "",
    duration: int = 0,
    width: int = 0,
    height: int = 0,
    thumb: str = None,
) -> Message:
    msg_guide = await reply_text(message, "🚀 Sending video...")
    del_msg_guide = False
    while True:
        try:
            await message.reply_chat_action(action=ChatAction.UPLOAD_VIDEO)
            msg = await message.reply_video(
                video=video,
                quote=False,
                caption=caption[:1024] if caption else None,
                parse_mode=ParseMode.HTML,
                duration=duration,
                width=width,
                height=height,
                thumb=thumb,
                supports_streaming=True,
            )
            del_msg_guide = True
            return msg
        except BadRequest:
            del_msg_guide = True
            return await reply_document(
                message, document=video, thumb=thumb, caption=caption
            )
        except FloodWait as e:
            await sleep(e.value)
        except (AttributeError, UnicodeEncodeError):
            del_msg_guide = True
            return
        except Exception as e:
            if "empty" in str(e):
                del_msg_guide = True
                return
            logger.info(e)
        finally:
            if del_msg_guide:
                await msg_guide.delete()


async def reply_audio(
    message: Message,
    audio: str,
    caption: str = "",
    duration: int = 0,
    performer: str = "",
    title: str = "",
    thumb: str = None,
) -> Message:
    msg_guide = await reply_text(message, "🚀 Sending audio...")
    del_msg_guide = False
    while True:
        try:
            await message.reply_chat_action(action=ChatAction.UPLOAD_AUDIO)
            msg = await message.reply_audio(
                audio=audio,
                quote=False,
                caption=caption[:1024] if caption else None,
                parse_mode=ParseMode.HTML,
                duration=duration,
                performer=performer,
                title=title,
                thumb=thumb,
            )
            del_msg_guide = True
            return msg
        except BadRequest:
            del_msg_guide = True
            return await reply_document(
                message, document=audio, thumb=thumb, caption=caption
            )
        except FloodWait as e:
            await sleep(e.value)
        except (AttributeError, UnicodeEncodeError):
            del_msg_guide = True
            return
        except Exception as e:
            if "empty" in str(e):
                del_msg_guide = True
                return
            logger.info(e)
        finally:
            if del_msg_guide:
                await msg_guide.delete()


async def reply_document(
    message: Message,
    document: str,
    thumb: str = None,
    caption: str = "",
) -> Message:
    msg_guide = await reply_text(message, "🚀 Sending document...")
    del_msg_guide = False
    while True:
        try:
            await message.reply_chat_action(action=ChatAction.UPLOAD_DOCUMENT)
            msg = await message.reply_document(
                document=document,
                quote=False,
                thumb=thumb,
                caption=caption[:1024] if caption else None,
                parse_mode=ParseMode.HTML,
                force_document=True,
            )
            del_msg_guide = True
            return msg
        except BadRequest as e:
            del_msg_guide = True
            raise Exception(e)
        except FloodWait as e:
            await sleep(e.value)
        except (AttributeError, UnicodeEncodeError):
            del_msg_guide = True
            return
        except Exception as e:
            if "empty" in str(e):
                del_msg_guide = True
                return
            logger.info(e)
        finally:
            if del_msg_guide:
                await msg_guide.delete()


async def download(message: Message, sender_path: str) -> str:
    msg_guide = await reply_text(message, "🚀 Downloading file...")
    while True:
        try:
            file_path = await message.download(f"{sender_path}/")
            if not file_path:
                continue
            await msg_guide.delete()
            return file_path
        except Exception as e:
            logger.info(e)


async def send_dl_media(message: Message, data: dict) -> None:
    await handle_video(message, data)
    # await handle_subtitles(message, data)
    await handle_images(message, data)
    # await handle_audio(message, data)


async def handle_video(message: Message, data: dict) -> None:
    if not data.get("video_path"):
        return

    if data["video_path"].lower().endswith(".mp4"):
        await handle_mp4_video(message, data)
    else:
        await handle_non_mp4_video(message, data)


async def handle_mp4_video(message: Message, data: dict) -> None:
    if data.get("album_thumb_path"):
        await send_media_group_with_photo_and_video(message, data)
    else:
        await send_video(message, data)


async def send_media_group_with_photo_and_video(message: Message, data: dict) -> None:
    input_media_photo = get_InputMediaPhoto(
        media=data["album_thumb_path"],
        caption=data["caption"],
    )
    input_media_video = get_InputMediaVideo(
        media=data["video_path"],
        thumb=data.get("youtube_thumb_path", data.get("thumb_path", None)),
        caption=data["caption"],
        width=data["video_width"],
        height=data["video_height"],
        duration=data["video_duration"],
    )
    try:
        await reply_media_group(
            message,
            list_of_media=[input_media_photo, input_media_video],
        )
    except Exception:
        await reply_photo(
            message,
            photo=data["album_thumb_path"],
            caption=data["caption"],
        )
        return await send_video(message, data)

    await reply_document(
        message,
        document=data["video_path"],
        thumb=data.get("youtube_thumb_path", data.get("thumb_path", None)),
        caption=data["caption"],
    )


async def send_video(message: Message, data: dict) -> None:
    await reply_video(
        message,
        video=data["video_path"],
        caption=data["caption"],
        duration=data["video_duration"],
        width=data["video_width"],
        height=data["video_height"],
        thumb=data.get("youtube_thumb_path", data.get("thumb_path", None)),
    )
    # await reply_document(
    #     message,
    #     document=data["video_path"],
    #     thumb=data.get("youtube_thumb_path", data.get("thumb_path", None)),
    #     caption=data["caption"],
    # )


async def handle_non_mp4_video(message: Message, data: dict) -> None:
    if data.get("album_thumb_path"):
        await reply_photo(
            message,
            photo=data["album_thumb_path"],
            caption=data["caption"],
        )
    await reply_document(
        message,
        document=data["video_path"],
        thumb=data.get("youtube_thumb_path", data.get("thumb_path", None)),
        caption=data["caption"],
    )


async def handle_subtitles(message: Message, data: dict) -> None:
    if not data.get("subtitles_path"):
        return

    for subtitle_path in data["subtitles_path"]:
        await reply_document(
            message,
            document=subtitle_path,
            thumb=data.get("youtube_thumb_path", data.get("thumb_path", None)),
            caption=data["caption"],
        )


async def handle_images(message: Message, data: dict) -> None:
    if not data.get("images_path"):
        return

    group_images = list(split_list_groups(data["images_path"], 10))
    for group in group_images:
        if len(group) == 1:
            await reply_photo(message, photo=group[0])
        else:
            try:
                await reply_media_group(
                    message,
                    list_of_media=[
                        get_InputMediaPhoto(image_path) for image_path in group
                    ],
                )
            except Exception:
                for image_path in group:
                    await reply_photo(message, photo=image_path)


async def handle_audio(message: Message, data: dict) -> None:
    if not data.get("audio_path"):
        return

    await reply_audio(
        message,
        audio=data["audio_path"],
        caption=data["caption"],
        duration=data["audio_duration"],
        performer=data["uploader_id"],
        title=data["title"],
        thumb=data.get("youtube_thumb_path", data.get("thumb_path", None)),
    )

    await reply_document(
        message,
        document=data["audio_path"],
        thumb=data.get("youtube_thumb_path", data.get("thumb_path", None)),
        caption=data["caption"],
    )
