from functools import wraps
from flask import make_response, redirect
def redirect_no_cache(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        response = make_response(redirect(f(*args, **kwds), 307))
        response.headers['Cache-Control'] = 'no-cache, no-store'
        return response
    return wrapper
