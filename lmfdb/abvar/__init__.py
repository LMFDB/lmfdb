from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint

abvar_page = Blueprint(
    "abvar", __name__, template_folder="templates", static_folder="static"
)
abvar_logger = make_logger(abvar_page)


@abvar_page.context_processor
def body_class():
    return {"body_class": "abvar"}


app.register_blueprint(abvar_page, url_prefix="/Variety/Abelian")

# API2 has been disabled for now
#from lmfdb.api2.searchers import register_search_function
#register_search_function(
#    "abvar",
#    "Abelian varieties",
#    "Search over abelian varieties",
#    auto_search="av_fqisog",
#    inv=["av", "av_fqisog"],
#)
