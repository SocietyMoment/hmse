from typing import Type
import os
from flask import Blueprint
import peewee as pw
import posix_ipc
from models import db, ModelType

MESSAGE_QUEUE_NAME = "/HMSE_orderqueue"

BASE_URL = os.environ.get("BASE_URL")
CLIENT_ID = os.environ.get("CLIENT_ID")
HOLDING_ACCOUNT_USERNAME = os.environ.get("HOLDING_ACCOUNT_USERNAME")
HOLDING_ACCOUNT_ACCESS_TOKEN = os.environ.get("HOLDING_ACCOUNT_ACCESS_TOKEN")

def safe_get_or_create(model: Type[ModelType], *args, defaults={}, **kwargs) -> tuple[ModelType, bool]:
    obj = model.get_or_none(*args, **kwargs)
    if obj is not None: return obj, False

    try:
        with db.atomic():
            return model.create(*args, **kwargs, **defaults), True
    except pw.IntegrityError:
        return model.get(*args, **kwargs), False

def open_message_queue(read: bool, write: bool) -> posix_ipc.MessageQueue:
    return posix_ipc.MessageQueue(MESSAGE_QUEUE_NAME, posix_ipc.O_CREAT, 500, read=read, write=write)

utils_bp = Blueprint('utils', __name__)

def format_money(money: int) -> str:
    return '{:0,.2f}'.format(money/100)
utils_bp.add_app_template_filter(format_money)
