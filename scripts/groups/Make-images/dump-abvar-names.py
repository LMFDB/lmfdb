import sys, os, re
from collections import defaultdict, Counter
HOME=os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'sage', 'lmfdb'))
from lmfdb import db
from sage.all import ZZ

num_wes = defaultdict(Counter)
num_ind = defaultdict(Counter)
pic_size = defaultdict(dict)
for rec in db.av_fq_weak_equivalences.search({}, ["is_invertible", "isog_label", "multiplicator_ring", "pic_size"]):
    ilabel, mring = rec["isog_label"], rec["multiplicator_ring"]
    N = mring.split(".")[0]
    num_wes[ilabel][mring] += 1
    if rec["is_invertible"]:
        num_ind[ilabel][N] += 1
        pic_size[ilabel][mring] = rec["pic_size"]

texdata = set((mring, pic_size[ilabel][mring], num_we, num_ind[ilabel][mring.split(".")[0]] > 1) for (ilabel, mrings) in num_wes.items() for (mring, num_we) in mrings.items())

count = 2
with open("eqguts.tex", "w") as eqguts:
    with open("prettyindex", "w") as prettyindex:
        prettyindex.write('[1,"?"]\n[2,"\\cdot"]\n')
        eqguts.write('$?$\n$\\cdot$\n')
        for (mring, pic, we_cnt, include_i) in texdata:
            N, i = mring.split(".")
            N = ZZ(N)
            if N == 1:
                factored_index = "1"
            else:
                factored_index = r"\cdot".join((f"{p}^{{{e}}}" if e > 1 else f"{p}") for (p, e) in N.factor())
            istr = f"_{{{i}}}" if include_i else ""
            we_pic = fr"{we_cnt}\cdot{pic}" if we_cnt > 1 else f"{pic}"
            pp = "[%s]^{%s}%s" % (factored_index, we_pic, istr)
            eqguts.write(f'${pp}$\n')
            count += 1
            prettyindex.write('[%d, "%s"]\n'%(count, pp))

print ("Max count is %d" % count)
