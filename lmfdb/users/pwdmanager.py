#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# store passwords, check users, ...
# password hashing is done with fixed and variable salting
# Author: Harald Schilly <harald.schilly@univie.ac.at>
# Modified : Chris Brady and Heather Ratcliffe

# NEVER EVER change the fixed_salt!
fixed_salt = '=tU\xfcn|\xab\x0b!\x08\xe3\x1d\xd8\xe8d\xb9\xcc\xc3fM\xe9O\xfb\x02\x9e\x00\x05`\xbb\xb9\xa7\x98'

from lmfdb.db_backend import PostgresBase, db
from lmfdb.db_encoding import Array
from psycopg2.sql import SQL, Identifier, Placeholder
from datetime import datetime, timedelta

from main import logger, FLASK_LOGIN_VERSION, FLASK_LOGIN_LIMIT
from distutils.version import StrictVersion

# Read about flask-login if you are unfamiliar with this UserMixin/Login
from flask_login import UserMixin, AnonymousUserMixin

class PostgresUserTable(PostgresBase):
    def __init__(self):
        PostgresBase.__init__(self, 'db_users', db)
        # never narrow down the rmin-rmax range, only increase it!
        self.rmin, self.rmax = -10000, 10000
        self._rw_userdb = db.can_read_write_userdb()
        #TODO use this instead of hardcoded columns names
        #with identifiers
        self._username_full_name = ["username", "full_name"]
        if self._rw_userdb:
            cur = self._execute(SQL("SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s"), ['userdb', 'users'])
            self._cols = [rec[0] for rec in cur]
        else:
            self._cols = self._username_full_name

    def can_read_write_userdb(self):
        return self._rw_userdb

    def get_random_salt(self):
        """
        Generates a random salt.
        This random_salt is a way to have the passwords and code public,
        but still make it very hard to guess it.
        once computers are 10x faster, change the rmin,rmax limits
        """
        import random
        return str(random.randrange(self.rmin, self.rmax))

    def hashpwd(self, pwd, random_salt=None):
        """
        Globally unique routine how passwords are hashed.
        Once in production, never ever change it - otherwise all
        passwords are useless.
        """
        from hashlib import sha256
        hashed = sha256()
        hashed.update(pwd)  # pwd must come first!
        if not random_salt:
            random_salt = self.get_random_salt()
        hashed.update(random_salt)
        hashed.update(fixed_salt)  # fixed salt must come last!
        return hashed.hexdigest()

    def bchash(self, pwd, existing_hash = None):
        """
        Generate a bcrypt based password hash. Intended to replace
        Schilly's original hashing algorithm
        """
        try:
            import bcrypt
            if not existing_hash:
                existing_hash = unicode(bcrypt.gensalt())
            return bcrypt.hashpw(pwd.encode('utf-8'), existing_hash.encode('utf-8'))
        except Exception:
            logger.warning("Failed to return bchash, perhaps bcrypt is not installed");
            return None

    def new_user(self, uid, pwd=None, full_name=None, about=None, url=None):
        """
        generates a new user, asks for the password interactively,
        and stores it in the DB. This is now replaced with bcrypt version
        """
        if not self._rw_userdb:
            logger.info("no attempt to create user, not enough privileges")
            return LmfdbAnonymousUser()

        if self.user_exists(uid):
            raise Exception("ERROR: User %s already exists" % uid)
        if not pwd:
            from getpass import getpass
            pwd_input = getpass("Enter  Password: ")
            pwd_input2 = getpass("Repeat Password: ")
            if pwd_input != pwd_input2:
                raise Exception("ERROR: Passwords do not match!")
            pwd = pwd_input
        password = self.bchash(pwd)
        from datetime import datetime
        #TODO: use identifiers
        insertor = SQL(u"INSERT INTO userdb.users (username, bcpassword, created, full_name, about, url) VALUES (%s, %s, %s, %s, %s, %s)")
        self._execute(insertor, [uid, password, datetime.utcnow(), full_name, about, url])
        new_user = LmfdbUser(uid)
        return new_user

    def change_password(self, uid, newpwd):
        if self._rw_userdb:
            bcpass = self.bchash(newpwd)
            #TODO: use identifiers
            updater = SQL("UPDATE userdb.users SET (bcpassword) = (%s) WHERE username = %s")
            self._execute(updater, [bcpass, uid])
            logger.info("password for %s changed!" % uid)
        else:
            logger.info("no attempt to change password, not enough privileges")

    def user_exists(self, uid):
        selecter = SQL("SELECT username FROM userdb.users WHERE username = %s")
        cur = self._execute(selecter, [uid])
        return cur.rowcount > 0

    def get_user_list(self):
        """
        returns a list of tuples: [('username', 'full_name'),…]
        If full_name is None it will be replaced with username.
        """
        #TODO: use identifiers
        selecter = SQL("SELECT username, full_name FROM userdb.users")
        cur = self._execute(selecter)
        return [(uid, full_name or uid) for uid, full_name in cur]

    def authenticate(self, uid, pwd, bcpass=None, oldpass=None):
        if not self._rw_userdb:
            logger.info("no attempt to authenticate, not enough privileges")
            return False

        #TODO: use identifiers
        selecter = SQL("SELECT bcpassword, password FROM userdb.users WHERE username = %s")
        cur = self._execute(selecter, [uid])
        if cur.rowcount == 0:
            raise ValueError("User not present in database!")
        bcpass, oldpass = cur.fetchone()
        if bcpass:
            if bcpass == self.bchash(pwd, existing_hash = bcpass):
                return True
        else:
            for i in range(self.rmin, self.rmax + 1):
                if oldpass == self.hashpwd(pwd, str(i)):
                    bcpass = self.bchash(pwd)
                    if bcpass:
                        logger.info("user " + uid  +  " logged in with old style password, trying to update")
                        try:
                            #TODO: use identifiers
                            updater = SQL("UPDATE userdb.users SET (bcpassword) = (%s) WHERE username = %s")
                            self._execute(updater, [bcpass, uid])
                            logger.info("password update for " + uid + " succeeded")
                        except Exception:
                            #if you can't update the password then likely someone is using a local install
                            #log and continue
                            logger.warning("password update for " + uid + " failed!")
                        return True
                    else:
                        logger.warning("user " + uid + " logged in with old style password, but update was not possible")
                        return False
        return False

    def save(self, data):
        if not self._rw_userdb:
            logger.info("no attempt to save, not enough privileges")
            return;

        data = dict(data) # copy
        uid = data.pop("username",None)
        if not uid:
            raise ValueError("data must contain username")
        if not self.user_exists(uid):
            raise ValueError("user does not exist")
        if not data:
            raise ValueError("no data to save")
        fields, values = zip(*data.items())
        updater = SQL("UPDATE userdb.users SET ({0}) = ({1}) WHERE username = %s").format(SQL(", ").join(map(Identifier, fields)), SQL(", ").join(Placeholder() * len(values)))
        self._execute(updater, list(values) + [uid])

    def lookup(self, uid):
        selecter = SQL("SELECT {0} FROM userdb.users WHERE username = %s").format(SQL(", ").join(map(Identifier, self._cols)))
        cur = self._execute(selecter, [uid])
        if cur.rowcount == 0:
            raise ValueError("user does not exist")
        if cur.rowcount > 1:
            raise ValueError("multiple users with same username!")
        return {field:value for field,value in zip(self._cols, cur.fetchone()) if value is not None}

    def full_names(self, uids):
        #TODO: use identifiers
        selecter = SQL("SELECT username, full_name FROM userdb.users WHERE username = ANY(%s)")
        cur = self._execute(selecter, [Array(uids)])
        return [{k:v for k,v in zip(["username","full_name"], rec)} for rec in cur]

    def create_tokens(self, tokens):
        if not self._rw_userdb:
            return;

        insertor = SQL("INSERT INTO userdb.tokens (id, expire) VALUES %s")
        now = datetime.utcnow()
        tdelta = timedelta(days=1)
        exp = now + tdelta
        self._execute(insertor, [(t, exp) for t in tokens], values_list=True)

    def token_exists(self, token):
        if not self._rw_userdb:
            logger.info("no attempt to check if token exists, not enough privileges")
            return False;
        selecter = SQL("SELECT 1 FROM userdb.tokens WHERE id = %s")
        cur = self._execute(selecter, [token])
        return cur.rowcount == 1

    def delete_old_tokens(self):
        if not self._rw_userdb:
            logger.info("no attempt to delete old tokens, not enough privileges")
            return;
        deletor = SQL("DELETE FROM userdb.tokens WHERE expire < %s")
        now = datetime.utcnow()
        tdelta = timedelta(days=8)
        cutoff = now - tdelta
        self._execute(deletor, [cutoff])

    def delete_token(self, token):
        if not self._rw_userdb:
            return;
        deletor = SQL("DELETE FROM userdb.tokens WHERE id = %s")
        self._execute(deletor, [token])

userdb = PostgresUserTable()

class LmfdbUser(UserMixin):
    """
    The User Object

    It is backed by MongoDB.
    """
    properties = ('full_name', 'url', 'about')

    def __init__(self, uid):
        if not isinstance(uid, basestring):
            raise Exception("Username is not a basestring")

        self._uid = uid
        self._authenticated = False
        self._dirty = False  # flag if we have to save
        self._data = dict([(_, None) for _ in LmfdbUser.properties])

        if userdb.user_exists(uid):
            self._data.update(userdb.lookup(uid))

    @property
    def name(self):
        return self.full_name or self._data.get('username')

    @property
    def full_name(self):
        return self._data['full_name']

    @full_name.setter
    def full_name(self, full_name):
        self._data['full_name'] = full_name
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
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        self._data['url'] = url
        self._dirty = True

    @property
    def created(self):
        return self._data.get('created')

    @property
    def id(self):
        return self._data['username']

    # def is_authenticated(self):
    #     """required by flask-login user class"""
    #     return self._authenticated

    def is_anonymous(self):
        """required by flask-login user class"""
        if StrictVersion(FLASK_LOGIN_VERSION) < StrictVersion(FLASK_LOGIN_LIMIT):
            return not self.is_authenticated()
        return not self.is_authenticated

    def is_admin(self):
        """true, iff has attribute admin set to True"""
        return self._data.get("admin", False)

    def authenticate(self, pwd):
        """
        checks if the given password for the user is valid.
        @return: True: OK, False: wrong password.
        """
        if not 'password' in self._data and not 'bcpassword' in self._data:
            logger.warning("no password data in db for '%s'!" % self._uid)
            return False
        self._authenticated = userdb.authenticate(self._uid, pwd)
        return self._authenticated

    def save(self):
        if not self._dirty:
            return
        logger.debug("saving '%s': %s" % (self.id, self._data))
        userdb.save(self._data)
        self._dirty = False

class LmfdbAnonymousUser(AnonymousUserMixin):
    """
    The sole purpose of this Anonymous User is the 'is_admin' method
    and probably others.
    """
    def is_admin(self):
        return False

    def name(self):
        return "Anonymous"

    # For versions of flask_login earlier than 0.3.0,
    # AnonymousUserMixin.is_anonymous() is callable. For later versions, it's a
    # property. To match the behavior of LmfdbUser, we make it callable always.
    def is_anonymous(self):
        return True

if __name__ == "__main__":
    print "Usage:"
    print "add user"
    print "remove user"
    print "…"
