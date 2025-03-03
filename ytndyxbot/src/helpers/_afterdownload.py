import time

import aiofiles.os
import ffmpeg

from asyncio import to_thread
from pathlib import Path
from os import path
from dataclasses import dataclass

from pyvideothumbnailer.videothumbnailer import Parameters, VideoThumbnailer


@dataclass
class VideoData:
    path: str | None
    width: int | None
    height: int | None
    duration: int | None
    is_audio: bool


@dataclass
class AudioData:
    path: str | None
    duration: int | None


class ThumbnailGenerator:
    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path

    async def generate(self, ss_cap: int = None) -> None:
        await to_thread(self._create_thumbnail, ss_cap)

    def _create_thumbnail(self, ss_cap: int = None) -> None:
        ffmpeg_input = (
            ffmpeg.input(self.input_path, ss=ss_cap)
            if ss_cap
            else ffmpeg.input(self.input_path)
        )
        (
            ffmpeg_input.filter("scale", 320, -1)
            .output(
                self.output_path,
                vframes=1 if ss_cap else None,
                format="image2",
                vcodec="mjpeg",
                pix_fmt="yuvj420p",
                qmin=1,
                q=0,
                compression_level=0,
                loglevel="quiet",
            )
            .run()
        )


class BaseAfterDownload:
    def __init__(self):
        self.font_path: str = ""
        self.client_name: str = ""

    async def start(
        self,
        video_path: str = None,
        audio_path: str = None,
        thumb_path: str = None,
        **kwargs,
    ) -> dict:
        if not video_path and not audio_path:
            return {}

        video_data = await self._analyze_video(video_path)
        audio_path, video_data = self._handle_audio_path(video_data, audio_path)
        audio_data = await self._analyze_audio(audio_path)
        thumbnail_path = await self._generate_thumbnail(video_data, thumb_path)
        album_thumb_path = await self._generate_preview_thumbnails(video_data.path)

        return {
            "video_path": video_data.path,
            "audio_path": audio_data.path,
            "video_width": video_data.width,
            "video_height": video_data.height,
            "video_duration": video_data.duration,
            "audio_duration": audio_data.duration,
            "thumb_path": thumbnail_path,
            "album_thumb_path": album_thumb_path,
        }

    def _handle_audio_path(
        self, video_data: VideoData, audio_path: str
    ) -> tuple[str, VideoData]:
        if video_data.path and video_data.is_audio and not audio_path:
            audio_path = video_data.path
            video_data.path = None
        return audio_path, video_data

    async def _analyze_video(self, media_path: str) -> VideoData:
        if not media_path:
            return VideoData(None, None, None, None, False)

        media_probe = await to_thread(ffmpeg.probe, media_path)
        video_info = next(
            (
                stream
                for stream in media_probe["streams"]
                if stream["codec_type"] == "video"
            ),
            None,
        )
        audio_info = next(
            (
                stream
                for stream in media_probe["streams"]
                if stream["codec_type"] == "audio"
            ),
            None,
        )
        duration = int(float(media_probe["format"]["duration"]))

        return VideoData(
            path=media_path,
            width=int(video_info["width"]) if video_info else None,
            height=int(video_info["height"]) if video_info else None,
            duration=duration,
            is_audio=bool(audio_info and not video_info),
        )

    async def _analyze_audio(self, audio_path: str) -> AudioData:
        if not audio_path:
            return AudioData(None, None)

        audio_probe = await to_thread(ffmpeg.probe, audio_path)
        duration = int(float(audio_probe["format"]["duration"]))

        return AudioData(path=audio_path, duration=duration)

    async def _generate_thumbnail(
        self, video_data: VideoData, thumb_path: str
    ) -> str | None:
        if not video_data.path and not thumb_path:
            return None

        fpath = video_data.path or thumb_path
        new_thumb_path = path.join(path.dirname(fpath), f"thumb_path_{time.time()}.jpg")
        ss_cap = 1 if video_data.duration else None

        generator = ThumbnailGenerator(fpath, new_thumb_path)
        await generator.generate(ss_cap)

        return new_thumb_path if await aiofiles.os.path.exists(new_thumb_path) else None

    async def _generate_preview_thumbnails(self, video_path: str) -> str | None:
        if not video_path:
            return None

        try:
            parameters = Parameters(
                path=Path(video_path),
                recursive=False,
                width=1024,
                columns=4,
                rows=4,
                vertical_video_columns=None,
                vertical_video_rows=None,
                spacing=2,
                background_color="black",
                no_header=False,
                header_font_name=self.font_path,
                header_font_size=14,
                header_font_color="white",
                timestamp_font_name=self.font_path,
                timestamp_font_size=12,
                timestamp_font_color="white",
                timestamp_shadow_color="black",
                comment_label="Comment:",
                comment_text=f"PREVIEW GENERATED BY @{self.client_name}",
                skip_seconds=10.0,
                suffix=None,
                jpeg_quality=95,
                override_existing=False,
                output_directory=None,
                raise_errors=False,
                verbose=False,
            )
            thumbnailer = VideoThumbnailer(parameters)
            await to_thread(thumbnailer.create_and_save_preview_thumbnails)
            output_path = video_path + ".jpg"
            return output_path if await aiofiles.os.path.exists(output_path) else None
        except Exception:
            return None
