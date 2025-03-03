import json
import re

from datetime import datetime
from typing import Generator

from .common import InfoExtractor


class PmvhavenIE(InfoExtractor):
    _VALID_URL = r"https?://(?:www\.)?pmvhaven\.com/video/(?P<title>[a-zA-Z0-9-]+)_(?P<id>[a-z0-9]+)"

    def _search_dict(
        self, partial: dict, search_key: str
    ) -> Generator[dict, None, None]:
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
            else:
                current_item = current_item[0]

    def _resolve_indices(self, data, index_or_indices):
        if isinstance(index_or_indices, int):
            return data[index_or_indices]
        elif isinstance(index_or_indices, list):
            return [
                data[i]
                for i in index_or_indices
                if isinstance(i, int) and i < len(data)
            ]

    def _extract_data(self, data, key_map):
        extracted_data = {}
        for key, index in key_map.items():
            value = self._resolve_indices(data, index)
            if isinstance(value, list) and all(isinstance(i, int) for i in value):
                extracted_data[key] = self._resolve_indices(data, value)
            else:
                extracted_data[key] = value
        return extracted_data

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        nuxt_data_str = self._search_regex(
            r'<script type="application/json" id="__NUXT_DATA__" data-ssr="true">(.*)</script>\n',
            webpage,
            "NUXT_DATA",
        )
        cleaned_str = re.sub(r",\s*]", "]", nuxt_data_str)
        cleaned_str = re.sub(r",\s*}", "}", cleaned_str)
        cleaned_str = re.sub(r",\s*,", ",", cleaned_str)
        nuxt_data_json = json.loads(cleaned_str)

        # 1. Find the index of the key "video" in nuxt_data_json.
        # 2. Use that index to get a list.
        # 3. Take the first element of that list.
        # 4. Use that element to access a dictionary in nuxt_data_json.
        key_map = nuxt_data_json[
            nuxt_data_json[next(self._search_dict(nuxt_data_json, "video"), None)][0]
        ]
        info = self._extract_data(nuxt_data_json, key_map)
        formats = []
        url = info.get("url")
        if url:
            formats.append(
                {
                    "url": url,
                    "filesize": info.get("size"),
                    "height": int(info.get("height")),
                    "width": int(info.get("width")),
                    "aspect_ratio": info.get("aspectratio"),
                }
            )
        url = info.get("videoUrl264")
        if url:
            formats.append(
                {
                    "url": url,
                    "filesize": info.get("size264"),
                    "height": int(info.get("height")),
                    "width": int(info.get("width")),
                    "aspect_ratio": info.get("aspectratio"),
                }
            )
        thumbnails = []
        all_thumbnails = info.get("thumbnails", [])
        all_thumbnails.extend(info.get("thumbnail240Url", []))
        all_thumbnails = list(filter(lambda item: item is not None, all_thumbnails))

        if all_thumbnails:
            for thumb in all_thumbnails:
                if thumb.startswith("https") and self._is_valid_url(
                    thumb, video_id, "thumbnail"
                ):
                    thumbnails.append({"url": thumb})

        upload_date = info.get("isoDate")

        if upload_date:
            try:
                upload_date_obj = datetime.strptime(
                    upload_date, "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                upload_date = upload_date_obj.strftime("%Y%m%d")
            except ValueError:
                upload_date = None

        return {
            "id": video_id,
            "title": info.get("title"),
            "description": info.get("description"),
            "formats": formats,
            "thumbnails": thumbnails,
            "tags": info.get("tags"),
            "uploader": info.get("uploader"),
            "duration": int(info.get("duration")),
            "upload_date": upload_date,
        }
