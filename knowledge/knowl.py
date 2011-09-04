# -*- coding: utf-8 -*-
# the basic knowlege object, with database awareness, …
from knowledge import logger
from base import getDBConnection
from datetime import datetime

def get_knowls():
  _C = getDBConnection()
  knowls = _C.knowledge.knowls
  knowls.ensure_index('authors')
  # _keywords is used for the full text search
  knowls.ensure_index('_keywords')
  return knowls

def get_deleted_knowls():
  _C = getDBConnection()
  return _C.knowledge.deleted_knowls

def get_knowl(ID, fields = { "history": 0, "_keywords" : 0 }):
  return get_knowls().find_one({'_id' : ID}, fields=fields)

import re
valid_keywords = re.compile(r"\b[a-zA-Z-]{3,}\b")

def make_keywords(content, kid, title):
  """
  this function is used to create the keywords for the
  full text search. tokenizes them and returns a list
  of the id, the title and content string.
  """
  kws = [ kid ] # always included
  kws += kid.split(".")
  kws += valid_keywords.findall(title)
  kws += valid_keywords.findall(content)
  kws = [ k.lower() for k in kws ]
  kws = list(set(kws))
  return kws

class Knowl(object):
  def __init__(self, ID, template_kwargs = None):
    """
    template_kwars is the list of additional parameters that
    are passed into the knowl the point where the knowl is 
    included in the template.
    """
    self.template_kwargs = template_kwargs or {}

    self._id = ID
    data = get_knowl(ID)
    if data:
      self._title   = data.get('title', '')
      self._content = data.get('content', '')
      self._quality = data.get('quality', 'beta')
      self._authors = data.get('authors', [])
      self._last_author = data.get('last_author', '')
      self._timestamp = data.get('timestamp', datetime.now())
    else:
      self._title   = ''
      self._content = ''
      self._quality = 'beta'
      self._authors = []
      self._last_author = ''
      self._timestamp = datetime.now()

  def save(self, who):
    """who is the ID of the user, who wants to save the knowl"""
    new_history_item = get_knowl(self.id)
    search_keywords = make_keywords(self.content, self.id, self.title)
    get_knowls().update({'_id' : self.id},
        {"$set": {
           'content' :    self.content,
           'title' :      self.title,
           'quality':     self.quality,
	       'last_author': who,
	       'timestamp':   self.timestamp,
           '_keywords' :  search_keywords
	       } ,
	     "$push": {"history": new_history_item}}, upsert=True)
    if who:
      get_knowls().update(
         { '_id':self.id }, 
         { "$addToSet" : { "authors" : who }})
        
  def delete(self):
    """deletes this knowl from the db. (DANGEROUS, ADMIN ONLY!)"""
    get_deleted_knowls().save(get_knowls().find_one({'_id' : self._id}))
    get_knowls().remove({'_id' : self._id})

  @property
  def authors(self):
    return self._authors

  def author_links(self):
     a_query = [{'_id': _} for _ in self.authors]
     a = []
     if len(a_query) > 0:
       users = getDBConnection().userdb.users
       a = users.find({"$or" : a_query}, fields=["full_name"])
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
  def quality(self):
    return self._quality
 
  @quality.setter
  def quality(self, quality):
    """a measurment information, if this is just "beta", or reviewed ..."""
    if len(quality) == 0: return
    if not quality in ['beta', 'ok', 'reviewed']:
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
    get_knowls().update({'_id' : self._id},
                        {'$set' : { key : value }})

  def exists(self):
    return get_knowls().find({'_id' : self._id }).count() > 0

  def data(self, fields=None):
    """
    returns the full database entry or if
    keyword 'fields' is a list of strings,only
    the given fields. 
    """
    if not self._title or not self._content:
      data = get_knowl(self._id, fields=fields)
      if data:
        self._title = data['title']
        self._content = data['content']
        return data
      
    data = { 'title' : self._title, 
             'content' : self._content}
    return data

  def __unicode__(self):
    return "title: %s, content: %s" % (self.title, self.content)
