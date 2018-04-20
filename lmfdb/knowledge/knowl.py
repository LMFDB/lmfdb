# -*- coding: utf-8 -*-
# the basic knowlege object, with database awareness, …
from lmfdb.knowledge import logger
from lmfdb.base import getDBConnection
from datetime import datetime
import pymongo
ASC = pymongo.ASCENDING
DSC = pymongo.DESCENDING

import psycopg2, psycopg2.extras
from lmfdb.db_backend import getPostgresConnection

import re
text_keywords = re.compile(r"\b[a-zA-Z0-9-]{3,}\b")
# this one is different from the hashtag regex in main.py,
# because of the match-group ( ... )
hashtag_keywords = re.compile(r'#[a-zA-Z][a-zA-Z0-9-_]{1,}\b')
common_words = set(
    ['and', 'an', 'or', 'some', 'many', 'has', 'have', 'not', 'too', 'mathbb', 'title', 'for'])

# categories, level 0, never change this id
CAT_ID = 'categories'

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

def extract_cat(kid):
    if not hasattr(kid, 'split'):
        return None
    return kid.split(".")[0]

# We don't use the PostgresBackend from lmfdb.db_backend
# since it's aimed at constructing queries for mathematical
# objects, doesn't support insertion, etc.

class KnowlBackend(object):
    _default_fields = ['authors', 'cat', 'content', 'last_author', 'quality', 'timestamp', 'title'] # doesn't include id
    def __init__(self):
        self._conn = getPostgresConnection()
    def _execute(self, query, vars=None):
        cur = self._conn.cursor()
        try:
            cur.execute(query, vars)
        except DatabaseError:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()
        return cur
    def get_knowl(self, ID, fields=None):
        if fields is None:
            fields = ['id'] + self._default_fields
        selector = "SELECT {0} FROM knowls WHERE id = %s;".format(", ".join(fields))
        cur = self._execute(selector, (ID,))
        if cur.rowcount > 0:
            res = cur.fetchone()
            return {k:v for k,v in zip(fields, res)}
    def search(self, category="", filters=[], keywords=""):
        restrictions = []
        values = []
        if category:
            restrictions.append("category = %s")
            values.append(category)
        if any(filters):
            qualities = [quality for quality, filt in zip(knowl_qualities, filters) if filt]
            restrictions.append("quality IN %s")
            values.append(qualities)
        if keywords:
            keywords = filter(lambda _: len(_) >= 3, keyword.split(" "))
            if keywords:
                restrictions.append("_keywords @> %s")
                values.append(psycopg2.extras.Json(keywords))
        selector = "SELECT id, title FROM knowls"
        if restrictions:
            selector += " WHERE " + " AND ".join(restrictions)
        cur = self._execute(selector, values)
        return [{k:v for k,v in zip(["id", "title"], res)} for res in cur]
    def save(self, knowl, who):
        """who is the ID of the user, who wants to save the knowl"""
        new_history_item = self.get_knowl(knowl.id, ['id'] + self._default_fields + ['history'])
        new_knowl = new_history_item is None
        if new_knowl:
            history = []
            authors = []
        else:
            history = new_history_item.pop('history') + [new_history_item]
            authors = new_history_item['authors']
        if who and who not in authors:
            authors = authors + [who]
        search_keywords = make_keywords(knowl.content, knowl.id, knowl.title)
        cat = extract_cat(knowl.id)
        values = (authors, cat, knowl.content, who, knowl.quality, knowl.timestamp, knowl.title, history, search_keywords)
        insertor = u"INSERT INTO knowls (id, {0}, history, _keywords) VALUES (%s, {1}, %s, %s) ON CONFLICT (id) DO UPDATE SET ({0}, history, _keywords) = ({1}, %s, %s);".format(u', '.join(self._default_fields), u', '.join(u"%s" * len(self._default_fields)))
        self._execute(insertor, (knowl.id,) + values + values)
        if new_knowl:
            self.update_knowl_categories(cat)
        self.save_history(knowl, who)
    def update(self, kid, key, value):
        if key not in self._default_fields + ['history', '_keywords']:
            raise ValueError("Bad key")
        updator = "UPDATE knowls SET ({0}) VALUES (%s) WHERE id = %s".format(key)
        cur = self._execute(updator, (value, kid))
    def save_history(self, knowl, who):
        """
        saves history tokens in a collection "history".
        each entry has the _id of the updated knowl and at least a timestamp
        and a reference to who has edtited it. also, the title is nice to
        avoid an additional lookup when listing the history!
        'state' can either be 'saved' (for the recent changes list) or 'locked'.
        TODO also calculate a diff with python's difflib and store it here.
        """
        insertor = u"INSERT INTO knowls_history (id, title, time, who, state) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET (title, time, who, state) = (%s, %s, %s, %s);"
        now = datetime.utcnow()
        values = (knowl.title, now, who, 'saved')
        self._execute(insertor, (knowl.id,) + values + values)
    def get_history(self, limit=25):
        """
        returns the last @limit history items
        """
        cols = ("id", "title", "time", "who")
        selector = "SELECT {0} FROM knowls_history WHERE state = 'saved' ORDER BY time DESC LIMIT %s;".format(", ".join(cols))
        cur = self._execute(selector, (limit,))
        return [{k:v for k,v in zip(cols, res)} for res in cur]
    def delete(self, knowl):
        """deletes this knowl from the db. (DANGEROUS, ADMIN ONLY!)"""
        insertor = u"INSERT INTO knowls_deleted (id, {0}) VALUES (%s, {1});".format(u', '.join(self._default_values), u', '.join(u"%s"*len(self._default_values)))
        values = self.get_knowl(knowl.id)
        self._execute(insertor, [knowl.id] + [values[i] for i in self._default_values])
        deletor = "DELETE FROM knowls WHERE id = %s"
        self._execute(deletor, (knowl.id,))
        self.refresh_knowl_categories()
    def is_locked(self, knowlid, delta_min=10):
        """
        if there has been a lock in the last @delta_min minutes, returns a dictionary with the name of the user who obtained a lock and the time it was obtained; else None.
        attention, it discards all locks prior to @delta_min!
        """
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        tdelta = timedelta(minutes=delta_min)
        time = now - tdelta
        deletor = "DELETE FROM knowls_history WHERE state = 'locked' AND time <= %s;"
        cur = self._execute(deletor, (time,))
        selector = "SELECT who, time FROM knowls_history WHERE id = %s AND time >= %s LIMIT 1;"
        cur.execute(selector, (knowlid, time))
        if cur.rowcount > 0:
            return {k:v for k,v in zip(["who", "time"], cur.fetchone())}
    def set_locked(self, knowl, who):
        """
        when a knowl is edited, a lock is created. who is the user id.
        """
        insertor = u"INSERT INTO knowls_history (id, title, time, who, state) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET (title, time, who, state) = (%s, %s, %s, %s);"
        now = datetime.utcnow()
        self._execute(insertor, (knowl.id, knowl.title, now, who, 'locked', know.title, now, who, 'locked'))
    def knowl_title(self, kid):
        """
        just the title, used in the knowls in the templates for the pages.
        returns None, if knowl does not exist.
        """
        k = self.get_knowl(kid, ['title'])
        return k['title'] if k else None
    def knowl_exists(self, kid):
        """
        checks if the given knowl with ID=@kid exists
        """
        return self.get_knowl(kid) is not None
    #def refresh_knowl_categories(self):
    #    selector = "SELECT id FROM knowls;"
    #    cur = self._execute(selector)
    #    cats = sorted(list(set((extract_cat(res[0]) for res in cur))))
    #    updator = "UPDATE knowls_meta SET categories = %s WHERE id = %s;"
    #    cur.execute(updator, (cats, CAT_ID))
    #    return str(cats)
    #def update_knowl_categories(self, cat):
    #    """
    #    when a new knowl is saved, it's category could be new. this function
    #    ensures that we know it. this is much more efficient than the
    #    refresh variant.
    #    """
    #    selector = "SELECT categories FROM knowls_meta WHERE id = %s AND NOT categories @> %s"
    #    cur = self._execute(selector, (CAT_ID, psycopg2.extras.Json([cat])))
    #    if cur.rowcount > 0:
    #        categories = cur.fetchone()[0]
    #        updator = "UPDATE knowls_meta SET categories = %s WHERE id = %s"
    #        categories = psycopg2.extras.Json(sorted(categories + [cat]))
    #        cur.execute(updator, (categories, CAT_ID))
    def get_categories(self):
        #selector = "SELECT categories FROM knowls_meta WHERE id = %s"
        #cur.execute(selector, (CAT_ID,))
        selector = "SELECT DISTINCT cat FROM knowls;"
        cur.execute(selector)
        return sorted([res[0] for res in cur])
    def cleanup(self, max_h=50):
        """
        reindexes knowls, also the list of categories. prunes history.
        returns the list of categories (as a string), a count of the the number of knowls reindexed and the number of histories pruned.
        """
        cats = self.refresh_knowl_categories()
        selector = "SELECT (id, content, title) FROM knowls;"
        cur = self._execute(selector)
        updator = "UPDATE knowls SET (cat, _keywords) = (%s, %s) WHERE id = %s;"
        for kid, content, title in cur:
            cat = extract_cat(kid)
            search_keywords = make_keywords(content, kid, title)
            self._execute(updator, (cat, search_keywords, kid))
        hcount = 0
        selector = "SELECT id, history FROM knowls WHERE history IS NOT NULL;"
        cur = self._execute(selector)
        updator = "UPDATE knowls SET history = %s WHERE id = %s"
        for kid, history in cur:
            if len(history) > max_h:
                hcount += 1
                self._execute(updator, (history[-max_h:], kid))
        counter = "SELECT COUNT(*) FROM knowls WHERE history IS NOT NULL;"
        cur = self._execute(counter)
        reindex_count = int(cur.fetchone()[0])
        return cats, reindex_count, hcount

backend = None
def knowl_db():
    global backend
    if backend is None:
        backend = KnowlBackend()
    return backend

def knowl_title(kid):
    return knowl_db().knowl_title(kid)

def knowl_exists(kid):
    return knowl_db().knowl_exists(kid)

def get_knowls():
    _C = getDBConnection()
    return _C.knowledge.knowls

def get_meta():
    """
    collection of meta-documents, like categories
    """
    _C = getDBConnection()
    return _C.knowledge.meta

def get_deleted_knowls():
    _C = getDBConnection()
    return _C.knowledge.deleted_knowls

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
        data = knowl_db().get_knowl(ID)
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
        knowl_db().save(self, who)

    def delete(self):
        """deletes this knowl from the db. (DANGEROUS, ADMIN ONLY!)"""
        knowl_db().delete(self)

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
        knowl_db().update(self.id, key, value)

    def exists(self):
        return knowl_db().knowl_exists(self._id)

    def data(self, fields=None):
        """
        returns the full database entry or if
        keyword 'fields' is a list of strings,only
        the given fields.
        """
        if not self._title or not self._content:
            data = knowl_db().get_knowl(self._id, fields)
            if data:
                self._title = data['title']
                self._content = data['content']
                return data

        data = {'title': self._title,
                'content': self._content}
        return data

    def __unicode__(self):
        return "title: %s, content: %s" % (self.title, self.content)
