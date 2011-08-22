# -*- coding: utf-8 -*-
# the basic knowlege object, with database awareness, …

def get_knowls():
  from base import getDBConnection
  _C = getDBConnection()
  return _C.knowledge.knowls

class Knowl(object):
  def __init__(self, ID):
    self._id = ID
    self._title = None
    self._content = None

  @property
  def id(self):
    return self._id

  @property
  def content(self):
    if not self._content:
      self._content = self.data(fields=['content'])
    return self._content

  @content.setter
  def content(self, content):
    """stores the given content string in the database"""
    if not isinstance(content, basestring):
      raise Exception("content has to be of type 'basestring'")
    self._content = content
    self._store_db("content", content)

  @property
  def title(self):
    """
    This just returns the "title" string, which is exactly the one
    that will be visible in the websites. 
    Example: KNOWL('algebra.dirichlet_series') should be replaced
    with "Dirichlet Series" and nothing else. 
    """
    if not self._title:
      self._title = self.data(fields=["title"])
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
      if not fields:
        fields = ['title', 'content']
      data = get_knowls().find_one({'_id' : kid}, fields=fields)
      self._title = data['title']
      self._content = data['content']
    else:
      data = { 'title' : self._title, 
               'content' : self._content}
    return data

  def __unicode__(self):
    return "title: %s, content: %s" % (self.title, self.content)
