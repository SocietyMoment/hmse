from decimal import Decimal
from flask import Blueprint, render_template, request, abort, redirect
from models import Stonk, Order, ORDER_BUY, ORDER_SELL, get_time
from auth import login_required
from utils import open_message_queue

stonks_bp = Blueprint('stonks', __name__)

@stonks_bp.app_context_processor
def jinja_stonks_list():
    return dict(all_stonks=Stonk.select(Stonk.id, Stonk.name))

@stonks_bp.route("/stonks")
@login_required(fail=False)
def stonks_list(user):
    return render_template("all_stonks.html", user=user, stonks=Stonk.select())

def return_stonk_view(user, ticker: int):
    stonk = Stonk.get_or_none(Stonk.id==ticker)
    if stonk is None:
        abort(404)
    return render_template("single_stonk.html", user=user, stonk=stonk)

@stonks_bp.route("/stonks/<int:ticker_num>")
@login_required(fail=False)
def stonk_single_num(user, ticker_num: int):
    return return_stonk_view(user, ticker_num)

@stonks_bp.route("/stonks/<string:ticker>")
@login_required(fail=False)
def stonk_single_str(user, ticker):
    return return_stonk_view(user, Stonk.convert_ticker(ticker))


mq = None

@stonks_bp.route("/trade", methods=["GET", "POST"])
@login_required()
def trade_stonk(user):
    stonk = Stonk.get_or_none(Stonk.id==int(request.args.get("id")))
    if stonk is None:
        abort(404)

    if request.method=="GET":
        return render_template("trade_stonk.html", user=user, stonk=stonk)

    price = round(Decimal(request.form.get("price"))*100)
    quantity = int(request.form.get("quantity"))
    buysell = request.form.get("buy_sell")

    if price<=0 or quantity<=0:
        abort(400)

    order = Order.create(
        user_id = user.id,
        type = ORDER_BUY if buysell=="buy" else ORDER_SELL,
        price = price,
        quantity = quantity,
        original_quantity = quantity,
        stonk_id = stonk.id,
        created_time = get_time(),
        cancelled = False,
    )

    global mq
    if mq is None:
        mq = open_message_queue(False, True)
    mq.send(str(order.id))

    return redirect('/stonks/'+stonk.ticker())

@stonks_bp.route("/cancel_order", methods=["POST"])
@login_required()
def cancel_order(user):
    order = Order.get_or_none(Order.id==int(request.args.get("id")))
    if (order is None) or (order.user_id != user.id):
        return {"error": "Order with id %d not found" % int(request.args.get("id"))}, 404

    if order.cancelled:
        return {"error": "Order with id %d not found" % int(request.args.get("id"))}, 409

    #TODO race conditions

    succ = Order.update(
        cancelled=True,
        cancelled_time=get_time(),
        cancelled_reason=Order.CANCEL_REASONS.USER_REQUEST,
    ).where(
        Order.id==order.id
    ).execute()

    if succ==0:
        return {"error": "Failed to update database"}, 500

    return {"message": "successfully cancelled order"}, 200

