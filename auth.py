from typing import Union
import uuid
import functools
from flask import redirect, Blueprint, make_response, request, abort
import requests
from models import User, get_time, LoginSession
from utils import safe_get_or_create, BASE_URL, CLIENT_ID

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login")
def login():
    return redirect(BASE_URL+"authorize/?client_id="+CLIENT_ID)

def get_user_from_drama(access_token) -> tuple[User, bool]:
    resp = requests.get(
        BASE_URL+"@me",
        headers={"Authorization": access_token}
    ).json()

    return safe_get_or_create(User, id=resp["id"], defaults={
        "username": resp["username"],
        "profile_pic_url": resp["profile_url"],
        "balance": 0,
        "created_time": get_time(),
    })

@auth_bp.route("/handle_login")
def handle_login():
    access_token = request.args.get("token")
    if not access_token:
        abort(401)

    user, new = get_user_from_drama(access_token)
    session = LoginSession.create(user_id = user.id, drama_access_token=access_token)

    redirect_url = '/'
    if new:
        redirect_url += '?welcome'

    resp = make_response(redirect(redirect_url))
    resp.set_cookie('session_id', str(session.id))
    return resp

def check_login() -> Union[User, None]:
    if "session_id" not in request.cookies:
        return None

    session_id = uuid.UUID(request.cookies["session_id"])
    session = LoginSession.select(LoginSession.user).where(LoginSession.id == session_id).first()

    if session is None:
        return None

    return session.user

#TODO redirect urls
def login_required(fail=True):
    def inner_decorator(route):
        @functools.wraps(route)
        def func(*args, **kwargs):
            user = check_login()
            if user is None and fail:
                return redirect('/')

            return route(user, *args, **kwargs)

        return func
    return inner_decorator

@auth_bp.route("/logout")
@login_required()
def logout(_user):
    session_id = uuid.UUID(request.cookies["session_id"])
    LoginSession.delete().where(LoginSession.id == session_id).execute()

    resp = make_response(redirect('/'))
    resp.set_cookie('session_id', '', expires=0)
    return resp

