from heapq import heappop, heappush
from flask import Blueprint
import posix_ipc
from models import Order, Position, Match, User, get_time, ORDER_BUY, Stonk
from utils import open_message_queue, safe_get_or_create

buys: dict[int, list[Order]] = {} # bids
sells: dict[int, list[Order]] = {} # asks

handled_orders: set[int] = set()

def execute_order(buy: Order, sell: Order, stonk_id: int) -> bool:
    # For now, assume that only one orderbook is running at a time
    # then the things that may have race conditions are
    # just the user's moneys

    # this completely fails the match if precondition
    # fail and kicks out the offending order(s).
    # more sophisticated partial matchings can
    # prolly be done

    #TODO: use locking to deal with order cancellation

    match = Match(seller_order_id = sell, buyer_order_id=buy, happened_time=get_time(), stonk_id=stonk_id)
    match.quantity = min(buy.quantity, sell.quantity)

    match.price = (buy.price+sell.price) // 2
    spent = match.quantity * match.price

    buy_pos, _ = safe_get_or_create(Position,
        user_id = buy.user_id,
        stonk_id = stonk_id,
        defaults = {"quantity": 0}
    )
    sell_pos, _ = safe_get_or_create(Position,
        user_id = sell.user_id,
        stonk_id = stonk_id,
        defaults = {"quantity": 0}
    )

    if sell_pos.quantity < match.quantity:
        sell.cancelled = True
        sell.cancelled_time = get_time()
        sell.cancelled_reason = Order.CANCEL_REASONS.INSUFFICIENT_POSITION
        sell.save()
        return False

    # TODO: readd this
    # if buy.user.balance < spent:
    #    return False

    #TODO: use transactions for actual
    # db issues and speeeeed

    succ = User.update(balance=User.balance-spent).where(User.id==buy.user_id, User.balance>=spent).execute()
    if not succ:
        buy.cancelled = True
        buy.cancelled_time = get_time()
        buy.cancelled_reason = Order.CANCEL_REASONS.INSUFFICIENT_BALANCE
        buy.save()
        return False

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

    return True

def process_order(order: Order) -> None:
    if order.id in handled_orders: return

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

        execute_order(buy, sell, order.stonk_id)

        if buy.quantity and not buy.cancelled: heappush(cur_buys, buy)
        if sell.quantity and not sell.cancelled: heappush(cur_sells, sell)

def build_orderbook() -> None:
    """ Runs on startup to build orderbook from db"""

    for order in Order.select().where(Order.cancelled==False, Order.quantity!=0).order_by(Order.created_time):
        process_order(order)

def handle_queue(mq: posix_ipc.MessageQueue) -> None:
    print("Starting queue processor")
    print()

    while 1:
        msg, _ = mq.receive()
        order_id = int(msg)
        order = Order.get_or_none(Order.id==order_id)
        if order is None:
            print("Non existent order id: " + str(order_id))
            continue

        process_order(order)

orderbook_bp = Blueprint('orderbook', __name__)

@orderbook_bp.cli.command("run")
def run_orderbook():
    mq = open_message_queue(True, False)
    build_orderbook()
    handle_queue(mq)

