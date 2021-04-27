# -*- coding: utf-8 -*-
from __future__ import absolute_import
from lmfdb.app import app
from lmfdb.logger import make_logger
from flask import Blueprint, request, redirect
from lmfdb.api2.searchers import register_search_function

local_fields_page = Blueprint("local_fields", __name__, template_folder='templates', static_folder="static")
logger = make_logger(local_fields_page)


@local_fields_page.context_processor
def body_class():
    return {'body_class': 'local_fields'}

from . import main
assert main

from six.moves.urllib.parse import urlparse, urlunparse
@local_fields_page.before_request
def redirect_local():
        urlparts = urlparse(request.url)
        if 'LocalNumberField' in urlparts.path:
            urlparts = urlparts._replace(path=urlparts.path.replace('LocalNumberField', 'padicField'))
            return redirect(urlunparse(urlparts), 301)
        return


app.register_blueprint(local_fields_page, url_prefix="/padicField")

register_search_function(
    "$p$-adic_fields",
    "$p$-adic fields",
    "Search over $p$-adic fields",
    auto_search = 'lf_fields'
)
