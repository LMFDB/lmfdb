# -*- coding: utf-8 -*-

from pwdmanager import login_manager
from main import user_page

from base import app

# secret key, necessary for sessions, and sessions are
# in turn necessary for users to login
app.secret_key = '9af"]ßÄ!_°$2ha€42~µ…010'

from login import login_manager
login_manager.setup_app(app)

#app.register_blueprint(user_page, url_prefix="/user")
app.register_module(user_page, url_prefix="/user")
