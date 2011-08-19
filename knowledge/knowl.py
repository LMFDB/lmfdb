# -*- coding: utf-8 -*-
# the basic knowlege object, with database awareness, …
from base import getDBConnection
_C = getDBConnection()


def get_knowl(kid, fields=None):
  if fields:
    return _C.knowledge.knowls.find_one({'_id' : kid}, fields=fields)
  return _C.knowledge.knowls.find_one({'_id' : kid})

class Knowl(object):
  def __init__(self, *args, **kwargs):
    self.args = args
    self.kwargs = kwargs
    self._id = args[0]

  @property
  def id(self):
    return self._id

  @property
  def content(self):
    return "this is the \(\LaTeX\) aware content."

  @property
  def title(self):
    """
    This just returns the "title" string, which is exactly the one
    that will be visible in the websites. 
    Example: KNOWL('algebra.dirichlet_series') should be replaced
    with "Dirichlet Series" and nothing else. 

    TODO: Since this happens several times for each page, it's
    godsend for implementing memcache optimization.
    """
    return get_knowl(self._id, fields=["title"])

  def __unicode__(self):
    return "args: %s, kwargs: %s" % (self.args, self.kwargs)
