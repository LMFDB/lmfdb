#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# store passwords, check users, ...
# password hashing is done with fixed and variable salting

# never ever change the fixed_salt!
fixed_salt = '=tU\xfcn|\xab\x0b!\x08\xe3\x1d\xd8\xe8d\xb9\xcc\xc3fM\xe9O\xfb\x02\x9e\x00\x05`\xbb\xb9\xa7\x98'

import os
import base

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

  It is backed by MongoDB and all modifications are done
  immideately via upserts.
  """
  def __init__(self, name, password):
    if not name or not isinstance(name, basestring):
      raise Exception("Username is not a basestring")
    if not password or not isinstance(password, basestring):
      raise Exception("Password is not a proper Hash (and not a basestring)")

    self._name = name
    self._password = password
    self._email = None
    self._authenticated = False
    self._full_name = None

  @property
  def name(self):
    return self._full_name or self._name

  @property
  def full_name(self):
    return self._full_name

  @full_name.setter
  def full_name(self, full_name):
    self._full_name = full_name
    print self._full_name
    get_users().update({'_id' : self._name} ,
                       {'$set' : { 'full_name' : full_name }})

  @property
  def email(self):
    return self._email

  @email.setter
  def email(self, email):
    if not self._validate_email(email):
      raise Exception("Email <%s> is not valid!" % email)
    self._email = email
    get_users().update({'_id' : self._name},
                       {'$set' : { 'email' : email }})

  @property
  def id(self):
    return self._name
  
  def is_authenticate(self):
    return self._authenticated 

  def is_anonymous(self):
    return not self.is_authenticated()

  def authenticate(self, pwd):
    """
    checks if the given password for the user is valid.
    @return: True: OK, False: wrong password.
    """
    #from time import time
    #t1 = time()
    for i in range(rmin, rmax + 1):
      if self._password == hashpwd(pwd, str(i)):
        #log "AUTHENTICATED after %s!!" % (time() - t1)
        self._authenticated = True
        break
    return self._authenticated

  def _validate_email(self, email):
    """should do a regex match"""
    return True

  @staticmethod
  def get(userid):
    """
    De-Serializes the MongoDB entry to a LmfdbUser object,
    or returns None.
    """
    u = get_users().find_one({'_id' : userid})
    if not u:
      return None
    user = LmfdbUser(userid, u['password'])
    for key in ['full_name', 'email']:
      if u.has_key(key): setattr(user, key, u[key])
    return user



def new_user(name, pwd = None):
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
  if get_users().find({'_id' : name}).count() > 0:
    raise Exception("ERROR: User %s already exists" % name)
  password = hashpwd(pwd)
  get_users().save({'_id' : name, 
              'email' : email,
              'password' : password
              })
  new_user = LmfdbUser(name, password)
  return new_user

  
def user_exists(name):
  return get_users().find({'_id' : name}).count() > 0



from flaskext.login import LoginManager
login_manager = LoginManager()



@login_manager.user_loader
def load_user(userid):
  return LmfdbUser.get(userid) 


if __name__=="__main__":
  print "add user"
  print "remove user"
  print "…"
 
