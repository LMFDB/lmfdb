import sys

def usage():
    print ''' Usage: to change a password, type 'sage user-manager.py
    changepassword username newpassword'.  You must have a file
    passwords.yaml in the current directory which holds the
    authentication passwords.  '''

def changepassword(username, newpassword):
    from lmfdb.base import getDBConnection
    C= getDBConnection()
    import yaml
    pw_dict = yaml.load(open("passwords.yaml"))
    C['userdb'].authenticate(pw_dict['data']['username'],
                             pw_dict['data']['password'])

    from lmfdb.users import pwdmanager
    pwdmanager.change_password(username, newpassword)

if len(sys.argv) != 4:
    usage()
    sys.exit(0)

if sys.argv[1] == 'changepassword':
    changepassword(sys.argv[2], sys.argv[3])
else:
    usage()
