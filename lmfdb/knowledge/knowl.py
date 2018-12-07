# -*- coding: utf-8 -*-
# the basic knowlege object, with database awareness, …
from lmfdb.knowledge import logger
from datetime import datetime
import time

from lmfdb.db_backend import db, PostgresBase, DelayCommit
from lmfdb.db_encoding import Array
from lmfdb.users.pwdmanager import userdb
from psycopg2.sql import SQL, Identifier, Placeholder

import re
text_keywords = re.compile(r"\b[a-zA-Z0-9-]{3,}\b")
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

# We don't use the PostgresTable from lmfdb.db_backend
# since it's aimed at constructing queries for mathematical objects

class KnowlBackend(PostgresBase):
    _default_fields = ['authors', 'cat', 'content', 'last_author', 'quality', 'timestamp', 'title'] # doesn't include id
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
        selecter = SQL("SELECT {0} FROM kwl_knowls WHERE id = %s").format(SQL(", ").join(map(Identifier, fields)))
        cur = self._execute(selecter, (ID,))
        if cur.rowcount > 0:
            res = cur.fetchone()
            return {k:v for k,v in zip(fields, res)}

    def get_all_knowls(self, fields=None):
        if fields is None:
            fields = ['id'] + self._default_fields
        selecter = SQL("SELECT {0} FROM kwl_knowls").format(SQL(", ").join(map(Identifier, fields)))
        cur = self._execute(selecter)
        return [{k:v for k,v in zip(fields, res)} for res in cur]

    def search(self, category="", filters=[], keywords="", author=None, sort=None):
        restrictions = []
        values = []
        if category:
            restrictions.append(SQL("cat = %s"))
            values.append(category)
        if len(filters) > 0:
            restrictions.append(SQL("quality = ANY(%s)"))
            values.append(Array([q for q in filters if q in knowl_qualities]))
        if keywords:
            keywords = filter(lambda _: len(_) >= 3, keywords.split(" "))
            if keywords:
                restrictions.append(SQL("_keywords @> %s"))
                values.append(keywords)
        if author is not None:
            restrictions.append(SQL("authors @> %s"))
            values.append([author])
        selecter = SQL("SELECT id, title FROM kwl_knowls")
        if restrictions:
            selecter = SQL("{0} WHERE {1}").format(selecter, SQL(" AND ").join(restrictions))
        if sort is not None:
            selecter = SQL("{0} ORDER BY {1}").format(selecter, self._sort_str(sort))
        cur = self._execute(selecter, values)
        return [{k:v for k,v in zip(["id", "title"], res)} for res in cur]

    def check_title_and_content(self):
        # This should really be done at the database level now that we can require columns to be not null
        cur = self._execute(SQL("SELECT COUNT(*) FROM kwl_knowls WHERE title IS NULL"))
        notitle = cur.fetchone()[0]
        cur = self._execute(SQL("SELECT COUNT(*) FROM kwl_knowls WHERE content IS NULL"))
        nocontent = cur.fetchone()[0]
        assert notitle == 0, "%s knowl(s) don't have a title" % notitle
        assert nocontent == 0, "%s knowl(s) don't have content" % nocontent

    def save(self, knowl, who):
        """who is the ID of the user, who wants to save the knowl"""
        new_history_item = self.get_knowl(knowl.id, ['id'] + self._default_fields + ['history'])
        new_knowl = new_history_item is None
        if new_knowl:
            history = []
            authors = []
        else:
            history = new_history_item.pop('history')
            if history is not None:
                history += [new_history_item]
            else:
                history = []
            authors = new_history_item.pop('authors', [])
            if authors is None:
                authors = []

        if who and who not in authors:
            authors = authors + [who]

        search_keywords = make_keywords(knowl.content, knowl.id, knowl.title)
        cat = extract_cat(knowl.id)
        values = (authors, cat, knowl.content, who, knowl.quality, knowl.timestamp, knowl.title, history, search_keywords)
        with DelayCommit(self):
            insterer = SQL("INSERT INTO kwl_knowls (id, {0}, history, _keywords) VALUES (%s, {1}) ON CONFLICT (id) DO UPDATE SET ({0}, history, _keywords) = ({1})")
            insterer = insterer.format(SQL(', ').join(map(Identifier, self._default_fields)), SQL(", ").join(Placeholder() * (len(self._default_fields) + 2)))
            self._execute(insterer, (knowl.id,) + values + values)
            self.save_history(knowl, who)
        self.cached_titles[knowl.id] = knowl.title

    def update(self, kid, key, value):
        if key not in self._default_fields + ['history', '_keywords']:
            raise ValueError("Bad key")
        updater = SQL("UPDATE kwl_knowls SET ({0}) = ROW(%s) WHERE id = %s").format(Identifier(key))
        self._execute(updater, (value, kid))

    def save_history(self, knowl, who):
        """
        saves history tokens in a collection "history".
        each entry has the _id of the updated knowl and at least a timestamp
        and a reference to who has edited it. Also, the title is nice to
        avoid an additional lookup when listing the history!
        'state' can either be 'saved' (for the recent changes list) or 'locked'.
        TODO also calculate a diff with python's difflib and store it here.
        """
        insterer = SQL("INSERT INTO kwl_history (id, title, time, who, state) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET (title, time, who, state) = (%s, %s, %s, %s)")
        now = datetime.utcnow()
        values = (knowl.title, now, who, 'saved')
        self._execute(insterer, (knowl.id,) + values + values)

    def get_history(self, limit=25):
        """
        returns the last @limit history items
        """
        cols = ("id", "title", "time", "who")
        selecter = SQL("SELECT {0} FROM kwl_history WHERE state = 'saved' ORDER BY time DESC LIMIT %s").format(SQL(", ").join(map(Identifier, cols)))
        cur = self._execute(selecter, (limit,))
        return [{k:v for k,v in zip(cols, res)} for res in cur]

    def delete(self, knowl):
        """deletes this knowl from the db. (DANGEROUS, ADMIN ONLY!)"""
        with DelayCommit(self):
            insterer = SQL("INSERT INTO kwl_deleted (id, {0}) VALUES (%s, {1})").format(SQL(', ').join(map(Identifier, self._default_fields)), SQL(', ').join(Placeholder() * len(self._default_fields)))
            values = self.get_knowl(knowl.id)
            self._execute(insterer, [knowl.id] + [values[i] for i in self._default_fields])
            deletor = SQL("DELETE FROM kwl_knowls WHERE id = %s")
            self._execute(deletor, (knowl.id,))
        if knowl.id in self.cached_titles:
            self.cached_titles.pop(knowl.id)

    def is_locked(self, knowlid, delta_min=10):
        """
        if there has been a lock in the last @delta_min minutes, returns a dictionary with the name of the user who obtained a lock and the time it was obtained; else None.
        attention, it discards all locks prior to @delta_min!
        """
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        tdelta = timedelta(minutes=delta_min)
        time = now - tdelta
        deletor = SQL("DELETE FROM kwl_history WHERE state = 'locked' AND time <= %s")
        cur = self._execute(deletor, (time,))
        selecter = SQL("SELECT who, time FROM kwl_history WHERE id = %s AND time >= %s LIMIT 1")
        cur.execute(selecter, (knowlid, time))
        if cur.rowcount > 0:
            return {k:v for k,v in zip(["who", "time"], cur.fetchone())}

    def set_locked(self, knowl, who):
        """
        when a knowl is edited, a lock is created. who is the user id.
        """
        insterer = SQL("INSERT INTO kwl_history (id, title, time, who, state) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET (title, time, who, state) = (%s, %s, %s, %s)")
        now = datetime.utcnow()
        self._execute(insterer, (knowl.id, knowl.title, now, who, 'locked', knowl.title, now, who, 'locked'))

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
        selecter = SQL("SELECT DISTINCT cat FROM kwl_knowls")
        cur = self._execute(selecter)
        return sorted([res[0] for res in cur])

    def cleanup(self, max_h=50):
        """
        reindexes knowls, also the list of categories. prunes history.
        returns the list of categories (as a string), a count of the the number of knowls reindexed and the number of histories pruned.
        """
        with DelayCommit(self):
            cats = self.get_categories()
            selecter = SQL("SELECT (id, content, title) FROM kwl_knowls")
            cur = self._execute(selecter)
            updater = SQL("UPDATE kwl_knowls SET (cat, _keywords) = (%s, %s) WHERE id = %s")
            for kid, content, title in cur:
                cat = extract_cat(kid)
                search_keywords = make_keywords(content, kid, title)
                self._execute(updater, (cat, search_keywords, kid))
            hcount = 0
            selecter = SQL("SELECT id, history FROM kwl_knowls WHERE history IS NOT NULL")
            cur = self._execute(selecter)
            updater = SQL("UPDATE kwl_knowls SET history = %s WHERE id = %s")
            for kid, history in cur:
                if len(history) > max_h:
                    hcount += 1
                    self._execute(updater, (history[-max_h:], kid))
            counter = SQL("SELECT COUNT(*) FROM kwl_knowls WHERE history IS NOT NULL")
            cur = self._execute(counter)
            reindex_count = int(cur.fetchone()[0])
        return cats, reindex_count, hcount

knowldb = KnowlBackend()

def knowl_title(kid):
    return knowldb.knowl_title(kid)

def knowl_exists(kid):
    return knowldb.knowl_exists(kid)

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
        """deletes this knowl from the db. (DANGEROUS, ADMIN ONLY!)"""
        knowldb.delete(self)

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
        self._store_db("title", title)

    def _store_db(self, key, value):
        knowldb.update(self.id, key, value)

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
