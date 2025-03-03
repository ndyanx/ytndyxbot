import asyncio
import os
import aiofiles.os

from datetime import datetime

from yt_dlp.networking.impersonate import ImpersonateTarget
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessorError
from yt_dlp.utils import (
    ContentTooShortError,
    ExtractorError,
    EntryNotInPlaylist,
    DownloadCancelled,
    DownloadError,
    PostProcessingError,
    ReExtractInfo,
    SameFileError,
    UnavailableVideoError,
    UserNotLive,
    XAttrMetadataError,
    XAttrUnavailableError,
)

from ..cache import cancel_cache
from ..exceptions import (
    CancelledDownload,
    InvalidFileFormat,
    InvalidFileSize,
    InvalidPlaylist,
    NotFoundRequestedDownloads,
)
from ..utils import (
    get_max_intent_dl,
    get_valid_qualitys,
    traverse_obj,
)
from ..wrappers import _ytdlp


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"


def handle_download_exceptions(
    e: Exception, url: str, index_format: int, max_index_format: int
) -> dict:
    if isinstance(e, InvalidFileSize) and index_format < max_index_format:
        return {"retry": True, "index_format": index_format + 1}
    elif isinstance(e, CancelledDownload):
        raise CancelledDownload(e)
    elif isinstance(
        e, (InvalidFileFormat, InvalidPlaylist, NotFoundRequestedDownloads)
    ):
        return {"error": f"{str(e)}\n{url}"}
    elif isinstance(e, DownloadError):
        if "WinError" in e.msg:
            return {"retry": True}
        elif "Requested format is not available" in e.msg:
            return {"retry": True, "index_format": index_format + 1}
        elif e.exc_info[0]:
            if issubclass(
                e.exc_info[0].__bases__[0], PostProcessingError
            ) or issubclass(e.exc_info[0], FFmpegPostProcessorError):
                return {"retry": True, "remove_postprocessors": True}
            else:
                str_not_live = [
                    "Room is currently offline",
                    "Room is currently in a private show",
                    "Performer is currently away",
                    "Room is password protected",
                    "Hidden session in progress",
                    "Unable to find configuration for stream.",
                    "Model is offline",
                    "not currently live",
                    "private show",
                    "Model is in private show.",
                    "Model is offline.",
                ]
                if isinstance(e.exc_info[1], UserNotLive) or any(
                    x in e.exc_info[1].msg for x in str_not_live
                ):
                    raise Exception(f"[YTDLP_EXCEPTIONS]\n{e.exc_info[1].msg}\n{url}")
                else:
                    return {"error": f"[YTDLP_EXCEPTIONS]\n{e.exc_info[1].msg}\n{url}"}
        else:
            return {"error": f"{e.msg}\n{url}"}
    return {"retry": True}


class BaseDownload:
    _YTDLP_EXCEPTIONS = (
        ContentTooShortError,
        ExtractorError,
        EntryNotInPlaylist,
        DownloadCancelled,
        ReExtractInfo,
        SameFileError,
        UnavailableVideoError,
        XAttrMetadataError,
        XAttrUnavailableError,
    )
    _WARNING_EXCEPTIONS = (
        InvalidFileFormat,
        InvalidFileSize,
        InvalidPlaylist,
        NotFoundRequestedDownloads,
    )
    _VIDEO_EXTENSIONS = (
        "avi",
        "divx",
        "flv",
        "m4v",
        "mkv",
        "mov",
        "mp4",
        "mpg",
        "wmv",
        "mts",
        "gif",
    )
    _AUDIO_EXTENSIONS = ("mp3", "wav", "aac", "m4a", "flac", "ogg", "wma", "opus")
    _IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "jfif")

    def __init__(self, sender_id, sender_path, sender_temp_path, params):
        self.sender_id: str = sender_id
        self.sender_path: str = sender_path
        self.sender_temp_path: str = sender_temp_path
        self.params: dict = params
        self.max_intent_dl: int = get_max_intent_dl()
        self.cookie_path: str = ""
        self.limit_size: dict = {}
        self.ytdlp_formats: list = []
        self.max_index_format: int = 0
        self.ydl_opts: dict = {}

    async def start(self, url: str) -> dict:
        intent_dl = 0
        index_format = 0
        self._prepare_formats()
        self._prepare_opts(url)

        while intent_dl < self.max_intent_dl:
            try:
                return await self._download(url)
            except Exception as e:
                result = handle_download_exceptions(
                    e, url, index_format, self.max_index_format
                )
                if "error" in result:
                    return result
                if "index_format" in result:
                    self.ydl_opts["format"] = self.ytdlp_formats[result["index_format"]]
                if "remove_postprocessors" in result:
                    del self.ydl_opts["postprocessors"]
                intent_dl += 1
                await asyncio.sleep(5)
        return {"error": "Max download attempts reached"}

    def _prepare_formats(self) -> None:
        quality = self.params.get("quality")
        formats = []
        if quality is None:
            quality = "1440"

        valid_qualitys = get_valid_qualitys()
        quality_index = valid_qualitys.index(quality)
        for q in valid_qualitys[quality_index:]:
            formats.append(
                f"bestvideo[height<={q}][ext=mp4]+bestaudio[ext=m4a]/"
                + f"bestvideo[height<={q}][ext=mp4]+bestaudio/"
                + f"best[height<={q}]/best"
            )

        self.ytdlp_formats = formats
        self.max_index_format = len(self.ytdlp_formats) - 1

    def _prepare_opts(self, url: str) -> None:
        self.ydl_opts = {
            "paths": {"home": self.sender_path, "temp": self.sender_temp_path},
            "cookiefile": self.cookie_path,
            "format": self.ytdlp_formats[0],
            "format_sort": ["tbr"],
            "outtmpl": "%(id).50s.f%(format_id)s.%(ext)s",
            "writesubtitles": True,
            "subtitleslangs": ["es", "en"],
            "sleep_interval_subtitles": 5,
            "playlistend": "1",
            "noplaylist": True,
            "restrictfilenames": True,
            "writethumbnail": True,
            # "verbose": True,
            "quiet": True,
            "noprogress": True,
            "keepvideo": True,
            "socket_timeout": 1500,
            "videopassword": self.params.get("password"),
            "http_headers": self.params.get("http_headers")
            or {"User-Agent": USER_AGENT},
            "progress_hooks": self._get_all_funcs(),
            "postprocessors": [
                {"key": "FFmpegSubtitlesConvertor", "format": "srt"},
                {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": True},
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail", "already_have_thumbnail": True},
            ],
            "fixup": "detect_or_warn",
            "retries": 100,
        }

        if url.endswith(self._AUDIO_EXTENSIONS + self._IMAGE_EXTENSIONS):
            del self.ydl_opts["format"]
            del self.ydl_opts["writethumbnail"]
            del self.ydl_opts["postprocessors"]
        if any(netloc in url for netloc in ["camsoda.com", "stripchat.com"]):
            self.ydl_opts["impersonate"] = ImpersonateTarget(
                "chrome", "110", "windows", "10"
            )
            self.ydl_opts["external_downloader_args"] = {"ffmpeg": ["-t", "5400"]}
        if "tiktok.com" in url:
            self.ydl_opts["postprocessors"].pop()
        if "hstream.moe" in url:
            self.ydl_opts["format_sort"] = ["+codec:avc:m4a"]

    def _get_all_funcs(self) -> list:
        def verify_size(d):
            total1 = d.get("total_bytes") if d.get("total_bytes") else 0
            total2 = (
                d.get("total_bytes_estimate") if d.get("total_bytes_estimate") else 0
            )
            total_bytes_aprox = (
                min(total1, total2) if total1 and total2 else max(total1, total2)
            )
            if total_bytes_aprox > self.limit_size.get("int") or d.get(
                "downloaded_bytes", 0
            ) > self.limit_size.get("int"):
                raise InvalidFileSize(
                    "⚠️ Max upload size: " + self.limit_size.get("str")
                )

        def verify_cancel(d):
            if cancel_cache.get(self.sender_id, {}).get("state"):
                cancel_cache[self.sender_id]["state"] = False
                raise CancelledDownload("❌ Download cancelled")

        def verify_playlist(d):
            is_playlist = traverse_obj(d, ("info_dict", "playlist")) or traverse_obj(
                d, ("info_dict", "playlist_index")
            )
            if is_playlist:
                raise InvalidPlaylist("⚠️ Playlist download disabled")

        return [verify_size, verify_cancel, verify_playlist]

    async def _download(self, url) -> dict:
        data = {}
        if url:
            data |= await self._download_media(url)
        if self.params.get("images_url"):
            data |= await self._download_images()
        return data

    async def _download_media(self, url) -> dict:
        info = await asyncio.to_thread(
            _ytdlp.extract_info, url, self.ydl_opts, self.params.get("referer")
        )
        return await self._get_data(info)

    async def _get_data(self, info) -> dict:
        video_path = None
        audio_path = None
        thumb_path = None
        subtitles_path = None
        images_path = None

        req_subtitles = info.get("requested_subtitles")
        subtitles_path = (
            [sub["filepath"] for sub in req_subtitles.values()]
            if req_subtitles
            else None
        )
        if subtitles_path:
            updated_subtitles_path = []
            for sub in subtitles_path:
                sub_path = await self._get_final_path(sub)
                if sub_path:
                    updated_subtitles_path.append(sub_path)
            subtitles_path = updated_subtitles_path

        req_downloads = traverse_obj(info, ("requested_downloads", 0))
        if not req_downloads:
            raise NotFoundRequestedDownloads(
                "⚠️ Not found requested_downloads\n" + info.get("original_url")
            )

        media_path = req_downloads.get("filename", "_filename")
        if self._verify_ext(media_path, self._VIDEO_EXTENSIONS):
            video_path = media_path
            await self._verify_size(video_path)

            files_to_merge = req_downloads.get("__files_to_merge")
            if files_to_merge:
                audio = [
                    file
                    for file in files_to_merge
                    if file.endswith(self._AUDIO_EXTENSIONS)
                ]
                audio_path = await self._get_final_path(audio[0]) if audio else None

        elif self._verify_ext(media_path, self._AUDIO_EXTENSIONS):
            audio_path = await self._get_final_path(media_path)

        elif self._verify_ext(media_path, self._IMAGE_EXTENSIONS):
            images_path = [await self._get_final_path(media_path)]

        else:
            raise InvalidFileFormat("⚠️ The file format is invalid")

        thumb = traverse_obj(info, ("thumbnails", -1, "filepath"))
        thumb_path = await self._get_final_path(thumb) if thumb else None

        paths = {
            "video_path": video_path,
            "audio_path": audio_path,
            "thumb_path": thumb_path,
            "subtitles_path": subtitles_path,
            "images_path": images_path,
            "only_images": bool(images_path),
        }

        is_youtube = info.get("extractor").lower().startswith("youtube")
        is_short = info.get("height", 0) > info.get("width", 0)
        if is_youtube and not is_short:
            filepath = await self._get_youtube_thumb_path(info.get("id"))
            if filepath:
                paths["youtube_thumb_path"] = filepath

        return {**paths, **self._get_extra_data(info)}

    def _verify_ext(self, media_path, exts) -> bool:
        return media_path.lower().endswith(exts)

    async def _verify_size(self, media_path) -> None:
        video_size = await aiofiles.os.path.getsize(media_path)
        if video_size > self.limit_size.get("int"):
            raise InvalidFileSize("⚠️ Max upload size: " + self.limit_size.get("str"))

    async def _get_final_path(self, file_path: str) -> str | None:
        file_path = os.path.join(self.sender_path, os.path.basename(file_path))
        if not await aiofiles.os.path.exists(file_path):
            return None
        await self._verify_size(file_path)
        return file_path

    async def _get_youtube_thumb_path(self, video_id) -> str | None:
        def task():
            intent = 1
            while intent < 3:
                try:
                    info = _ytdlp.extract_info(
                        "https://i.ytimg.com/vi/{0}/mqdefault.jpg".format(video_id),
                        self.ydl_opts,
                    )
                    return traverse_obj(info, ("requested_downloads", 0, "filepath"))
                except Exception:
                    intent += 1

        return await asyncio.to_thread(task)

    def _get_extra_data(self, info) -> dict:
        original_url = info.get("original_url")
        title = info.get("fulltitle", "title")
        extractor = (
            info["webpage_url_domain"]
            if info["extractor"] == "generic"
            else info["extractor"]
        ).upper()
        uploader_id = info.get("uploader_id", extractor)

        caption = [f"<b>[{extractor}]</b>"]
        if title not in info.get("id"):
            caption.append(f"<b>TITLE:</b> {title}")
        if self.params.get("content"):
            caption.append(f"<b>CONTENT:</b> {self.params.get('content')}")
        if info.get("upload_date"):
            upload_date = str(datetime.strptime(info["upload_date"], "%Y%m%d").date())
            caption.append(f"<b>PUBLISHED DATE:</b> {upload_date}")
        caption.append(f'<b>URL:</b> <a href="{original_url}">click here</a>')

        return {
            "uploader_id": uploader_id,
            "title": title,
            "caption": "\n".join(caption) if caption else None,
        }

    async def _download_images(self) -> dict:
        del self.ydl_opts["format"]
        del self.ydl_opts["postprocessors"]
        images_url = self.params.get("images_url")

        def task():
            images_path = []
            for image in images_url:
                self.ydl_opts["http_headers"] = image.get("http_headers", {})
                while True:
                    try:
                        info = _ytdlp.extract_info(image["url"], self.ydl_opts)
                        image_path = traverse_obj(
                            info, ("requested_downloads", 0, "filepath")
                        )
                        if not image_path:
                            continue
                        images_path.append(image_path)
                        break
                    except Exception:
                        pass
            return {"images_path": images_path, "only_images": True}

        return await asyncio.to_thread(task)
