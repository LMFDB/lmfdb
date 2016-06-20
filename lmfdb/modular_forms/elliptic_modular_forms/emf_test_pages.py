
from lmfdb.base import LmfdbTest, getDBConnection

from flask import request
import unittest2
import sys

from views.emf_main import *
from . import emf_logger
emf_logger.setLevel(100)

version=1.3

def anum(a):
    return sum([26**i*(ord(a[len(a)-i-1])-ord('a')+1) for i in range(len(a))])

def check_orbit_list(a):
    return set([anum(c) for c in a]) == set(range(1,len(a)+1))

class EmfTest(LmfdbTest):

    def runTest():
        pass

    def check_spaces(self,data):
        errors = []
        forms = getDBConnection().modularforms2.webnewforms
        for s in data:
            if not 'space_label' in s:
                print "Record has no space_label attribute"
                print s
                errors.append("Missing label")
                continue
            if not 'level' in s or not 'weight' in s or not 'character' in s:
                print "Invalid space record in DB, missing on of the required attributes level, weight, character"
                print s
                errors.append(s['space_label'])
                continue
            if s['space_label'] != "%d.%d.%d"%(s['level'],s['weight'],s['character']):
                 print "Label %s does not match level=%d, weight=%d, character=%d"%(s['space_label'],s['level'],s['weight'],s['character'])
                 errors.append(s['space_label'])
                 continue
            if not 'hecke_orbits' in s:
                print "Space %s has no hecke_orbits attribute" % s['space_label']
                errors.append(s['space_label'])
            if not check_orbit_list(s['hecke_orbits']):
                print "Space %s has a bad list of Hecke orbits: %s" % (s['space_label'], s['hecke_orbits'])
                errors.append(s['space_label'])
            orbits = forms.find({'version':float(version),'parent':s['space_label']})
            olabels = [r.get('label','?') for r in orbits]
            if len(olabels) != len(s['hecke_orbits']) or set(olabels) != set(s['hecke_orbits']):
                print "Hecke orbit data in webnewforms for space %s is incomplete or inconsistent" % s['space_label']
                print "    %s versus %s" % (olabels,s['hecke_orbits'])
                errors.append(s['space_label'])
                continue
            orbits = orbits.rewind()
            odims = [r.get('dimension') for r in orbits] 
            if sum(odims) != s.get('dimension_new_cusp_forms',-1):
                print "Hecke orbit dimensions %s do not sum to %d for space %s" % (odims, s['dimension_new_cusp_forms'], s['space_label'])
                errors.append(s['space_label'])
            l = s['space_label'].split('.')
            url = "ModularForm/GL2/Q/holomorphic/%s/%s/%s/"%(l[0],l[1],l[2])
            print "Checking %s (%d Hecke orbits, total dimension %d)"%(url,len(s['hecke_orbits']),s['dimension_new_cusp_forms'])
            try:
                page = self.tc.get(url, follow_redirects=True)
            except:
                print "Internal server error on page "+url
                errors.append(s['space_label'])
                continue
            if s['dimension_new_cusp_forms'] == 0:
                if not "no newforms of this weight, level and character" in page.data:
                    print "Failed on", url
                    errors.append(s['space_label'])
            else:
                if not ("Decomposition of" in page.data and "irreducible Hecke orbits" in page.data):
                    print "Failed on", url
                    errors.append(s['space_label'])
                orbits.rewind()
                for r in orbits:
                    if not 'hecke_orbit_label' in r:
                        print "No hecke_orbit_label attribute in record"
                        print r
                        errors.append('no hecke orbit label')
                        continue
                    if not r['hecke_orbit_label'] in page.data:
                        print "Hecke orbit label %s does not appear on page %s"%(r['hecke_orbit_label'],url)
                        errors.append(r['hecke_orbit_label'])
                orbits.rewind()
                for r in orbits:
                    if not 'hecke_orbit_label' in r:
                        print "no hecke_orbit_label in ", r
                        errors.append(r['hecke_orbit_label'])
                    l = r['hecke_orbit_label'].split('.')
                    if len(l) != 4:
                        print 'bad hecke_orbit_label', l
                        errors.append(r['hecke_orbit_label'])
                    url = "ModularForm/GL2/Q/holomorphic/%s/%s/%s/%s/"%(l[0],l[1],l[2],l[3])
                    print "Checking %s"%url
                    try:
                        page = self.tc.get(url, follow_redirects=True)
                    except:
                        print "Internal server error on page "+url
                        errors.append(r['hecke_orbit_label'])
                        continue
                    if not ("Coefficient field" in page.data and "Download this Newform" in page.data and r['hecke_orbit_label'] in page.data):
                        print 'Failed on', url
                        errors.append(r['hecke_orbit_label'])
        return errors
    
    def test_gamma0_pages(self):
        errors = []
        spaces = getDBConnection().modularforms2.webmodformspace
        wmax = 40; Nmax = 25
        data = spaces.find({'weight':{'$ge':int(2)},'weight':{'$lt':int(wmax+1)},'level':{'$lt':int(Nmax+1)},'character':int(1),'version':float(version)})
        print "Checking %d spaces with trivial character of weight w <= %d and level N <= %d"%(data.count(),wmax,Nmax)
        errors = self.check_spaces(data)
        if errors:
            print "Errors occurred for the following labels: ", errors
        wmax = 12; Nmax = 100
        data = spaces.find({'weight':{'$ge':int(2)},'weight':{'$lt':int(wmax+1)},'level':{'$lt':int(Nmax+1)},'character':int(1),'version':float(version)})
        print "Checking %d spaces with trivial character of weight w <= %d and level N <= %d"%(data.count(),wmax,Nmax)
        errors = self.check_spaces(data)
        if errors:
            print "Errors occurred for the following labels: ", errors

    def test_gamma1_pages(self):
        errors = []
        spaces = getDBConnection().modularforms2.webmodformspace
        wmax = 10; Nmax = 50
        data = spaces.find({'weight':{'$ge':int(2)},'weight':{'$lt':int(wmax+1)},'level':{'$lt':int(Nmax+1)},'version':float(version)})
        print "Checking %d spaces of weight w <= %d and level N <= %d"%(data.count(),wmax,Nmax)
        errors = self.check_spaces(data)
        if errors:
            print "Errors occurred for the following labels: ", errors
        wmax = 20; Nmax = 16
        data = spaces.find({'weight':{'$ge':int(2)},'weight':{'$lt':int(wmax+1)},'level':{'$lt':int(Nmax+1)},'version':float(version)})
        print "Checking %d spaces of weight w <= %d and level N <= %d"%(data.count(),wmax,Nmax)
        errors = self.check_spaces(data)
        if errors:
            print "Errors occurred for the following labels: ", errors
