#-*- coding: utf-8 -*-
import os

class CocalcWrap():
    """Wrap the application in this middleware
        if you are running Flask in Cocalc

    - app -- the WSGI application
    """

    def __init__(self, app):
        self.app = app
        from .config import Configuration
        flask_options = Configuration().get_flask()
        self.app_root = '/' + os.environ['COCALC_PROJECT_ID'] + "/server/" + str(flask_options['port'])

    def __call__(self, environ, start_response):
        environ["SCRIPT_NAME"] = self.app_root
        return self.app(environ, start_response)
