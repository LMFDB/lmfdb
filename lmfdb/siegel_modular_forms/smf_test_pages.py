# -*- coding: utf-8 -*-
from lmfdb.base import LmfdbTest
from lmfdb.db_backend import db

class SMFPageTest(LmfdbTest):

    def runTest():
        pass

    def test_all_pages(self):
        errors = []
        data = db.smf_samples.search({'collection':{'$exists':True},'name':{'$exists':True}},['collection','name'])
        n = 0
        print ""
        for s in data:
            full_label = s['collection'][0] + "." + s['name']
            url = "/ModularForm/GSp/Q/"+full_label+"/"
            print "Checking home page for SMF sample " + full_label
            try:
                n = n+1
                pagedata = self.tc.get(url, follow_redirects=True).data
                #print "Got %d bytes" % len(pagedata)
                assert full_label in pagedata and "Hecke eigenform" in pagedata
            except:
                print "Error on page " + url
                errors.append(url)
        if not errors:
            print "Tested %s pages with no errors" % n
        else:
            print "Tested %d pages with %d errors occuring on the following pages:" %(n,len(errors))
            for url in errors:
                print url
