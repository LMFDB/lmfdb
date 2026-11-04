import hmac
import secrets

from flask import abort, request, session


def csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def require_csrf_token():
    expected = session.get("_csrf_token")
    supplied = request.form.get("csrf_token", "")
    if not expected or not hmac.compare_digest(expected.encode(), supplied.encode()):
        abort(400, "Invalid CSRF token")
