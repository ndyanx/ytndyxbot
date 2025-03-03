from pyrogram import Client
from pyrogram.types import Message

from .. import utils
from ..enums import SiteIE
from ..helpers import BaseAfterDownload, BaseDownload
from ..queues import DownloadQueue, AfterDownloadQueue, SenderMediaQueue


def extract_url(text: str) -> str:
    url = text.split()[0].strip()
    utils.is_valid_url(url)
    return url


def extract_params_scraper(text: str) -> dict:
    return {
        "limit_id": utils.extract_value(text, "limitid"),
        "sort_by": utils.extract_value(text, "sortby"),
        "only_images": "--onlyimages" in text,
    }


def extract_params_dl(text: str) -> dict:
    referer = utils.extract_value(text, "referer")
    if referer:
        utils.is_valid_url(referer)

    quality = utils.extract_value(text, "quality")
    valid_qualities = utils.get_valid_qualitys()
    if quality and quality not in valid_qualities:
        raise Exception(
            f"Invalid quality, use: <b>{' - '.join(valid_qualities)}</b>\n"
            "Default quality is up to 1440p, but it may vary depending on the site, starting from 1440p down to 240p."
        )

    return {
        "referer": referer,
        "password": utils.extract_value(text, "password"),
        "quality": quality,
    }


class Base:
    def __init__(
        self,
        client: Client,
        message: Message,
        sender_id: int,
        site_ie: SiteIE,
        url_direct: str = None,
    ):
        sender_id = str(sender_id)
        self.client = client
        self.message = message
        self.sender_id = sender_id
        self.site_ie = site_ie
        self.sender_priority = 0
        self.is_sender_premium = False
        self.dir_sender = ""
        self.dir_sender_temp = ""
        self.is_simulation = "-simulate" in message.text
        self.url = url_direct or extract_url(message.text)
        self.params_scraper = extract_params_scraper(message.text)
        self.dl = BaseDownload(
            sender_id,
            sender_path="",
            sender_temp_path="",
            params=extract_params_dl(message.text),
        )
        self.dl_queue = DownloadQueue()
        self.after_dl = BaseAfterDownload()
        self.after_dl_queue = AfterDownloadQueue()
        self.sender_media_queue = SenderMediaQueue()
