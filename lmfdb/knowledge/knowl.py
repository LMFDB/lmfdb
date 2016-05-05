# -*- coding: utf-8 -*-
# the basic knowlege object, with database awareness, …
from lmfdb.knowledge import logger
from lmfdb.base import getDBConnection
from datetime import datetime
import pymongo
ASC = pymongo.ASCENDING
DSC = pymongo.DESCENDING


def get_knowls():
    _C = getDBConnection()
    knowls = _C.knowledge.knowls
# See issue #1169
#    try:
#        knowls.ensure_index('authors')
#        # _keywords is used for the full text search
#        knowls.ensure_index('title')
#        knowls.ensure_index('cat')
#        knowls.ensure_index('_keywords')
#    except pymongo.errors.OperationFailure:
#        pass
    return knowls


def get_meta():
    """
    collection of meta-documents, like categories
    """
    _C = getDBConnection()
    return _C.knowledge.meta


def get_deleted_knowls():
    _C = getDBConnection()
    return _C.knowledge.deleted_knowls


def save_history(knowl, who):
    """
    saves history tokens in a collection "history".
    each entry has the _id of the updated knowl and at least a timestamp
    and a reference to who has edtited it. also, the title is nice to
    avoid an additional lookup when listing the history!
    'state' can either be 'saved' (for the recent changes list) or 'locked'.
    TODO also calculate a diff with python's difflib and store it here.
    """
    history = getDBConnection().knowledge.history
#   See issue #1169
#   history.ensure_index("time")
    h_item = {'_id': knowl.id,
              'title': knowl.title,
              'time': datetime.utcnow(),
              'who': who,
              'state': 'saved'}
    history.save(h_item)


def get_history(limit=25):
    """
    returns the last @limit history items
    """
    history = getDBConnection().knowledge.history
    return history.find({'state': 'saved'}, sort=[('time', DSC)], limit=limit)


def is_locked(knowlid, delta_min=10):
    """
    returns a lock (as True), if there has been a lock in the last @delta_min minutes; else False.
    attention, it discards all locks prior to @delta_min!
    """
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    tdelta = timedelta(minutes=delta_min)
    time = now - tdelta
    history = getDBConnection().knowledge.history
    #try:
    history.remove({'state': 'locked', 'time': {'$lt': time}})
    #except:
    #    return None 
    # search for both: either locked OR has been saved in the last 10 min
    lock = history.find_one({'_id': knowlid, 'time': {'$gte': time}})
    return lock or False


def set_locked(knowl, who):
    """
    when a knowl is edited, a lock is created. who is the user id.
    """
    history = getDBConnection().knowledge.history
# See issue #1169
#   history.ensure_index("time")
    lock_item = {'_id': knowl.id,
                 'title': knowl.title,
                 'time': datetime.utcnow(),
                 'who': who,
                 'state': 'locked'}
    history.save(lock_item)


def get_knowl(ID, fields={"history": 0, "_keywords": 0}):
    return get_knowls().find_one({'_id': ID}, fields)


def knowl_title(kid):
    """
    just the title, used in the knowls in the templates for the pages.
    returns None, if knowl does not exist.
    """
    k = get_knowl(kid, ['title'])
    return k['title'] if k else None


def knowl_exists(kid):
    """
    checks, if the given knowl with ID=@kid exists
    """
    return get_knowl(kid) is not None


def extract_cat(kid):
    if not hasattr(kid, 'split'):
        return None
    return kid.split(".")[0]

# categories, level 0, never change this id
CAT_ID = 'categories'


def refresh_knowl_categories():
    """
    when saving, we refresh the knowl categories
    (actually, this should only happen if it is a new knowl!)

    TODO this should only be called by a housekeeping task, saving a new
    knowl should be a simple set union with the existing list of categories
    """
    # assumes that all actual knowls have a title field
    cats = set((extract_cat(_['_id']) for _ in get_knowls().find({},[])))
    # set the categories list in the categories document in the 'meta' collection
    get_meta().save({'_id': CAT_ID, 'categories': sorted(cats)})
    return str(cats)


def update_knowl_categories(cat):
    """
    when a new knowl is saved, it's category could be new. this function
    ensures that we know it. this is much more efficient than the
    refresh variant.
    """
    get_meta().update({'_id': CAT_ID}, {'$addToSet': {'categories': cat}})


def get_categories():
    c_doc = get_meta().find_one(CAT_ID)
    return c_doc.get('categories', []) if c_doc else []


def get_knowls_by_category(cat):
    """searching for IDs that start with cat and continue with a dot + at least one char"""
    # TODO later on search for the knowl field 'cat'
    # return get_knowls().find({'_id' : { "$regex" : r"^%s\..+" % cat }}, ['title'])
    return get_knowls().find({'cat': cat}, ['title'])

import re
text_keywords = re.compile(r"\b[a-zA-Z0-9-]{3,}\b")
# this one is different from the hashtag regex in main.py,
# because of the match-group ( ... )
hashtag_keywords = re.compile(r'#[a-zA-Z][a-zA-Z0-9-_]{1,}\b')
common_words = set(
    ['and', 'an', 'or', 'some', 'many', 'has', 'have', 'not', 'too', 'mathbb', 'title', 'for'])


def make_keywords(content, kid, title):
    """
    this function is used to create the keywords for the
    full text search. tokenizes them and returns a list
    of the id, the title and content string.
    """
    kws = [kid]  # always included
    kws += kid.split(".")
    kws += text_keywords.findall(title)
    kws += text_keywords.findall(content)
    kws += hashtag_keywords.findall(title)
    kws += hashtag_keywords.findall(content)
    kws = [k.lower() for k in kws]
    kws = set(kws)
    kws = filter(lambda _: _ not in common_words, kws)
    return kws

# allowed qualities for knowls
knowl_qualities = ['beta', 'ok', 'reviewed']


class Knowl(object):
    def __init__(self, ID, template_kwargs=None):
        """
        template_kwars is the list of additional parameters that
        are passed into the knowl the point where the knowl is
        included in the template.
        """
        self.template_kwargs = template_kwargs or {}

        self._id = ID
        data = get_knowl(ID)
        if data:
            self._title = data.get('title', '')
            self._content = data.get('content', '')
            self._quality = data.get('quality', 'beta')
            self._authors = data.get('authors', [])
            self._category = data.get('cat', extract_cat(ID))
            self._last_author = data.get('last_author', '')
            self._timestamp = data.get('timestamp', datetime.utcnow())
        else:
            self._title = ''
            self._content = ''
            self._quality = 'beta'
            self._category = extract_cat(ID)
            self._authors = []
            self._last_author = ''
            self._timestamp = datetime.utcnow()

    def save(self, who):
        """who is the ID of the user, who wants to save the knowl"""
        new_history_item = get_knowl(self.id)
        new_knowl = new_history_item is None
        search_keywords = make_keywords(self.content, self.id, self.title)
        cat = extract_cat(self.id)
        update_op = {"$set": {
                     'content': self.content,
                     'title': self.title,
                     'cat': cat,
                     'quality': self.quality,
                     'last_author': who,
                     'timestamp': self.timestamp,
                     '_keywords': search_keywords
                     }}
        if not new_knowl:
            update_op["$push"] = {"history": new_history_item}
        if who:
            update_op['$addToSet'] = {"authors": who}
        get_knowls().update({'_id': self.id}, update_op, upsert=True)
        # TODO instead of refreshing all knowl categories, just do a
        # set union with the existing categories list and the one from
        # this new knowl!
        if new_knowl:
            update_knowl_categories(cat)
        save_history(self, who)

    def delete(self):
        """deletes this knowl from the db. (DANGEROUS, ADMIN ONLY!)"""
        get_deleted_knowls().save(get_knowls().find_one({'_id': self._id}))
        get_knowls().remove({'_id': self._id})
        refresh_knowl_categories()

    @property
    def authors(self):
        return self._authors

    def author_links(self):
        """
        Basically finds all full names for all the referenced authors.
        (lookup for all full names in just *one* query, hence the or)
        """
        a_query = [{'_id': _} for _ in self.authors]
        a = []
        if len(a_query) > 0:
            users = getDBConnection().userdb.users
            a = users.find({"$or": a_query}, ["full_name"])
        return a

    @property
    def id(self):
        return self._id

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, content):
        """stores the given content string in the database"""
        if not isinstance(content, basestring):
            raise Exception("content has to be of type 'basestring'")
        self._content = content
        self._store_db("content", content)

    @property
    def category(self):
        return self._category

    @property
    def quality(self):
        return self._quality

    @quality.setter
    def quality(self, quality):
        """a measurment information, if this is just "beta", or reviewed ..."""
        if len(quality) == 0:
            return
        if not quality in knowl_qualities:
            logger.warning("quality '%s' is not allowed")
            return
        self._quality = quality
        self._store_db("quality", quality)

    @property
    def title(self):
        """
        This just returns the "title" string, which is exactly the one
        that will be visible in the websites.
        Example: KNOWL('algebra.dirichlet_series') should be replaced
        with "Dirichlet Series" and nothing else.
        """
        return self._title

    @title.setter
    def title(self, title):
        if not isinstance(title, basestring):
            raise Exception("title needs to be of type 'basestring'")
        self._title = title
        self._store_db("title", title)

    def _store_db(self, key, value):
        get_knowls().update({'_id': self._id},
                            {'$set': {key: value}})

    def exists(self):
        return get_knowls().find({'_id': self._id}).count() > 0

    def data(self, fields=None):
        """
        returns the full database entry or if
        keyword 'fields' is a list of strings,only
        the given fields.
        """
        if not self._title or not self._content:
            data = get_knowl(self._id, fields)
            if data:
                self._title = data['title']
                self._content = data['content']
                return data

        data = {'title': self._title,
                'content': self._content}
        return data

    def __unicode__(self):
        return "title: %s, content: %s" % (self.title, self.content)
