
# this is the caching wrapper, use it like this:
# @app.route(....)
# @cached()
# def func(): ...
from flask import request, make_response
from functools import wraps
from werkzeug.contrib.cache import SimpleCache

from copy import copy
from werkzeug import cached_property
from flask import url_for

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

class MongoDBPagination(object):
    def __init__(self, query, per_page, page, endpoint, endpoint_params):
        self.query = query
        self.per_page = int(per_page)
        self.page = int(page)
        self.endpoint = endpoint
        self.endpoint_params = endpoint_params

    @cached_property
    def count(self):
        return self.query.count(True)

    @cached_property
    def entries(self):
        return self.query.skip(self.start).limit(self.per_page)

    has_previous = property(lambda x: x.page > 1)
    has_next = property(lambda x: x.page < x.pages)
    pages = property(lambda x: max(0, x.count - 1) // x.per_page + 1)
    start = property(lambda x: (x.page - 1) * x.per_page)
    end = property(lambda x: x.start + x.per_page - 1)

    @property
    def previous(self):
        kwds = copy(self.endpoint_params)
        kwds['page'] = self.page - 1
        return url_for(self.endpoint, **kwds)

    @property
    def next(self):
        kwds = copy(self.endpoint_params)
        kwds['page'] = self.page + 1
        return url_for(self.endpoint, **kwds)

class LazyMongoDBPagination(MongoDBPagination):
    @cached_property
    def has_next(self):
        return self.query.skip(self.start).limit(self.per_page+1).count(True) > self.per_page

    @property
    def count(self):
        raise NotImplementedError
    
    @property
    def pages(self):
        raise NotImplementedError


def orddict_to_strlist(v):
    """
    v -- dictionary with int keys
    """
