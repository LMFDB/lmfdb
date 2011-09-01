#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# store passwords, check users, ...
# password hashing is done with fixed and variable salting
# Author: Harald Schilly <harald.schilly@univie.ac.at>

__all__ = [ 'LmfdbUser', 'user_exists' ]

# NEVER EVER change the fixed_salt!
fixed_salt = '=tU\xfcn|\xab\x0b!\x08\xe3\x1d\xd8\xe8d\xb9\xcc\xc3fM\xe9O\xfb\x02\x9e\x00\x05`\xbb\xb9\xa7\x98'

import os
import base
from main import logger

def get_users():
  import base
  return base.getDBConnection().userdb.users

# never narrow down this range, only increase it!
rmin = -10000
rmax =  10000

def get_random_salt():
  """
  Generates a random salt.
  This random_salt is a way to have the passwords and code public,
  but still make it very hard to guess it.
  once computers are 10x faster, change the rmin,rmax limits
  """
  import random
  return str(random.randrange(rmin, rmax))
  
def hashpwd(pwd, random_salt = None):
  """
  Globally unique routine how passwords are hashed.
  Once in production, never ever change it - otherwise all
  passwords are useless.
  """
  from hashlib import sha256
  hashed = sha256()
  hashed.update(pwd) # pwd must come first!
  if not random_salt:
    random_salt = get_random_salt()
  hashed.update(random_salt)
  hashed.update(fixed_salt) # fixed salt must come last!
  return hashed.hexdigest()

# Read about flask-login if you are unfamiliar with this UserMixin/Login 
from flaskext.login import UserMixin

class LmfdbUser(UserMixin):
  """
  The User Object

  It is backed by MongoDB.
  """
  properties = ('full_name', 'email', 'url', 'about')

  def __init__(self, uid):
    if not isinstance(uid, basestring):
      raise Exception("Username is not a basestring")

    self._uid = uid
    self._authenticated = False
    self._dirty = False #flag if we have to save
    self._data = dict([(_,None) for _ in LmfdbUser.properties])

    u = get_users().find_one({'_id' : uid})
    if u:
      self._data.update(u)

  @property
  def name(self):
    return self.full_name or self._data['_id']

  @property
  def full_name(self):
    return self._data['full_name']

  @full_name.setter
  def full_name(self, full_name):
    self._data['full_name'] = full_name
    self._dirty = True

  @property
  def email(self):
    return self._data['email']

  @email.setter
  def email(self, email):
    if not self._validate_email(email):
      raise Exception("Email <%s> is not valid!" % email)
    self._data['email'] = email
    self._dirty = True

  @property
  def about(self):
    return self._data['about']

  @about.setter
  def about(self, about):
    self._data['about'] = about
    self._dirty = True

  @property
  def url(self):
    return self._data['url']

  @url.setter
  def url(self, url):
    self._data['url'] = url
    self._dirty = True

  @property
  def created(self):
    return self._data['created']

  #def _my_entry(self):
  #  return get_users().find_one({'_id' : self._name})  

  @property
  def id(self):
    return self._data['_id']
  
  def is_authenticate(self):
    """required by flask-login user class"""
    return self._authenticated 

  def is_anonymous(self):
    """required by flask-login user class"""
    return not self.is_authenticated()

  def is_admin(self):
    """true, iff has attribute admin set to True"""
    return self._data.get("admin", False)

  def authenticate(self, pwd):
    """
    checks if the given password for the user is valid.
    @return: True: OK, False: wrong password.
    """
    #from time import time
    #t1 = time()
    if not 'password' in self._data: 
      logger.warning("no password data in db for '%s'!" % self._uid)
      return False
    for i in range(rmin, rmax + 1):
      if self._data['password'] == hashpwd(pwd, str(i)):
        #log "AUTHENTICATED after %s!!" % (time() - t1)
        self._authenticated = True
        break
    return self._authenticated

  def _validate_email(self, email):
    """should do a regex match"""
    return True

  def save(self):
    if not self._dirty: return
    logger.debug("saving '%s': %s" % (self.id, self._data))
    get_users().save(self._data)


def new_user(uid, pwd = None):
  """
  generates a new user, asks for the password interactively,
  and stores it in the DB.
  """
  if not pwd:
    from getpass import getpass
    pwd_input = getpass( "Enter  Password: ")
    pwd_input2 = getpass("Repeat Password: ")
    if pwd_input != pwd_input2:
      raise Exception("ERROR: Passwords do not match!")
    pwd = pwd_input
  if get_users().find({'_id' : uid}).count() > 0:
    raise Exception("ERROR: User %s already exists" % uid)
  password = hashpwd(pwd)
  from datetime import datetime
  data = {'_id' : uid, 'password' : password, 'created' : datetime.utcnow() }
  # set defaults to empty strings
  for key in LmfdbUser.properties:
    data.update({key: ""})
  get_users().save(data)
  new_user = LmfdbUser(uid)
  return new_user

  
def user_exists(uid):
  return get_users().find({'_id' : uid}).count() > 0

def get_user_list():
  """
  returns a list of tuples: [('user_db_id', 'full_name'),…]
  full_name could be None
  """
  users_cursor = get_users().find(fields=["full_name"])
  ret = []
  for e in users_cursor:
    name = e['full_name'] or e['_id']
    ret.append((e['_id'], name))
  return ret

from flaskext.login import AnonymousUser
class LmfdbAnonymousUser(AnonymousUser):
  """
  The sole purpose of this Anonymous User is the 'is_admin' method
  and probably others.
  """
  def is_admin(self):
    return False

if __name__=="__main__":
  print "Usage:"
  print "add user"
  print "remove user"
  print "…"
 
