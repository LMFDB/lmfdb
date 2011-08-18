# -*- coding: utf-8 -*-
from knowledge import knowledge_page
from base import app

app.register_blueprint(knowledge_page, url_prefix="/knowledge")

