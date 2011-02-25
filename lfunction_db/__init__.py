from base import app

import main
app.register_module(main.mod, url_prefix="/LfunctionDB")
