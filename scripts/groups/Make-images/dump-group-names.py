import sys, os
from collections import defaultdict
HOME=os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'lmfdb'))
from lmfdb import db

myhash = defaultdict(list)

for g in db.gps_groups.search({}, ['tex_name', 'label']):
    myhash[g['tex_name']].append(g['label'])

for g in db.gps_subgroup_search.search({}, ['quotient_tex', 'subgroup_tex', 'label']):
    if g['quotient_tex']:
        myhash[g['quotient_tex']].append(g['label'])
    if g['subgroup_tex']:
        myhash[g['subgroup_tex']].append(g['label'])

count = 1
with open("eqguts.tex", "w") as eqguts:
    with open("prettyindex", "w") as prettyindex:
        prettyindex.write('[1,"?"]\n')
        eqguts.write(r'$?$'+'\n')
        for p in myhash.keys():
            pp = p.replace('\\', '\\\\')
            eqguts.write('$'+str(p)+'$\n')
            count += 1
            prettyindex.write('[%d, "%s"]\n'%(count, pp))

print ("Max count is %d" % count)
