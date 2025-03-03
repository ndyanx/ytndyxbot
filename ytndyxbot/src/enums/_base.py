from enum import Enum


class SiteIE(str, Enum):
    ANY_URL = "any_url"
    RUTUBE_PROFILE = "rutube_profile"
    VK_PROFILE = "vk_profile"
    YOUTUBE_PROFILE = "youtube_profile"
    YOUTUBE_PLAYLIST = "youtube_playlist"
    COOMER_PROFILE = "coomer_profile"
    KEMONO_PROFILE = "kemono_profile"
    BUNKR_ALBUM = "bunkr_album"
    HSTREAM_ALBUM = "hstream_album"
    STRIPCHAT_LIVE = "stripchat_live"
    CHATURBATE_LIVE = "chaturbate_live"
    CAMSODA_LIVE = "camsoda_live"
    BONGACAMS_LIVE = "bongacams_live"


class RequestMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class RequestReturn(str, Enum):
    TEXT = "text"
    JSON = "json"
    SOUP = "soup"
    RESPONSE = "response"


class SenderStatus(int, Enum):
    AVAILABLE = 1
    NOT_AVAILABLE = 0


class StorageOption(dict, Enum):
    PREMIUM = {"int": 4194304000, "str": "4G"}
    FREE = {"int": 2097152000, "str": "2GB"}
    LIMIT = {"int": 50152000, "str": "50MB"}
