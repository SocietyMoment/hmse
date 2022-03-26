from typing import Union
import uuid
import json
import urllib
import functools
from flask import redirect, Blueprint, make_response, request, abort, render_template
import requests
from models import User, get_time, LoginSession, safe_get_or_create
from utils import DRAMA_BASE_URL, DRAMA_CLIENT_ID

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login")
def login():
    drama_auth_url = DRAMA_BASE_URL+"authorize/?client_id="+DRAMA_CLIENT_ID

    redir = request.args.get("redirect")
    if redir:
        resp = make_response(render_template("login.html", drama_auth_url=drama_auth_url))
        resp.set_cookie('redirect_url', redir)
        return resp

    resp = make_response(redirect(drama_auth_url))
    resp.set_cookie('redirect_url', '', expires=0)
    return resp

def get_user_from_drama(access_token) -> tuple[User, bool]:
    resp = requests.get(
        DRAMA_BASE_URL+"@me",
        headers={"Authorization": access_token}
    ).json()

    return safe_get_or_create(User, id=resp["id"], defaults={
        "username": resp["username"],
        "profile_pic_url": resp["profile_url"],
        "balance": 0,
        "created_time": get_time(),
        "show_push_notifications": True,
    })

@auth_bp.route("/handle_login")
def handle_login():
    access_token = request.args.get("token")
    if not access_token:
        abort(401)

    user, new = get_user_from_drama(access_token)
    session = LoginSession.create(
        user_id = user.id,
        drama_access_token=access_token,
        created_time = get_time(),
    )

    redirect_url = request.cookies.get("redirect_url") or '/'
    #TODO: welcome
    if new:
        redirect_url += '?welcome'

    resp = make_response(redirect(redirect_url))
    resp.set_cookie('session_id', str(session.id), expires=2147483647)
    resp.set_cookie('redirect_url', '', expires=0)
    return resp

def check_login() -> Union[User, None]:
    if "session_id" not in request.cookies:
        return None

    session_id = uuid.UUID(request.cookies["session_id"])
    session = LoginSession.select(LoginSession.user).where(LoginSession.id == session_id).first()

    if session is None:
        return None

    return session.user

def login_required(fail=True):
    def inner_decorator(route):
        @functools.wraps(route)
        def func(*args, **kwargs):
            user = check_login()
            if user is None and fail:
                return redirect(
                    'login?redirect='+
                    urllib.parse.quote_plus(request.url)
                )

            return route(user, *args, **kwargs)

        return func
    return inner_decorator

@auth_bp.route("/subscribe_notifications", methods=["POST"])
@login_required()
def subscribe_notifications(user):
    sub = request.json

    session_id = uuid.UUID(request.cookies["session_id"])
    LoginSession.update(
        notification_subscription = json.dumps(sub)
    ).where(LoginSession.id == session_id).execute()

    return {'success':True}, 200

@auth_bp.route("/logout")
@login_required()
def logout(_user):
    session_id = uuid.UUID(request.cookies["session_id"])
    LoginSession.delete().where(LoginSession.id == session_id).execute()

    resp = make_response(redirect('/'))
    resp.set_cookie('session_id', '', expires=0)
    return resp

