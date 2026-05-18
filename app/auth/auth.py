from functools import wraps

from flask import redirect, session, url_for
from werkzeug.security import check_password_hash

from database import get_user_by_username


def authenticate(username: str, password: str) -> dict | None:
    user = get_user_by_username(username)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view
