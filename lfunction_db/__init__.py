from base import app

import main
app.register_blueprint(main.mod, url_prefix="/LfunctionDB")
