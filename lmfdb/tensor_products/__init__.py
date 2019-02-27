# -*- coding: utf-8 -*-
from lmfdb.base import app
from lmfdb.utils import make_logger
from flask import Blueprint

tensor_products_page = Blueprint(
    "tensor_products", __name__, template_folder='templates', static_folder="static")
tensor_products_logger = make_logger("tensor_products", hl=True)

@tensor_products_page.context_processor
def body_class():
    return {'body_class': 'tensor_products'}

import main
assert main #silence pyflakes

app.register_blueprint(tensor_products_page, url_prefix="/TensorProducts")
