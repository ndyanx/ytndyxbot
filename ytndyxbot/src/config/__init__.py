import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SESSION_PATH = os.path.join(BASE_DIR, "client", "session_string.txt")
COOKIES_PATH = os.path.join(BASE_DIR, "cookies")
DOWNLOADS_PATH = os.path.join(BASE_DIR, "downloads")
DOWNLOADS_TEMP_PATH = os.path.join(BASE_DIR, "downloads", "temp")
FONTS_PATH = os.path.join(BASE_DIR, "fonts")
SQLITE_DB_PATH = os.path.join(BASE_DIR, "database", "mydb.db")

MYSQL_DB_HOST = os.getenv("MYSQL_DB_HOST")
MYSQL_DB_USER = os.getenv("MYSQL_DB_USER")
MYSQL_DB_PASSWORD = os.getenv("MYSQL_DB_PASSWORD")
MYSQL_DB_NAME = os.getenv("MYSQL_DB_NAME")
MAX_INTENT_DOWNLOAD = int(os.getenv("MAX_INTENT_DOWNLOAD", "10"))

CLIENT_NAME = os.getenv("CLIENT_NAME", "my_account")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN", None)
PHONE_NUMBER = os.getenv("PHONE_NUMBER", None)
PASSWORD = os.getenv("PASSWORD", None)
