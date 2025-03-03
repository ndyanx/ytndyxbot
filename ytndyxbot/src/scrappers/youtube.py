import json
import re

from ..enums import RequestMethod, RequestReturn
from ..utils import search_dict, traverse_obj
from ..wrappers import AiohttpSG


class YoutubeIE:
    _API_YOUTUBEIV1 = "https://www.youtube.com/youtubei/v1/browse"
    _YTCFG = {}
    _HEADERS_YOUTUBEIV1 = {}
    _PARAMS = {}
    _INITIAL_DATA = {}
    _CONTENT_BY_SECTION = {
        "videos": ("richItemRenderer", "content", "videoRenderer"),
        "live": ("richItemRenderer", "content", "videoRenderer"),
        "shorts": (
            "richItemRenderer",
            "content",
            "shortsLockupViewModel",
            "onTap",
            "innertubeCommand",
            "reelWatchEndpoint",
        ),
    }
    _SORT_BY_MAP = {
        "newest": 0,
        "popular": 1,
        "oldest": 2,
    }
    _HEADERS_WEB = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US",  # useful param
        "priority": "u=0, i",
        "sec-ch-ua": '"Chromium";v="124", "Not-A.Brand";v="99", "Google Chrome";v="124"',
        "sec-ch-ua-arch": '"x86"',
        "sec-ch-ua-bitness": '"64"',
        "sec-ch-ua-full-version-list": '"Chromium";v="124.0.6367.201", "Not-A.Brand";v="99.0.0.0", "Google Chrome";v="124.0.6367.201"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-model": '""',
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-platform-version": '"15.0.0"',
        "sec-ch-ua-wow64": "?0",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

    def _prepare_ytcfg(self, url, text) -> None:
        search = re.search(r"ytcfg\.set\((.*)\); ", text.strip())
        if not search:
            raise Exception("Error extracting ytcfg")
        ytcfg = json.loads(search.group(1))
        client = ytcfg["INNERTUBE_CONTEXT"]["client"]
        self._YTCFG = {
            "INNERTUBE_API_KEY": ytcfg["INNERTUBE_API_KEY"],
            "visitorData": client["visitorData"],
            "remoteHost": client["remoteHost"],
            "hl": client["hl"],
            "gl": client["gl"],
            "userAgent": client["userAgent"],
            "clientName": client["clientName"],
            "clientVersion": client["clientVersion"],
            "osName": client.get("osName", "Windows"),
            "osVersion": client["osVersion"],
            "originalUrl": client["originalUrl"],
            "platform": client["platform"],
            "clientFormFactor": client["clientFormFactor"],
            "appInstallData": client["configInfo"]["appInstallData"],
            "userInterfaceTheme": client["userInterfaceTheme"],
            "browserName": client.get("browserName", "Chrome"),
            "browserVersion": client.get("browserVersion", "131.0.0.0"),
            "acceptHeader": client["acceptHeader"],
            "deviceExperimentId": client["deviceExperimentId"],
            "ctp": True,
            "continuation": True,
        }
        self._HEADERS_YOUTUBEIV1 = {
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://www.youtube.com",
            "priority": "u=1, i",
            "sec-ch-ua": '"Chromium";v="124", "Not-A.Brand";v="99", "Google Chrome";v="124"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version": '"124.0.6367.201"',
            "sec-ch-ua-full-version-list": '"Chromium";v="124.0.6367.201", "Not-A.Brand";v="99.0.0.0", "Google Chrome";v="124.0.6367.201"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"15.0.0"',
            "sec-ch-ua-wow64": "?0",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "same-origin",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "x-youtube-bootstrap-logged-in": "false",
            "x-youtube-client-name": "1",
            "x-goog-visitor-id": client["visitorData"],
            "x-youtube-client-version": ytcfg["INNERTUBE_CLIENT_VERSION"],
            "referer": url,
        }
        self._PARAMS = {"prettyPrint": "false"}

    def _prepare_initialdata(self, text) -> None:
        search = None
        search = re.search(r"var ytInitialData = (.*)};</script>", text.strip())
        if not search:
            raise Exception("Error extracting ytInitialData")
        self._INITIAL_DATA = json.loads(search.group(1).strip() + "}")

    async def _get_contents_channel(self, section, sort_by="newest") -> list | None:
        tabs = traverse_obj(
            self._INITIAL_DATA, ("contents", "twoColumnBrowseResultsRenderer", "tabs")
        )
        try:
            tab = next(
                (
                    tab
                    for tab in tabs
                    if traverse_obj(tab, ("tabRenderer", "title")).lower() == section
                ),
                None,
            )
        except Exception:
            raise Exception(f"This channel has not section {section}")

        if not tab or traverse_obj(tab, ("tabRenderer", "content")).get(
            "sectionListRenderer"
        ):
            raise Exception(f"This channel has not section {section}")

        if sort_by and sort_by != "newest":
            part = await anext(
                search_dict(self._INITIAL_DATA, "feedFilterChipBarRenderer"), None
            )
            endpoint = traverse_obj(
                part,
                (
                    "contents",
                    self._SORT_BY_MAP[sort_by],
                    "chipCloudChipRenderer",
                    "navigationEndpoint",
                ),
            )
            if not endpoint:
                raise Exception(f"Sort option unavailable ({sort_by}) in {section}")
            self._YTCFG["ctp"] = endpoint.get("clickTrackingParams")
            self._YTCFG["continuation"] = traverse_obj(
                endpoint, ("continuationCommand", "token")
            )
            return []
        return traverse_obj(
            tab, ("tabRenderer", "content", "richGridRenderer", "contents")
        )

    def _update_ytcfg(self, item) -> None:
        endpoint = traverse_obj(
            item, ("continuationItemRenderer", "continuationEndpoint")
        )
        self._YTCFG["ctp"] = endpoint.get("clickTrackingParams")
        self._YTCFG["continuation"] = traverse_obj(
            endpoint, ("continuationCommand", "token")
        )

    def _get_json_youtubeiv1(self) -> dict:
        return {
            "context": {
                "client": {
                    "hl": self._YTCFG["hl"],
                    "gl": self._YTCFG["gl"],
                    "remoteHost": self._YTCFG["remoteHost"],
                    "deviceMake": "",
                    "deviceModel": "",
                    "visitorData": self._YTCFG["visitorData"],
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "clientName": self._YTCFG["clientName"],
                    "clientVersion": self._YTCFG["clientVersion"],
                    "osName": self._YTCFG["osName"],
                    "osVersion": self._YTCFG["osVersion"],
                    "originalUrl": self._YTCFG["originalUrl"],
                    "platform": self._YTCFG["platform"],
                    "clientFormFactor": self._YTCFG["clientFormFactor"],
                    "configInfo": {
                        "appInstallData": self._YTCFG["appInstallData"],
                    },
                    "userInterfaceTheme": self._YTCFG["userInterfaceTheme"],
                    "browserName": self._YTCFG["browserName"],
                    "browserVersion": self._YTCFG["browserVersion"],
                    "acceptHeader": self._YTCFG["acceptHeader"],
                    "deviceExperimentId": self._YTCFG["deviceExperimentId"],
                    "screenWidthPoints": 594,
                    "screenHeightPoints": 742,
                    "utcOffsetMinutes": -300,
                    "connectionType": "CONN_CELLULAR_4G",
                    "memoryTotalKbytes": "8000000",
                    "mainAppWebInfo": {
                        "graftUrl": self._YTCFG["originalUrl"],
                        "pwaInstallabilityStatus": "PWA_INSTALLABILITY_STATUS_UNKNOWN",
                        "webDisplayMode": "WEB_DISPLAY_MODE_BROWSER",
                        "isWebNativeShareAvailable": True,
                    },
                },
                "user": {
                    "lockedSafetyMode": False,
                },
                "request": {
                    "useSsl": True,
                    "internalExperimentFlags": [],
                    "consistencyTokenJars": [],
                },
                "clickTracking": {
                    "clickTrackingParams": self._YTCFG["ctp"],
                },
                "adSignalsInfo": {
                    "params": [
                        {
                            "key": "dt",
                            "value": "1697240808069",
                        },
                        {
                            "key": "flash",
                            "value": "0",
                        },
                        {
                            "key": "frm",
                            "value": "0",
                        },
                        {
                            "key": "u_tz",
                            "value": "-300",
                        },
                        {
                            "key": "u_his",
                            "value": "2",
                        },
                        {
                            "key": "u_h",
                            "value": "864",
                        },
                        {
                            "key": "u_w",
                            "value": "1536",
                        },
                        {
                            "key": "u_ah",
                            "value": "816",
                        },
                        {
                            "key": "u_aw",
                            "value": "1536",
                        },
                        {
                            "key": "u_cd",
                            "value": "24",
                        },
                        {
                            "key": "bc",
                            "value": "31",
                        },
                        {
                            "key": "bih",
                            "value": "742",
                        },
                        {
                            "key": "biw",
                            "value": "579",
                        },
                        {
                            "key": "brdim",
                            "value": "0,0,0,0,1536,0,1536,816,594,742",
                        },
                        {
                            "key": "vis",
                            "value": "1",
                        },
                        {
                            "key": "wgl",
                            "value": "true",
                        },
                        {
                            "key": "ca_type",
                            "value": "image",
                        },
                    ],
                },
            },
            "continuation": self._YTCFG["continuation"],
        }

    async def _get_continuation_items(self) -> dict | None:
        data = await AiohttpSG.fetch(
            url=self._API_YOUTUBEIV1,
            request_method=RequestMethod.POST,
            request_return_type=RequestReturn.JSON,
            headers=self._HEADERS_YOUTUBEIV1,
            params=self._PARAMS,
            json=self._get_json_youtubeiv1(),
        )
        op1 = traverse_obj(
            data,
            (
                "onResponseReceivedActions",
                1,
                "reloadContinuationItemsCommand",
                "continuationItems",
            ),
        )
        op2 = traverse_obj(
            data,
            (
                "onResponseReceivedActions",
                0,
                "appendContinuationItemsAction",
                "continuationItems",
            ),
        )
        return op1 or op2

    async def _get_videos_channel(self, contents, section, limit_id) -> list:
        videos = []
        while self._YTCFG["ctp"] and self._YTCFG["continuation"]:
            for item in contents:
                if item.get("richItemRenderer"):
                    self._YTCFG["ctp"] = self._YTCFG["continuation"] = ""
                    vd = traverse_obj(item, self._CONTENT_BY_SECTION[section])
                    if vd.get("upcomingEventData"):
                        continue
                    if section.startswith(("videos", "live")) and not vd.get(
                        "publishedTimeText"
                    ):
                        continue
                    videos.append(vd)
                    if vd["videoId"] == limit_id:
                        break
                else:
                    self._update_ytcfg(item)
            if not self._YTCFG["continuation"]:
                break
            contents = None
            while not contents:
                contents = await self._get_continuation_items()
        return videos

    async def profile(self, url, sort_by, limit_id, **kwargs) -> list:
        url = url.split("?")[0]
        section = url.split("/")[-1]
        section = "live" if section == "streams" else section
        if section and not self._CONTENT_BY_SECTION.get(section):
            raise Exception("section invalid, use: videos, shorts, streams/live")
        if sort_by and not self._SORT_BY_MAP.get(sort_by):
            raise Exception("sortby invalid, use: newest(default), popular, oldest")
        text = await AiohttpSG.fetch(
            url=url,
            request_method=RequestMethod.GET,
            request_return_type=RequestReturn.TEXT,
            headers=self._HEADERS_WEB,
            params={"themeRefresh": "1"},
        )
        self._prepare_ytcfg(url, text)
        self._prepare_initialdata(text)
        contents = await self._get_contents_channel(section, sort_by)
        videos = await self._get_videos_channel(contents, section, limit_id)
        dct = {}
        for vd in videos:
            url = ""
            video_id = vd["videoId"]

            if traverse_obj(
                vd,
                ("navigationEndpoint", "commandMetadata", "webCommandMetadata", "url"),
            ):
                url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                url = f"https://www.youtube.com/shorts/{video_id}"

            dct[video_id] = {"url": url, "params": {}}

        return list(reversed(dct.values()))
