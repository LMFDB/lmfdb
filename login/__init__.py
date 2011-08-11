from pwdmanager import login_manager
from main import user_page

from base import app
#app.register_blueprint(user_page, url_prefix="/user")
app.register_module(user_page, url_prefix="/user")
