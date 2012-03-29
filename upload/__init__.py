# -*- coding: utf-8 -*-
from upload import upload_page
from base import app

app.register_blueprint(upload_page, url_prefix="/upload")

