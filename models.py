import time
import json
import functools
import collections
from typing import TypeVar, Type, Iterator, Optional
import enum
import uuid
import methodtools
from flask import Blueprint
from pywebpush import webpush
import peewee as pw
from playhouse.pool import PooledMySQLDatabase
from utils import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, ticker_format, VAPID_PRIVATE_KEY

models_bp = Blueprint('models', __name__)

#TODO: turn on caching
db = PooledMySQLDatabase(
    DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    max_connections=50,
    stale_timeout=300,
)

# all times in db are integer microseconds
# even when not needed, for easyness
def get_time() -> int:
    return int(time.time() * 1000000)

def create_uuid() -> uuid.UUID:
    return uuid.uuid4()

# Peewee requires this
class BaseModel(pw.Model):
    class Meta:
        database = db

ModelType = TypeVar('ModelType', bound=BaseModel)
def safe_get_or_create(model: Type[ModelType], *args, defaults=None, **kwargs) -> tuple[ModelType, bool]:
    if defaults is None:
        defaults = {}

    obj = model.get_or_none(*args, **kwargs)
    if obj is not None: return obj, False

    try:
        with db.atomic():
            return model.create(*args, **kwargs, **defaults), True
    except pw.IntegrityError:
        return model.get(*args, **kwargs), False

class User(BaseModel):
    id = pw.IntegerField(primary_key=True) # rdrama's uid

    username = pw.CharField(null=False) # again, from rdrama
    # idk what's the best way to sync this, maybe reload button
    profile_pic_url = pw.CharField(null=True) # again, from rdrama

    balance = pw.IntegerField(null=False) # in cents, like all money
    created_time = pw.BigIntegerField(null=False)

    show_push_notifications = pw.BooleanField(null=False)

    @methodtools.lru_cache(maxsize=None)
    def get_position(self, stonk_id: int) -> Optional['Position']:
        return Position.select().where(
            Position.user_id==self.id,
            Position.quantity!=0,
            Position.stonk_id==stonk_id,
        ).first()

    @methodtools.lru_cache(maxsize=None)
    def get_position_with_pl(self, stonk_id: int) -> Optional['Position']:
        """ Does cost basis calculation for profit/loss. FIFO selection"""
        pos = self.get_position(stonk_id)
        if pos is None: return None

        matches = self.match_history(stonk_id)[::-1]
        ids = collections.Counter([i.id for i in matches])
        owned = collections.deque()
        for match in matches:
            if ids[match.id]>1: continue

            if match.buy:
                owned.appendleft([match.price, match.quantity])
            else:
                quantity = match.quantity
                while quantity:
                    # this shouldn't happen, but i don't wanna risk it
                    # in case some manual weirdness happens
                    if not owned:
                        owned.append([0, quantity])

                    cur = min(quantity, owned[-1][1])
                    quantity -= cur
                    owned[-1][1] -= cur
                    if owned[-1][1]==0:
                        owned.pop()

        tot_cost = 0
        for trans in owned:
            tot_cost += trans[0]*trans[1]
        pos.tot_cost = tot_cost

        return pos

    @methodtools.lru_cache(maxsize=None)
    def open_orders(self, stonk_id: int) -> Iterator['Order']:
        return Order.select().where(
            Order.user_id==self.id,
            Order.stonk_id==stonk_id,
            ~Order.cancelled,
            Order.quantity!=0
        )

    @methodtools.lru_cache(maxsize=None)
    def match_history(self, stonk_id: int) -> list['Match']:
        return list(Match.select(
            Match,
            Order.id,
            Order.user_id,
            Order.stonk_id,
            (Order.id==Match.buyer_order_id).alias("buy")
        ).join(
            Order, on=(Order.id==Match.seller_order_id) |
            (Order.id==Match.buyer_order_id),
        ).where(
            Order.user_id==self.id,
            Order.stonk_id==stonk_id
        ).order_by(Match.happened_time.desc()))

    @methodtools.lru_cache(maxsize=None)
    def equity(self) -> int:
        return (Position.select(
            pw.fn.SUM(Position.quantity*Stonk.latest_price),
            Position.user_id
        ).join(Stonk).where(
            Position.user_id==self.id
        ).scalar() or 0) + self.balance

    @methodtools.lru_cache(maxsize=None)
    def get_unread_notifs(self) -> Iterator['Notification']:
        return Notification.select().where(
            Notification.user_id==self.id,
            ~Notification.read
        ).order_by(Notification.created_time.desc())

class LoginSession(BaseModel):
    id = pw.BinaryUUIDField(primary_key=True, default=create_uuid)
    user = pw.ForeignKeyField(User, backref='sessions', null=False, lazy_load=True)
    drama_access_token = pw.CharField(null=False)

    created_time = pw.BigIntegerField(null=False)
    
    notification_subscription = pw.TextField(null=True)

class Stonk(BaseModel):
    id = pw.IntegerField(primary_key=True)
    name = pw.CharField(null=False)
    description = pw.TextField(null=True)

    latest_price = pw.IntegerField(null=False)

    # This is the google news search term
    # Check news.py to see how it is used
    search_term = pw.CharField(null=False)

    # ticker is encoded as an int, so
    # this gives it as a string
    # allows for up to 6 letter tickers
    def ticker(self) -> str:
        return ticker_format(self.id)

    @staticmethod
    def convert_ticker(ticker: str) -> int:
        ret = 0
        power = 1
        for char in ticker.upper():
            ret += (ord(char)-64)*power
            power *= 27
        return ret

    def latest_trades(self, limit: int=5) -> Iterator['Match']:
        return Match.select(
            Match.price,
            Match.quantity,
            Match.happened_time,
        ).where(
            Match.stonk_id==self.id,
            Match.seller_order_id!=None # pylint: disable=singleton-comparison
        ).order_by(Match.happened_time.desc()).limit(limit)

    # def get_latest_price(self) -> int:
    #     return (Match.
    #         select(Match.price, Match.happened_time).
    #         where(Match.stonk_id == self.id).
    #         order_by(Match.happened_time.desc())
    #     ).first() or 0

# import logging
# logger = logging.getLogger('peewee')
# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)
class Position(BaseModel):
    id = pw.BinaryUUIDField(primary_key=True, default=create_uuid)

    user = pw.ForeignKeyField(User, backref='positions', null=False, lazy_load=True)

    stonk = pw.ForeignKeyField(Stonk, null=False, lazy_load=True)
    quantity = pw.IntegerField(null=False)

ORDER_BUY = True
ORDER_SELL = False

@functools.total_ordering
class Order(BaseModel):
    """An order in the orderbook"""

    id = pw.AutoField()

    user = pw.ForeignKeyField(User, backref='orders', null=False, lazy_load=True)

    type = pw.BooleanField(null=False)
    price = pw.IntegerField(null=False)
    quantity = pw.IntegerField(null=False)
    original_quantity = pw.IntegerField(null=False)

    stonk = pw.ForeignKeyField(Stonk, backref='orders', null=False, lazy_load=True)

    created_time = pw.BigIntegerField(null=False)

    class CANCEL_REASONS(enum.IntEnum):
        # This is an enum, so I like
        # snake naming (like constants)
        # pylint: disable=invalid-name
        USER_REQUEST = 1
        INSUFFICIENT_BALANCE = 2
        INSUFFICIENT_POSITION = 3
        GIFT_RECV_ORDER = 4
        UNKOWN_REASON = 100

    cancelled = pw.BooleanField(null=False)
    cancelled_time = pw.BigIntegerField(null=True)
    cancelled_reason = pw.IntegerField(null=True)

    # These comparators are for order book only
    def __eq__(self, other):
        return self.price==other.price and self.created_time==other.created_time

    def __lt__(self, other):
        if self.type==ORDER_SELL:
            return self.price<other.price or (self.price==other.price and self.created_time<other.created_time)
        return self.price>other.price or (self.price==other.price and self.created_time<other.created_time)

models_bp.add_app_template_global(ORDER_BUY, "ORDER_BUY")
models_bp.add_app_template_global(ORDER_SELL, "ORDER_SELL")
models_bp.add_app_template_global(Order.CANCEL_REASONS, "CANCEL_REASONS")

class Match(BaseModel):
    """A transaction that happened"""

    id = pw.AutoField()

    seller_order = pw.ForeignKeyField(Order, backref='matches', null=True, lazy_load=True)
    buyer_order = pw.ForeignKeyField(Order, backref='matches', null=False, lazy_load=True)

    stonk = pw.ForeignKeyField(Stonk, null=False, lazy_load=True)

    price = pw.IntegerField(null=False)
    quantity = pw.IntegerField(null=False)

    happened_time = pw.BigIntegerField(null=False)

class Notification(BaseModel):
    id = pw.BinaryUUIDField(primary_key=True, default=create_uuid)

    user = pw.ForeignKeyField(User, backref='notifs', null=False, lazy_load=True)

    title = pw.CharField(null=False)
    text = pw.TextField(null=False)
    link = pw.TextField(null=True)
    color = pw.CharField(null=True)

    read = pw.BooleanField(null=False, default=False)
    created_time = pw.BigIntegerField(null=False)
    
    @staticmethod
    def create_and_send(user_id: int, title: str, text: str, color: str) -> None:
        """Create Notification object and send web push notifications"""
        Notification.create(
            user_id = user_id,
            title = title,
            text = text,
            color = color,
            created_time = get_time()
        )

        user = User.select(
            User.show_push_notifications
        ).where(User.id==user_id).first()

        if not user.show_push_notifications:
            return

        data = json.dumps({
            "title": title,
            "text": text,
            "color": color,
            "timestamp": int(get_time()/1000),
        })
        
        for login_session in LoginSession.select().where(
            LoginSession.user_id==user_id,
            LoginSession.notification_subscription!=None,
        ):
            webpush(
                json.loads(login_session.notification_subscription),
                data,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": "mailto:societymoment@protonmail.com"},
            )


        


