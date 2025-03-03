import yt_dlp

# from ..helpers import CookieManager


def extract_info(url, opts: dict, referer: str = None, download: bool = True) -> dict:
    # cookiefile = opts.get("cookiefile")
    # if cookiefile and ("kemono.su" in url or "coomer.su" in url):
    # cookie_manager = CookieManager(cookiefile)
    # cookie_manager.update_cookies()
    if referer:
        yt_dlp.utils.std_headers["Referer"] = referer
    ydl = yt_dlp.YoutubeDL(opts)
    info = ydl.extract_info(url, download)
    del ydl
    return info
