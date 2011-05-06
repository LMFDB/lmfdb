r"""
Import data from cremona tables and merging or updating existing database. 
Before running this script run import_ec_data.py

Gagan Sekhon (2011)
"""
import os.path, gzip, re, sys, time
import pymongo
import base

conn = base.getDBConnection()
isogeny=conn.ellcurves.isogeny
curves=conn.ellcurves.curves

###Import isogenies into isogeny table

sw_label_regex=re.compile(r'sw(\d+)(\.)(\d+)(\.*)(\d*)')

whitespace = re.compile(r'\s+')
def split(line):
    return whitespace.split(line.strip())
    
    
def degphi(line):
    data=split(line)
    label = data[0] + data[1]+data[2]
    iso= data[0] + data[1]
    return label,iso, {
        'degree':data[3]
    }
    
def lookup_or_create(label, *args):
    item = isogeny.find_one({'label': label})
    if len(args)==0 and item is None:
        return {'label':label}
    elif len(args)!=0:
        item=isogeny.find_one({'label':swlabel})
        print swlabel
        if item is None:
            return {'label': label,'swlabel':swlabel}
        else:
            item.update({'label':label, 'swlabel':swlabel})
            isogeny.save(item)
    return item

for path in sys.argv[1:]:
    print path
    for file in glob.glob( os.path.join(path, '*.*') ):
        filename = os.path.basename(file)
        
        base = filename[:filename.find('.')]
        print base
        range=filename[filename.find('.'):]
        r=range[1:].split('-')
        if base not in globals():
            print "Ignoring", file
            continue
        parse = globals()[base]
        print parse
        h = gzip.open(file) if filename[-3:] == '.gz' else open(file)
        t = time.time()
        for line in h.readlines():
            label,iso,data = parse(line)
            print label
            c=curves.find_one({'label':label})
            print c
            if c is None:
                print 'c'
                break
            elif'swlabel' in c:
                N,d1, iso,d2, number = sw_label_regex.match(c['swlabel']).groups()
                swlabel='sw'+str(N)+'.'+str(iso)
                info = lookup_or_create(iso,swlabel)
            else:
                info=lookup_or_create(iso)
            info.update(data)
            b=isogeny.save(info)
            if time.time() - t > 5:
                print "\t", label
                t = time.time()
                
for i in srange(int(r[0]), int(r[1])):
    r=curves.find({'conductor':int(i),'number':int(1)})
    for s in r:
        E=EllipticCurve([int(a) for a in s['ainvs']])
        Isogeny_matrix=list(E.isogeny_class()[-1])
        label=s['iso']
        print label
        curves_in_the_class=[a['label'] for a in curves.find({'conductor':s['conductor'], 'iso':s['iso']})]
        info=lookup_or_create(label)
        data={'label_of_curves_in_the_class':curves_in_the_class,'isogeny_matrix':str(Isogeny_matrix),'rank':int(s['rank']),'ainvs_for_optimal_curve':s['ainvs']}
        info.update(data)
        a=isogeny.save(info)



