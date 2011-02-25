# reference other objects in the same collection or across to other collections *automatically*
# copyright: harald schilly <harald.schilly@gmail.com>
# license: Apache 2.0


from pymongo import *
import base

db = base.getDBConnection().db
data1 = db.refdata1
data1.remove()
data2 = db.refdata2
data2.remove()

# here comes the magic:
db.add_son_manipulator(son_manipulator.AutoReference(db))
#enable NamespaceInjector if you reference documents in other collections
db.add_son_manipulator(son_manipulator.NamespaceInjector())

# random data
for i in range(10):
    data1.insert({'i' : i})

for i in range(2,4):
    element = data1.find_one({'i' : i})
    # here we reference from a doc in data2 to a doc in data1
    data2.insert({'k' : i+100, 'ref' : element})

# see what's in the collections
print "data1:"
for e in data1.find():
    print e
print
for e in data2.find():
    print e

#deref happens automatically
print
print "dereferencing: "
print data2.find_one()['ref']['i']

