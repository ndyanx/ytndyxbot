CLIENT_ID = None

SESSION_PATH = None
COOKIES_PATH = None
DOWNLOADS_PATH = None
DOWNLOADS_TEMP_PATH = None

FONTS_PATH = None

SQLITE_DB_PATH = None

MYSQL_DB_HOST = None
MYSQL_DB_USER = None
MYSQL_DB_PASSWORD = None
MYSQL_DB_NAME = None

MAX_INTENT_DL = None

RGX_VK_PROFILE = r"https?://vkvideo\.ru/@(?P<username>[a-zA-Z0-9]+)/uploaded"
RGX_RUTUBE_PROFILE = (
    r"https?://rutube\.ru/(channel|u)/(?P<id>[a-z0-9]+)/(videos|shorts)/"
)
RGX_YOUTUBE_PROFILE = r"https?://(?:www|m)\.youtube\.com/(@?(?P<username>[a-zA-Z0-9_]+)|channel/(?P<channelname>[a-zA-Z0-9_.-]+))/(videos|shorts|streams)"
RGX_YOUTUBE_PLAYLIST = r"https?://(?:www\.|m\.)?(youtube\.com|youtu\.be)/playlist\?list=(?P<id>[a-zA-Z0-9_-]+)"
RGX_BUNKR_ALBUM = r"https?://(bunkr+)\.(?P<domain>[a-z]+)/a/(?P<id>[a-zA-Z0-9]+)"
RGX_COOMER_PROFILE = (
    r"https?://coomer\.su/(?P<site>[a-z]+)/user/(?P<user>[a-zA-Z0-9_.]+)"
)
RGX_KEMONO_PROFILE = (
    r"https?://kemono\.su/(?P<site>[a-z]+)/user/(?P<user>[a-zA-Z0-9_.]+)"
)
RGX_HSTREAM_ALBUM = r"https?://hstream\.moe/hentai/(?P<id>[a-z0-9-]+)[^-0-9]$"
RGX_STRIPCHAT_LIVE = r"https?://stripchat\.com/(?P<id>[^/?#]+)"
RGX_CHATURBATE_LIVE = r"https?://(?:[^/]+\.)?chaturbate\.(?P<tld>com|eu|global)/(?:fullvideo/?\?.*?\bb=)?(?P<id>[^/?&#]+)"
RGX_CAMSODA_LIVE = r"https?://www\.camsoda\.com/(?P<id>[\w-]+)"
RGX_BONGACAMS_LIVE = (
    r"https?://(?P<host>(?:[^/]+\.)?bongacams\d*\.(?:com|net))/(?P<id>[^/?&#]+)"
)
SITES_LIVE = (
    RGX_STRIPCHAT_LIVE,
    RGX_CHATURBATE_LIVE,
    RGX_CAMSODA_LIVE,
    RGX_BONGACAMS_LIVE,
)

WELCOME_MESSAGE = "HI, I'M USERBOT"
