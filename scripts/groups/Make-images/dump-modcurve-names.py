import sys, os, re
from collections import defaultdict
HOME=os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'sage', 'lmfdb'))
from lmfdb import db

myhash = defaultdict(list)

triples = set((rec["level"], rec["index"], rec["genus"]) for rec in db.gps_gl2zhat.search({"contains_negative_one":True}, ["level", "index", "genus"]))

FAM_RE = re.compile(r"X([^\(]*)\((\d+(,\d+)?)\)")

count = 1
with open("eqguts.tex", "w") as eqguts:
    with open("prettyindex", "w") as prettyindex:
        prettyindex.write('[1,"?"]\n')
        eqguts.write(r'$?$'+'\n')
        for (level, index, genus) in triples:
            pp = "%s_{%s}^{%s}" % (level, index, genus)
            eqguts.write(f'${pp}$\n')
            count += 1
            prettyindex.write('[%d, "%s"]\n'%(count, pp))
        for name in db.gps_gl2zhat.search({"name":{"$ne":""}}, "name"):
            fam, n, _ = FAM_RE.fullmatch(name).groups()
            if fam == "0":
                fam = "_0"
            elif fam == "1":
                fam = "_1"
            elif fam == "pm1":
                fam = r"_{\pm 1}"
            elif fam == "sp":
                fam = r"_{\mathrm{sp}}"
            elif fam == "ns":
                fam = r"_{\mathrm{ns}}"
            elif fam == "sp+":
                fam = r"_{\mathrm{sp}}^+"
            elif fam == "ns+":
                fam = r"_{\mathrm{ns}}^+"
            elif fam == "S4":
                fam = r"_{S_4}"
            elif fam != "":
                raise ValueError(fam)
            tex = f"X{fam}({n})"
            pp = name
            eqguts.write(f'${tex}$\n')
            count += 1
            prettyindex.write('[%d, "%s"]\n'%(count, pp))

print ("Max count is %d" % count)
