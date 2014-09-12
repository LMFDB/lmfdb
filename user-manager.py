import sys

def usage():
    print \
'''
    Usage: to change a password, type 'sage user-manager.py changepassword username newpassword'
'''

def changepassword(username, newpassword):
    import lmfdb.users.pwdmanager
    lmfdb.users.pwdmanager.change_password(username, newpassword)

if len(sys.argv) < 1:
    usage()
    sys.exit(0)

if sys.argv[1] == 'changepassword':
    changepassword(sys.argv[2], sys.argv[3])
else:
    usage()
