# Map/Reduce example for MongoDB
# returns the minimum and maxium lenght of the interval between two values with sign changes around the origin.
# this mimics searching for ranges where there is no root around the origin.
# copyright harald schilly <harald.schilly@gmail.com>
# license apach 2.0

from pymongo import *
from bson import Code
from random import random
import base

mr = base.getDBConnection().testdb.mr

mr.remove()

entries = []
for _ in range(100):
    entries.append({'vector': [ 10 * random() - 5 for _ in range(100)] })
mr.insert(entries)
print list(mr.find(limit=1))

fmap = Code('function() { \
                this.vector.sort(); \
                if (this.vector[0] > 0 || this.vector[this.vector.length -1] < 0) { return; }; \
                var last = this.vector[0];\
                var m1 = 99999999; \
                var m2 = 0; \
                var o = null; \
                for (var i = 1; i < this.vector.length;  i++ ) { \
                    var cur  = this.vector[i]; \
                    if (cur * last < 0) { \
                         var t = cur - last; \
                         if (t < m1) { m1=t; }; \
                         if (t > m2) { m2=t; }; \
                         continue; \
                    }; \
                    last = this.vector[i];\
                }; \
                emit("min", m1); \
                emit("max", m2); \
            }')

freduce = Code('function(k, objs) {\
                    var m = objs[0];\
                    for (var i = 0; i < objs.length; i++) {\
                       var val = objs[i]; \
                       if(val > m) { m = val; };  \
                    };    \
                    return m; \
                }; ')


for e in mr.map_reduce(fmap, freduce).find():
    print e


