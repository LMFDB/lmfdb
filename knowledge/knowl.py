# -*- coding: utf-8 -*-
# the basic knowlege object, with database awareness, …

def get_knowls():
  from base import getDBConnection
  _C = getDBConnection()
  return _C.knowledge.knowls

def get_deleted_knowls():
  from base import getDBConnection
  _C = getDBConnection()
  return _C.knowledge.deleted_knowls

def get_knowl(ID, fields = None):
  return get_knowls().find_one({'_id' : ID}, fields=fields)

class Knowl(object):
  def __init__(self, ID):
    self._id = ID
    data = get_knowl(ID)
    if data:
      self._title   = data.get('title', '')
      self._content = data.get('content', '')
    else:
      self._title   = ''
      self._content = ''

  def save(self):
    get_knowls().save({
         '_id' : self.id,
         'content' : self.content,
         'title' : self.title
        })
        
  def delete(self):
    """deletes this knowl from the db. (DANGEROUS, ADMIN ONLY!)"""
    get_deleted_knowls().save(get_knowls().find_one({'_id' : self._id}))
    get_knowls().remove({'_id' : self._id})

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
