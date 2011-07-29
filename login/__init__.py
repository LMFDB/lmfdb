from base import app

import main
app.register_module(main.mod, url_prefix="/user")

from pwdmanager import login_manager
