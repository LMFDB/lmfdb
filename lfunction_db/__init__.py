from base import app

import zero_search
app.register_module(zero_search.mod, url_prefix="/LfunctionDB/ZeroSearch")
