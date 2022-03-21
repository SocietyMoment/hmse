import os
from gevent import monkey
if os.environ.get("FLASK_ENV")!="development":
    monkey.patch_all()
from flask import Flask, render_template, request, Blueprint
from models import db, models_bp, Position, Stonk
from auth import auth_bp, login_required
from orderbook import orderbook_bp
from admin import admin_bp
from stonks import stonks_bp
from user import user_bp
from text_pages import text_bp
from utils import utils_bp

app = Flask(__name__, template_folder='.')

app.register_blueprint(auth_bp)
app.register_blueprint(orderbook_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(stonks_bp)
app.register_blueprint(user_bp)
app.register_blueprint(models_bp)
app.register_blueprint(utils_bp)
app.register_blueprint(text_bp)

app.url_map.strict_slashes = False

if os.environ.get("FLASK_ENV")=="development":
    app.register_blueprint(Blueprint('images', __name__, static_folder='img'))
    app.debug = True

@app.before_request
def _db_connect():
    db.connect()

@app.teardown_request
def _db_close(exc):
    # I copied this from peewee docs
    # so i dont wanna mess with it
    # pylint: disable=unused-argument
    if not db.is_closed():
        db.close()

@app.route("/")
@login_required(fail=False)
def root(user):
    if user is None:
        return render_template('index.html')

    positions = Position.select(
        Position.user_id,
        Position.quantity,
        Position.stonk_id,
        Stonk.id,
        Stonk.latest_price,
    ).join(Stonk).where(
        Stonk.id==Position.stonk_id,
        Position.user_id==user.id,
        Position.quantity!=0
    )

    return render_template('dashboard.html', user=user,
        positions=positions, welcome='welcome' in request.args)

