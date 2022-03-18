from flask import Flask, render_template, request, Blueprint
from models import db, models_bp
from auth import auth_bp, login_required
from orderbook import orderbook_bp
from admin import admin_bp
from stonks import stonks_bp
from money import money_bp
from utils import format_money, utils_bp

app = Flask(__name__, template_folder='.')
app.debug = True

app.register_blueprint(auth_bp)
app.register_blueprint(orderbook_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(stonks_bp)
app.register_blueprint(money_bp)
app.register_blueprint(models_bp)
app.register_blueprint(utils_bp)

app.register_blueprint(Blueprint('images', __name__, static_folder='img'))

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
    return render_template('dashboard.html', user=user, welcome='welcome' in request.args)

