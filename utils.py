
# this is the caching wrapper, use it like this:
# @app.route(....)
# @cached()
# def func(): ...
from flask import request, make_response
from functools import wraps
from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache()
def cached(timeout=15 * 60, key='cache::%s::%s'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = key % (request.path, request.args)
            rv = cache.get(cache_key)
            if rv is None:
                rv = f(*args, **kwargs)
                cache.set(cache_key, rv, timeout=timeout)
            ret = make_response(rv)
            # this header basically says that any cache can store this infinitely long
            ret.headers['Cache-Control'] = 'max-age=360000, public'
            return ret
        return decorated_function
    return decorator

