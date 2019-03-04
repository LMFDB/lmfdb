# -*- coding: utf-8 -*-
# the basic knowlege object, with database awareness, …
from lmfdb.knowledge import logger
from datetime import datetime
import time

from lmfdb.backend.database import db, PostgresBase, DelayCommit
from lmfdb.backend.encoding import Json
from lmfdb.users.pwdmanager import userdb
from psycopg2.sql import SQL, Identifier, Placeholder

import re
text_keywords = re.compile(r"\b[a-zA-Z0-9-]{3,}\b")
top_knowl_re = re.compile(r"(.*)\.top$")
bottom_knowl_re = re.compile(r"(.*)\.bottom$")
link_finder_re = re.compile("""KNOWL(_INC)?\(\s*['"]([^'"]+)['"]""")
# this one is different from the hashtag regex in main.py,
# because of the match-group ( ... )
hashtag_keywords = re.compile(r'#[a-zA-Z][a-zA-Z0-9-_]{1,}\b')
common_words = set(
    ['and', 'an', 'or', 'some', 'many', 'has', 'have', 'not', 'too', 'mathbb', 'title', 'for'])

# categories, level 0, never change this id
#CAT_ID = 'categories'

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

def extract_typ(kid):
    m = top_knowl_re.match(kid)
    if m:
        return 1, m.group(1)
    m = bottom_knowl_re.match(kid)
    if m:
        return -1, m.group(1)
    return 0, None

def extract_links(content):
    return sorted(set(x[1] for x in link_finder_re.findall(content)))

# We don't use the PostgresTable from lmfdb.backend.database
# since it's aimed at constructing queries for mathematical objects

class KnowlBackend(PostgresBase):
    _default_fields = ['authors', 'cat', 'content', 'last_author', 'timestamp', 'title', 'status', 'type', 'links', 'source'] # doesn't include id, _keywords, reviewer or review_timestamp
    def __init__(self):
        PostgresBase.__init__(self, 'db_knowl', db)
        self._rw_knowldb = db.can_read_write_knowls()
        #FIXME this should be moved to the config file
        self.caching_time = 10
        self.cached_titles_timestamp = 0;
        self.cached_titles = {}

    @property
    def titles(self):
        now = time.time()
        if now - self.cached_titles_timestamp > self.caching_time:
            self.cached_titles_timestamp = now
            self.cached_titles = dict([(elt['id'], elt['title']) for elt in self.get_all_knowls(['id','title'])])
        return self.cached_titles


    def can_read_write_knowls(self):
        return self._rw_knowldb

    def get_knowl(self, ID, fields=None):
        if fields is None:
            fields = ['id'] + self._default_fields
        selecter = SQL("SELECT {0} FROM kwl_knowls2 WHERE id = %s AND status >= %s ORDER BY timestamp DESC LIMIT 1").format(SQL(", ").join(map(Identifier, fields)))
        cur = self._execute(selecter, [ID, 0])
        if cur.rowcount > 0:
            res = cur.fetchone()
            return {k:v for k,v in zip(fields, res)}

    def get_all_knowls(self, fields=None):
        if fields is None:
            fields = ['id'] + self._default_fields
        selecter = SQL("SELECT DISTINCT ON (id) {0} FROM kwl_knowls2 WHERE status >= %s ORDER BY timestamp DESC").format(SQL(", ").join(map(Identifier, fields)))
        cur = self._execute(selecter, [0])
        return [{k:v for k,v in zip(fields, res)} for res in cur]

    def search(self, category="", filters=[], keywords="", author=None, sort=[]):
        restrictions = []
        values = []
        if category:
            restrictions.append(SQL("cat = %s"))
            values.append(category)
        if len(filters) > 0:
            restrictions.append(SQL("status = ANY(%s)"))
            values.append([knowl_status_code[q] for q in filters if q in knowl_status_code])
        else:
            restrictions.append(SQL("status >= %s"))
            values.append(0)
        if keywords:
            keywords = filter(lambda _: len(_) >= 3, keywords.split(" "))
            if keywords:
                restrictions.append(SQL("_keywords @> %s"))
                values.append(Json(keywords))
        if author is not None:
            restrictions.append(SQL("authors @> %s"))
            values.append(Json(author))
        has_timestamp = any(x == 'timestamp' or isinstance(x, (list, tuple)) and x[0] == 'timestamp' for x in sort)
        if not has_timestamp:
            sort = sort + [('timestamp', -1)]
        selecter = SQL("SELECT DISTINCT ON (id) id, title FROM kwl_knowls2 WHERE {0} ORDER BY {1}").format(
            SQL(" AND ").join(restrictions), self._sort_str(sort))
        cur = self._execute(selecter, values)
        return [{k:v for k,v in zip(["id", "title"], res)} for res in cur]

    def save(self, knowl, who):
        """who is the ID of the user, who wants to save the knowl"""
        most_recent = self.get_knowl(knowl.id, ['id'] + self._default_fields)
        new_knowl = most_recent is None
        if new_knowl:
            authors = []
        else:
            authors = most_recent.pop('authors', [])

        if who and who not in authors:
            authors = authors + [who]

        search_keywords = make_keywords(knowl.content, knowl.id, knowl.title)
        cat = extract_cat(knowl.id)
        typ, source = extract_typ(knowl.id)
        links = extract_links(knowl.content)
        values = (knowl.id, Json(authors), cat, knowl.content, who, knowl.quality, knowl.timestamp, knowl.title, 0, typ, links, source, Json(search_keywords))
        with DelayCommit(self):
            insterer = SQL("INSERT INTO kwl_knowls2 (id, {0}, _keywords) VALUES ({1})")
            insterer = insterer.format(SQL(', ').join(map(Identifier, self._default_fields)), SQL(", ").join(Placeholder() * (len(self._default_fields) + 2)))
            self._execute(insterer, (knowl.id,) + values)
        self.cached_titles[knowl.id] = knowl.title

    def get_history(self, limit=25):
        """
        returns the last @limit history items
        """
        cols = ("id", "title", "timestamp", "last_author")
        selecter = SQL("SELECT {0} FROM kwl_knowls2 WHERE status >= %s ORDER BY timestamp DESC LIMIT %s").format(SQL(", ").join(map(Identifier, cols)))
        cur = self._execute(selecter, (0, limit,))
        return [{k:v for k,v in zip(cols, res)} for res in cur]

    def delete(self, knowl):
        """deletes this knowl from the db. This is effected by setting the status to -2 on all copies of the knowl"""
        updator = SQL("UPDATE kwl_knowls2 SET status=%s WHERE id=%s")
        self._execute(updator, [-2, knowl.id])
        if knowl.id in self.cached_titles:
            self.cached_titles.pop(knowl.id)

    def undelete(self, knowl):
        """Sets the status for all deleted copies of the knowl to beta"""
        updator = SQL("UPDATE kwl_knowls2 SET status=%s WHERE status=%s AND id=%s")
        self._execute(updator, [0, -2, knowl.id])

    def is_locked(self, knowlid, delta_min=10):
        """
        if there has been a lock in the last @delta_min minutes, returns a dictionary with the name of the user who obtained a lock and the time it was obtained; else None.
        attention, it discards all locks prior to @delta_min!
        """
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        tdelta = timedelta(minutes=delta_min)
        time = now - tdelta
        selecter = SQL("SELECT username, timestamp FROM kwl_locks WHERE id = %s AND timestamp >= %s LIMIT 1")
        cur.execute(selecter, (knowlid, time))
        if cur.rowcount > 0:
            return {k:v for k,v in zip(["username", "timestamp"], cur.fetchone())}

    def set_locked(self, knowl, who):
        """
        when a knowl is edited, a lock is created. who is the user id.
        """
        insterer = SQL("INSERT INTO kwl_locks (id, timestamp, who) VALUES (%s, %s, %s)")
        now = datetime.utcnow()
        self._execute(insterer, [knowl.id, now, who])

    def knowl_title(self, kid):
        """
        just the title, used in the knowls in the templates for the pages.
        returns None, if knowl does not exist.
        """
        return self.titles.get(kid, None)

    def knowl_exists(self, kid):
        """
        checks if the given knowl with ID=@kid exists
        """
        return self.knowl_title(kid) is not None

    def get_categories(self):
        selecter = SQL("SELECT DISTINCT cat FROM kwl_knowls2")
        cur = self._execute(selecter)
        return sorted([res[0] for res in cur])

knowldb = KnowlBackend()

def knowl_title(kid):
    return knowldb.knowl_title(kid)

def knowl_exists(kid):
    return knowldb.knowl_exists(kid)

# allowed qualities for knowls
knowl_status_code = {'reviewed':1, 'beta':0, 'in progress': -1, 'deleted': -2}
knowl_type_code = {'top': 1, 'normal': 0, 'bottom': -1, 'comments': -2}

class Knowl(object):
    def __init__(self, ID, template_kwargs=None):
        """
        template_kwars is the list of additional parameters that
        are passed into the knowl the point where the knowl is
        included in the template.
        """
        self.template_kwargs = template_kwargs or {}

        self._id = ID
        #given that we cache it's existence it is quicker to check for existence
        if self.exists():
            data = knowldb.get_knowl(ID)
        else:
            data = None
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
        knowldb.save(self, who)

    def delete(self):
        """Marks the knowl as deleted.  Admin only."""
        knowldb.delete(self)

    def undelete(self):
        """Brings the knowl back from being deleted by setting status to beta.  Admin only."""
        knowldb.undelete(self)

    @property
    def authors(self):
        return self._authors

    def author_links(self):
        """
        Basically finds all full names for all the referenced authors.
        (lookup for all full names in just *one* query, hence the or)
        """
        return userdb.full_names(self.authors)

    def last_author(self):
        """
        Full names for the last authors.
        (lookup for all full names in just *one* query, hence the or)
        """
        return userdb.lookup(self._last_author)["full_name"]

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

    @property
    def title(self):
        """
        This just returns the "title" string, which is exactly the one
        that will be visible in the websites.
        Example: KNOWL('algebra.dirichlet_series') should be replaced
        with "Dirichlet Series" and nothing else.
        """
        title = self._title
        #from flask import g
        # if self._quality=='beta' and g.BETA:
        #     title += " (beta status)"
        return title

    @title.setter
    def title(self, title):
        if not isinstance(title, basestring):
            raise Exception("title needs to be of type 'basestring'")
        self._title = title

    def exists(self):
        return knowldb.knowl_exists(self._id)

    def data(self, fields=None):
        """
        returns the full database entry or if
        keyword 'fields' is a list of strings,only
        the given fields.
        """
        if not self._title or not self._content:
            data = knowldb.get_knowl(self._id, fields)
            if data:
                self._title = data['title']
                self._content = data['content']
                return data

        data = {'title': self._title,
                'content': self._content}
        return data

    def __unicode__(self):
        return "title: %s, content: %s" % (self.title, self.content)
