# -*- coding: utf-8 -*-

from main import (login_page, login_manager, admin_required,
                  housekeeping, FLASK_LOGIN_VERSION, FLASK_LOGIN_LIMIT)
assert admin_required # silence pyflakes
assert housekeeping # silence pyflakes

from lmfdb.base import app

from lmfdb.utils import make_logger
from distutils.version import StrictVersion


# secret key, necessary for sessions, and sessions are
# in turn necessary for users to login
app.secret_key = '9af"]ßÄ!_°$2ha€42~µ…010'

login_manager.init_app(app)

app.register_blueprint(login_page, url_prefix="/users")

users_logger = make_logger("users", hl=True)

if StrictVersion(FLASK_LOGIN_VERSION) < StrictVersion(FLASK_LOGIN_LIMIT):
    users_logger.warning("DEPRECATION-WARNING: flask-login is older than version {version}. "
          "Versions older than {version} have different functionality and may stop working in the future. "
          "Consider updating, perhaps through `sage -pip install flask-login`."
          .format(version=FLASK_LOGIN_LIMIT))
