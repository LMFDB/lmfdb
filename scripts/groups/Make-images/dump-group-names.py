import sys, os
HOME=os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'lmfdb'))
from lmfdb import db

eqguts=open("eqguts.tex", "w")
prettyindex=open("prettyindex", "w")
a=db.gps_groups.search()

myhash = {}

for g in a:
    p = str(g['tex_name'])
    l = myhash.get(p, [])
    l.append(g['label'])
    myhash[p] = l

count = 1
prettyindex.write('[1,"?"]\n')
eqguts.write(r'$?$'+'\n')
for p in myhash.keys():
    pp = p.replace('\\', '\\\\')
    eqguts.write('$'+str(p)+'$\n')
    count += 1
    prettyindex.write('[%d, "%s"]\n'%(count, pp))

eqguts.close()
prettyindex.close()

print ("Max count is %d" % count)
