import os
from typing import Optional
from flask import Blueprint
from jinja2 import Markup
import posix_ipc

MESSAGE_QUEUE_NAME = "/HMSE_orderqueue"

#TODO: Fix names
DB_NAME = os.environ.get("DB_NAME")
BASE_URL = os.environ.get("BASE_URL")
CLIENT_ID = os.environ.get("CLIENT_ID")
HOLDING_ACCOUNT_USERNAME = os.environ.get("HOLDING_ACCOUNT_USERNAME")
HOLDING_ACCOUNT_ACCESS_TOKEN = os.environ.get("HOLDING_ACCOUNT_ACCESS_TOKEN")

def open_message_queue(read: bool, write: bool) -> posix_ipc.MessageQueue:
    return posix_ipc.MessageQueue(MESSAGE_QUEUE_NAME, posix_ipc.O_CREAT, 500, read=read, write=write)

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
