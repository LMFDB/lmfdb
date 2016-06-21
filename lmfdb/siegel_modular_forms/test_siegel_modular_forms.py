# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest, getDBconnection
import math
import unittest2


class HomePageTest(LmfdbTest):

    def check(self,url,text):
        data = self.tc.get(url, follow_redirects=True).data
        if isinstance(text,list):
            for t in text:
                assert t in data
        else:
            assert text in data
                
    # All tests should pass: these are all the links in the browse page 
    def test_browse_page(self):
        """
        Check that the top level browse pages work
        """
        self.check("/ModularForm/GSp/Q/Sp4Z_j/10/0/", 'M_{10,0}')
        self.check("/ModularForm/GSp/Q/Sp4Z_j/",  'Upsilon')
        self.check("/ModularForm/GSp/Q/Kp/",  'in level 277, the')
        self.check("/ModularForm/GSp/Q/Sp6Z/",  'Miyawaki (1)')
        self.check("/ModularForm/GSp/Q/Sp8Z/",  'Other_II (2)')
        self.check("/ModularForm/GSp/Q/Gamma0_2/",  'Gamma_0(2)')
        self.check("/ModularForm/GSp/Q/Gamma1_2/",  'Gamma_1(2)')
        self.check("/ModularForm/GSp/Q/Gamma_2/",  'Gamma(2)')
        self.check("/ModularForm/GSp/Q/Gamma0_3/",  'Gamma_0(3)')
        self.check("/ModularForm/GSp/Q/Gamma0_3_psi_3/",  'T.Ibukiyama:')
        self.check("/ModularForm/GSp/Q/Gamma0_4/",  'Gamma_0(4)')
        self.check("/ModularForm/GSp/Q/Gamma0_4_psi_4/",  'psi_4')
        self.check("/ModularForm/GSp/Q/Gamma0_4_half/",  'k-1/2')

    def test_sample_pages(self):
        """
        Check all the sample pages (should take 10s on atkin)
        """
        errors = []
        samples = getDBConnection().siegel_modular_forms.experimental_samples
        data = samples.find({'collection':{'$exists':True},'name':{'$exists':True}},{'_id':False,'collection':True,'name':True})
        n = 0
        print ""
        for s in data:
            full_label = s['collection'][0] + "." + s['name']
            url = "/ModularForm/GSp/Q/"+full_label+"/"
            print "Checking home page for SMF sample " + full_label
            try:
                n = n+1
                self.check(url,[full_label,'Hecke eigenform'])
            except:
                print "Error on page " + url
                errors.append(url)
        if not errors:
            print "Tested %s pages with no errors" % n
        else:
            print "Tested %d pages with %d errors occuring on the following pages:" %(n,len(errors))
            for url in errors:
                print url

