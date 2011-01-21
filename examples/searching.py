# search in arrays of ints or bucket search for floats in arrays
# copyright: harald schilly <harald.schilly@gmail.com>
# license: Apache 2.0

from pymongo import *
import random
from math import floor, ceil

test = Connection(port=37010).testdb.test
test.remove()
test.ensure_index('list')

for i in range(10):
   test.insert({'list': range(1+i, 4+2*i)})

print "all data"
for e in test.find(sort=[('list', 1)]):
    print e['list']

print

value = 17
print "entries that contain %s" % value
for r in test.find({'list' : { '$in' : [value] }}, sort=[('list', 1)]):
    print r['list']

print

query = [10, 9, 17]
print "all entries that contain %s in the array of key '%s'"% (query, 'list')
for r in test.find({'list' : { '$all' : query }}):
    print r['list']

for i in range(1000):
    vals = [ 10 * random.random() for _ in range(2,10)]
    test.insert({'val' : vals})
test.insert({'val' : [5.5232, 1.212121, 9.919191, 11.1111]})


#def mkinterval(x, digits = 2):
#    v = x * 10**digits
#    low = int(floor(v))
#    up = int(ceil(v))
#    return '%s::%s' % (low, up)


#def significant(x, n):
#    import math
#    val = int(n - math.ceil(math.log10(abs(x))))
#    return int(round(x, val) * 10**val)

def significant(x, n):
    import math
    return int(floor(x*10**n))


for e in test.find({'val' : {'$exists': True}}):
    s = {}
    for d in [2,3,4]:
        v = [ significant(_,d) for _ in e['val'] ]
        s['%s'%d] = v
    e['search'] = s
    test.save(e)

if False:
    for e in test.find({'val' : {'$exists': True}}, limit=10):
        print e['search']
    import sys;sys.exit()
        
query = test.find_one({'val' : {'$exists': True}})['search']['3'][0:2]
print
print "searching for %s (i.e. %s) in '%s'" % (query, [(float(_)/10**3, float(_+1)/10**3) for _ in query], 'search')
for e in test.find({'val' : {'$exists': True}, 'search.3' : {'$all' : query}}, sort=[('val', 1)]):
    print sorted(e['search']['3']), "->", sorted(e['val'])


print
x = 5.013401
print "explicitly searching for %s" % x
xq = significant(x, 3)
print "actually querying for %s which stands for (%s, %s)" % (xq, float(xq)/10**3, float(xq+1)/10**3)
print
for e in test.find({'val' : {'$exists': True}, 'search.3' : {'$all' : [xq]}}, sort=[('val', 1)]):
    print sorted(e['search']['3']), "->", sorted(e['val'])

print
d = 2
x = 1.212
y = 11.11
print "expcitly searching for %s and %s" % (x,y)
xq = significant(x, d)
yq = significant(y, d)
print "actually querying for %s which stands for (%s, %s)" % (xq, float(xq)/10**d, float(xq+1)/10**d)
print "AND"
print "actually querying for %s which stands for (%s, %s)" % (yq, float(yq)/10**d, float(yq+1)/10**d)
print
for e in test.find({'val' : {'$exists': True}, 'search.%d'%d : {'$all' : [xq, yq]}}, sort=[('val', 1)]):
    print sorted(e['search']['%d'%d]), "->", sorted(e['val'])


