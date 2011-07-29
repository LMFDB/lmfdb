#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# store passwords, check users, ...
# password hashing is done with fixed and variable salting

# never ever change the fixed_salt!
fixed_salt = '=tU\xfcn|\xab\x0b!\x08\xe3\x1d\xd8\xe8d\xb9\xcc\xc3fM\xe9O\xfb\x02\x9e\x00\x05`\xbb\xb9\xa7\x98'

import os
from pymongo import Connection
C = Connection("localhost:40000")
userdb = C.userdb
users = userdb.users

rmin = -10000
rmax =  10000

def random_salt(rmin, rmax):
  """
  generates a random salt
  once computers are 10x faster, change the rmin,rmax limits
  """
  import random
  return str(random.randrange(rmin, rmax))
  
def hashpwd(pwd, random_salt):
  """
  globally unique routine how passwords are hashed
  """
  from hashlib import sha256
  hashed.update(pwd) # pwd must come first!
  hashed.update(fixed_salt)
  hashed = sha256(random_salt) # random seed must come last!
  return hashed.hexdigest()


from flaskext.login import UserMixin

class LmfdbUser(UserMixin):
  """
  The User
  """
  def __init__(self, name, email):
    if not name or not isinstance(name, basestring):
      raise Exception("Username is not a basestring")
    if not email or not isinstance(email, basestring):
      raise Exception("Email is not a basestring")
    if not self._validate_email(email):
      raise Exception("Email <%s> is not valid!" % email)

    self.name = name
    self.email = email
    self.authenticated = False

  def get_id(self):
    return self.name
  
  def is_authenticate(self):
    return self.authenticated 

  def is_anonymous(self):
    return not self.is_authenticated()

  def authenticate(self, pwd):
    self.authenticated = validate_user(self.name, pwd) 
    return self.authenticated

  def _validate_email(email):
    """should do a regex match"""
    return True

  @staticmethod
  def get(userid):
    u = users.find_one({'_id' : userid})
    if not u:
      return None
    user = LmfdbUser(userid, u['email'])
    return user



def new_user(name, email):
  """
  generates a new user, asks for the password interactively,
  and stores it in the DB.
  """
  from getpass import getpass
  pwd_input = getpass()
  pwd_input2 = getpass("Repeat Password")
  if pwd_input != pwd_input2:
    raise Exception("ERROR: Passwords do not match!")
  if users.find({'_id' : name}).count() > 0:
    raise Exception("ERROR: User %s already exists" % name)
  new_user = LmfdbUser(name, email)
  

def validate_user(name, pwd):
  """
  checks if the given password for the user is valid.
  @return: True: OK, False: wrong password.
  """
  from time import time
  t1 = time()
  
  user = users.find_one({"_id" : name})
  if not user:
    raise Exception("User %s not found!" % user)
  challange = user['pwd']

  for i in range(rmin, rmax + 1):
    if challange == hashpwd(pwd, str(i)):
      #log "AUTHENTICATED after %s!!" % (time() - t1)
      return True
  return False


from flaskext.login import LoginManager
login_manager = LoginManager()
login_manager.anonymous_user = "Anonymous"



@login_manager.user_loader
def load_user(userid):
  return LmfdbUser.get(userid) 


