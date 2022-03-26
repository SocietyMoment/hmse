import uuid
from flask import Blueprint, render_template, request, abort
import requests
from models import LoginSession, User, Notification
from auth import login_required
from utils import DRAMA_BASE_URL, DRAMA_HOLDING_ACCOUNT_USERNAME, DRAMA_HOLDING_ACCOUNT_ACCESS_TOKEN

user_bp = Blueprint('user', __name__)

@user_bp.route("/deposit", methods=["GET", "POST"])
@login_required()
def deposit(user):
    if request.method=="GET":
        return render_template("deposit.html", user=user)
    amount = int(request.form.get("amount"))

    session_id = uuid.UUID(request.cookies["session_id"])
    drama_access_token = LoginSession.select(
        LoginSession.drama_access_token).where(
        LoginSession.id == session_id).first().drama_access_token

    resp = requests.post(
        f"{DRAMA_BASE_URL}@{DRAMA_HOLDING_ACCOUNT_USERNAME}/transfer_coins",
        headers = {"Authorization": drama_access_token},
        data = {"amount": str(amount)}
    )

    if resp.status_code>=400:
        error = resp.json().get("error") or resp.json().get("message")
        return render_template("deposit.html", error=error, user=user)

    trans = int(resp.json()["message"].split()[0])
    User.update(balance=User.balance+trans*100).where(User.id==user.id).execute()
    user.balance += trans
    return render_template("deposit.html", success=f"Successfully added {trans} dramacoins to your balance!", user=user)

@user_bp.route("/withdraw", methods=["GET", "POST"])
@login_required()
def withdraw(user):
    if request.method=="GET":
        return render_template("withdraw.html", user=user)

    amount = int(request.form.get("amount"))

    if amount <= 0:
        abort(400)

    succ = User.update(balance=User.balance-amount*100).where(User.id==user.id, User.balance>=amount*100).execute()
    if not succ:
        return render_template("withdraw.html", error="Insufficient balance!", user=user)

    resp = requests.post(
        f"{DRAMA_BASE_URL}@{user.username}/transfer_coins",
        headers = {"Authorization": DRAMA_HOLDING_ACCOUNT_ACCESS_TOKEN},
        data = {"amount": str(amount)}
    )

    if resp.status_code>=400:
        User.update(balance=User.balance+amount*100).where(User.id==user.id).execute()

        error = resp.json().get("error") or resp.json().get("message")
        return render_template("withdraw.html", error=error, user=user)

    trans = int(resp.json()["message"].split()[0])
    user.balance -= amount*100
    return render_template("withdraw.html", success=f"Successfully added {trans} dramacoins to your rdrama account!", user=user)

@user_bp.route("/notifications")
@login_required()
def notifications(user):
    Notification.update(read=True).where(
        Notification.user_id==user.id,
        ~Notification.read
    ).execute()

    return render_template("notifications.html",
        user=user,
        notifs=user.notifs.order_by(Notification.created_time.desc())
    )

@user_bp.route("/settings")
@login_required()
def settings(user):
    return render_template("settings.html", user=user)

@user_bp.route("/update_settings", methods=["POST"])
@login_required()
def update_settings(user):
    show_notifs = request.json.get("show_notifications")
    User.update(
        show_push_notifications=show_notifs
    ).where(User.id==user.id).execute()

    return {}, 200

