import shutil
from flask import Blueprint
import click
from models import db, Stonk, BaseModel, Order, Match, Position, User, safe_get_or_create, ORDER_BUY, get_time, Notification

admin_bp = Blueprint('admin', __name__)

@admin_bp.cli.command("reset-db")
def reset_db():
    click.confirm('Are you sure you want to completely erase the db?', abort=True)

    db.drop_tables(BaseModel.__subclasses__())
    db.create_tables(BaseModel.__subclasses__())

@admin_bp.cli.command("create-stonk")
@click.argument("ticker", required=True)
@click.argument("name", required=True)
@click.option("-d", "--description", type=click.File('r'), help="file containing blurb about the stonk")
@click.option("-i", "--image_file", type=click.Path(exists=True), help="icon for stonk (square)", default="img/no-image.png")
def create_stonk(ticker, name, image_file, description):
    """TICKER can be up to 6 chars"""

    if description is not None:
        description = description.read()
    if description is None:
        description = ""

    click.echo("You are about to create a stonk with the following values:")
    click.echo("")
    click.echo("Ticker: " + ticker)
    click.echo("Id: " + str(Stonk.convert_ticker(ticker)))
    click.echo("Name: " + name)
    click.echo("Description: " + str(description))
    # TODO: fix image file on docker
    click.echo("Image File (this is broken on docker btw): " + image_file)
    click.echo("")

    click.confirm('Do you want to continue?', abort=True)

    stonk = Stonk.create(
        id = Stonk.convert_ticker(ticker),
        name = name,
        description = description,
        latest_price = 0
    )
    shutil.copy2(image_file, "img/stonk-icons/icon_" + str(stonk.id))

    assert Stonk.get_or_none(Stonk.id==stonk.id) is not None
    click.echo("success!")

@admin_bp.cli.command("give-stonk")
@click.argument("ticker", required=True)
@click.argument("userid", required=True, type=int)
@click.argument("quantity", required=True, type=click.IntRange(1))
def give_stonk(ticker, userid, quantity):
    """TICKER can be up to 6 chars"""

    tid = Stonk.convert_ticker(ticker)

    stonk = Stonk.get_or_none(Stonk.id==tid)
    if stonk is None:
        raise click.BadOptionUsage("ticker", "stonk doesn't exist")

    user = User.get_or_none(User.id==userid)
    if user is None:
        raise click.BadOptionUsage("userid", "user doesn't exist")



    click.echo(f"You are about to give {quantity} {ticker} to {user.username} (user id: {user.id}).")
    click.echo("")
    click.confirm('Do you want to continue?', abort=True)

    fake_order = Order.create(
        user_id=user.id,
        type = ORDER_BUY,
        price = 0,
        quantity = 0,
        original_quantity = quantity,
        stonk_id = stonk.id,
        created_time = get_time(),
        cancelled = True,
        cancelled_reason = Order.CANCEL_REASONS.GIFT_RECV_ORDER,
    )

    Match.create(
        seller_order = None,
        buyer_order = fake_order,
        stonk_id = stonk.id,
        price = 0,
        quantity = quantity,
        happened_time = get_time(),
    )

    position, _ = safe_get_or_create(Position,
        user_id = user.id,
        stonk_id = stonk.id,
        defaults = {"quantity": 0}
    )

    succ = Position.update(quantity = Position.quantity+quantity).where(Position.id==position.id).execute()

    assert succ!=0
    click.echo("success!")

@admin_bp.cli.command("send-notification")
@click.argument("userid", required=True, type=int)
@click.argument("title", required=True)
@click.argument("message", required=True)
@click.option("-c", "--color")
def send_notif(userid, title, message, color):
    user = User.get_or_none(User.id==userid)
    if user is None:
        raise click.BadOptionUsage("userid", "user doesn't exist")

    Notification.create_and_send(
        userid,
        title,
        message,
        color,
    )

