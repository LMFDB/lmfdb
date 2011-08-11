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

def get_random_salt():
  """
  generates a random salt
  once computers are 10x faster, change the rmin,rmax limits
  """
  import random
  return str(random.randrange(rmin, rmax))
  
def hashpwd(pwd, random_salt = None):
  """
  globally unique routine how passwords are hashed
  """
  from hashlib import sha256
  hashed = sha256()
  hashed.update(pwd) # pwd must come first!
  if not random_salt:
    random_salt = get_random_salt()
  hashed.update(random_salt)
  hashed.update(fixed_salt) # fixed salt must come last!
  return hashed.hexdigest()


from flaskext.login import UserMixin

class LmfdbUser(UserMixin):
  """
  The User
  """
  def __init__(self, name, email, password):
    if not name or not isinstance(name, basestring):
      raise Exception("Username is not a basestring")
    if not email or not isinstance(email, basestring):
      raise Exception("Email is not a basestring")
    if not password or not isinstance(password, basestring):
      raise Exception("Password is not a proper Hash (and not a basestring)")
    if not self._validate_email(email):
      raise Exception("Email <%s> is not valid!" % email)

    self.name = name
    self.email = email
    self.password = password
    self.authenticated = False
    self.full_name = None

  def get_name(self):
    return self.full_name or self.name

  def set_full_name(self, full_name):
    self.full_name = full_name
    users.update({'_id' : self.name} ,
                 {'$set' : { 'full_name' : full_name }})

  def set_email(self, email):
    self.email = email
    users.update({'_id' : self.name},
                 {'$set' : { 'email' : email }})

  def get_id(self):
    return self.name
  
  def is_authenticate(self):
    return self.authenticated 

  def is_anonymous(self):
    return not self.is_authenticated()

  def authenticate(self, pwd):
    self.authenticated = validate(self.name, pwd) 
    return self.authenticated

  def _validate_email(self, email):
    """should do a regex match"""
    return True

  def validate(self, pwd):
    """
    checks if the given password for the user is valid.
    @return: True: OK, False: wrong password.
    """
    from time import time
    t1 = time()
    challange = self.password

    for i in range(rmin, rmax + 1):
      if challange == hashpwd(pwd, str(i)):
        #log "AUTHENTICATED after %s!!" % (time() - t1)
        return True
    return False

  @staticmethod
  def get(userid):
    u = users.find_one({'_id' : userid})
    if not u:
      return None
    user = LmfdbUser(userid, u['email'], u['password'])
    if u.has_key("full_name"):
      user.full_name = u['full_name']
    return user



def new_user(name, email, pwd = None):
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
  if users.find({'_id' : name}).count() > 0:
    raise Exception("ERROR: User %s already exists" % name)
  password = hashpwd(pwd)
  users.save({'_id' : name, 
              'email' : email,
              'password' : password
              })
  new_user = LmfdbUser(name, email, password)
  return new_user

  



from flaskext.login import LoginManager
login_manager = LoginManager()



@login_manager.user_loader
def load_user(userid):
  return LmfdbUser.get(userid) 


if __name__=="__main__":
  print "add user"
  print "remove user"
  print "…"
 
