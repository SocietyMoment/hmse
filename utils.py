import os
from typing import Optional
from flask import Blueprint
from jinja2 import Markup
import posix_ipc

MESSAGE_QUEUE_NAME = "/HMSE_orderqueue"

DB_NAME = os.environ.get("MARIADB_DATABASE")
DB_USER = os.environ.get("MARIADB_USER")
DB_PASSWORD = os.environ.get("MARIADB_PASSWORD")
DB_HOST = os.environ.get("DB_HOST")

DRAMA_BASE_URL = os.environ.get("DRAMA_BASE_URL")
DRAMA_CLIENT_ID = os.environ.get("DRAMA_CLIENT_ID")
DRAMA_HOLDING_ACCOUNT_USERNAME = os.environ.get("DRAMA_HOLDING_ACCOUNT_USERNAME")
DRAMA_HOLDING_ACCOUNT_ACCESS_TOKEN = os.environ.get("DRAMA_HOLDING_ACCOUNT_ACCESS_TOKEN")

def open_message_queue(read: bool, write: bool) -> posix_ipc.MessageQueue:
    return posix_ipc.MessageQueue(MESSAGE_QUEUE_NAME, posix_ipc.O_CREAT, 500, read=read, write=write)

CHRLOOKUP = [""]+list(map(chr, range(65, 91)))
def ticker_format(val: int) -> str:
    ret = ""
    for _ in range(6):
        ret += CHRLOOKUP[val%27]
        val //= 27
    return ret

utils_bp = Blueprint('utils', __name__)

def format_money(money: Optional[int]) -> str:
    if money is None: return ""
    return '{:0,.2f}'.format(money/100)
utils_bp.add_app_template_filter(format_money)

def format_datetime(timestamp: int) -> str:
    return Markup("<span data-timestamp='"
        + str(timestamp)
        + "' class='timestamp-format'></span>"
    )
utils_bp.add_app_template_filter(format_datetime)
