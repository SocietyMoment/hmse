from typing import Optional
from heapq import heappop, heappush
from flask import Blueprint
import posix_ipc
from models import db, Order, Position, Match, User, get_time, ORDER_BUY, Stonk, safe_get_or_create, Notification
from utils import open_message_queue, format_money, ticker_format

buys: dict[int, list[Order]] = {} # bids
sells: dict[int, list[Order]] = {} # asks

handled_orders: set[int] = set()

REASON_MAPPING = {
    Order.CANCEL_REASONS.INSUFFICIENT_BALANCE: "not enough balance",
    Order.CANCEL_REASONS.INSUFFICIENT_POSITION: "not enough stonks held",
}
def send_notif(order: Order, match: Optional[Match]) -> None:
    if match is None:
        title = "Order Failed"
        text = f"Failed to execute {'buy' if order.type==ORDER_BUY else 'sell'} order for {ticker_format(order.stonk_id)} because of: {REASON_MAPPING[order.cancelled_reason]}"
        color = "danger"
    else:
        if order.quantity!=0:
            title = "Order Partially Filled"
        else:
            title = "Order Filled"

        text = f"Successfully {'bought' if order.type==ORDER_BUY else 'sold'} {match.quantity} shares of {ticker_format(match.stonk_id)} at ${format_money(match.price)}."
        color = "success"

    Notification.create(
        user_id = order.user_id,
        title = title,
        text = text,
        color = color,
        created_time = get_time()
    )

def execute_order(buy: Order, sell: Order, stonk_id: int) -> tuple[Order, Order, bool]:
    # For now, assume that only one orderbook is running at a time
    # then the things that may have race conditions are
    # just the user's moneys

    with db.atomic():
        buy = Order.select().where(Order.id==buy.id).for_update().get()
        sell = Order.select().where(Order.id==sell.id).for_update().get()

        buy_user = User.select().where(User.id==buy.user_id).for_update().get()

        sell_pos, _ = safe_get_or_create(Position,
            user_id = sell.user_id,
            stonk_id = stonk_id,
            defaults = {"quantity": 0}
        )

        buy_pos, _ = safe_get_or_create(Position,
            user_id = buy.user_id,
            stonk_id = stonk_id,
            defaults = {"quantity": 0}
        )

        buy_pos = Position.select().where(Position.id==buy_pos.id).for_update().get()
        sell_pos = Position.select().where(Position.id==sell_pos.id).for_update().get()

        match = Match(seller_order_id = sell.id, buyer_order_id=buy.id, happened_time=get_time(), stonk_id=stonk_id)
        match.quantity = min(buy.quantity, sell.quantity)

        match.price = (buy.price+sell.price) // 2
        spent = match.quantity * match.price

        if sell.cancelled or buy.cancelled or buy.quantity==0 or sell.quantity==0:
            print("failed because of cancelled " + str(sell.id) + " | " + str(buy.id), flush=True)
            return buy, sell, False

        if sell_pos.quantity < match.quantity:
            sell.cancelled = True
            sell.cancelled_time = get_time()
            sell.cancelled_reason = Order.CANCEL_REASONS.INSUFFICIENT_POSITION
            sell.save()
            send_notif(sell, None)
            print("failed because of not enough stonk " + str(sell.id) + " | " + str(buy.id), flush=True)
            return buy, sell, False

        if buy_user.balance < spent:
            buy.cancelled = True
            buy.cancelled_time = get_time()
            buy.cancelled_reason = Order.CANCEL_REASONS.INSUFFICIENT_BALANCE
            buy.save()
            send_notif(buy, None)
            print("failed because of not enough cash " + str(sell.id) + " | " + str(buy.id), flush=True)
            return buy, sell, False

        User.update(balance=User.balance-spent).where(User.id==buy.user_id).execute()
        User.update(balance=User.balance+spent).where(User.id==sell.user_id).execute()

        Position.update(quantity=Position.quantity+match.quantity).where(Position.id==buy_pos.id).execute()
        Position.update(quantity=Position.quantity-match.quantity).where(Position.id==sell_pos.id).execute()
        #TODO autodelete position when 0

        Stonk.update(latest_price=match.price).where(Stonk.id==stonk_id).execute()

        buy.quantity -= match.quantity
        sell.quantity -= match.quantity
        buy.save()
        sell.save()

        match.save()

        send_notif(buy, match)
        send_notif(sell, match)
        print("succeeded order " + str(sell.id) + " | " + str(buy.id), flush=True)
        return buy, sell, True

def process_order(order: Order) -> None:
    if order.id in handled_orders: return

    print("Processing order " + str(order.id), flush=True)

    if order.stonk_id not in buys:
        buys[order.stonk_id] = []
        sells[order.stonk_id] = []

    cur_buys = buys[order.stonk_id]
    cur_sells = sells[order.stonk_id]

    if order.type == ORDER_BUY:
        heappush(cur_buys, order)
    else:
        heappush(cur_sells, order)

    handled_orders.add(order.id)

    while len(cur_buys) and len(cur_sells) and cur_buys[0].price >= cur_sells[0].price:
        buy = heappop(cur_buys)
        sell = heappop(cur_sells)

        buy, sell, _ = execute_order(buy, sell, order.stonk_id)

        if buy.quantity and not buy.cancelled: heappush(cur_buys, buy)
        if sell.quantity and not sell.cancelled: heappush(cur_sells, sell)

def build_orderbook() -> None:
    """ Runs on startup to build orderbook from db"""

    for order in Order.select().where(
        ~Order.cancelled,
        Order.quantity!=0
    ).order_by(Order.created_time):
        process_order(order)

def handle_queue(message_queue: posix_ipc.MessageQueue) -> None:
    print("Starting queue processor")
    print(flush=True)

    while 1:
        msg, _ = message_queue.receive()
        order_id = int(msg)
        order = Order.get_or_none(Order.id==order_id)
        if order is None:
            print("Non existent order id: " + str(order_id), flush=True)
            continue

        process_order(order)

orderbook_bp = Blueprint('orderbook', __name__)

@orderbook_bp.cli.command("run")
def run_orderbook():
    message_queue = open_message_queue(True, False)
    build_orderbook()
    handle_queue(message_queue)

