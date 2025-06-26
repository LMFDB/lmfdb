

from lmfdb.logger import make_logger
from lmfdb.app import app
from .main import (
    login_page,
    login_manager,
    admin_required,
    knowl_reviewer_required,
    housekeeping,
)

assert admin_required  # silence pyflakes
assert knowl_reviewer_required  # silence pyflakes
assert housekeeping  # silence pyflakes


login_manager.init_app(app)

app.register_blueprint(login_page, url_prefix="/users")

users_logger = make_logger("users", hl=True)
