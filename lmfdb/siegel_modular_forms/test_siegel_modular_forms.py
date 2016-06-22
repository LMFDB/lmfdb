# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest, getDBConnection
import math
import unittest2

class HomePageTest(LmfdbTest):

    def check(self,url,text):
        data = self.tc.get("/ModularForm/GSp/Q/"+url, follow_redirects=True).data
        if isinstance(text,list):
            for t in text:
                assert t in data, "expected string '%s' not found in page /ModularForm/GSp/Q/%s"%(t,url)
        else:
            assert text in data
                
    def test_random_page(self):
        """
        Test random sample page
        """
        self.check("random", "Hecke eigenform")

    def test_browse_page(self):
        """
        Test the top level browse pages
        """
        self.check("Sp4Z_j/",  'Upsilon')
        self.check("Sp4Z/",  ['Galois orbits', 'Klingen', 'Eisenstein', 'Maass', 'Saito-Kurokawa'])
        self.check("Sp4Z_2/",  ['Galois orbits', 'Cusp', 'Non cusp', 'Satoh bracket'])
        self.check("Kp/",  'in level 277, the')
        self.check("Sp6Z/",  'Miyawaki (1)')
        self.check("Sp8Z/",  'Other_II (2)')
        self.check("Gamma0_2/",  'Gamma_0(2)')
        self.check("Gamma1_2/",  'Gamma_1(2)')
        self.check("Gamma_2/",  'Gamma(2)')
        self.check("Gamma0_3/",  'Gamma_0(3)')
        self.check("Gamma0_3_psi_3/",  'T.Ibukiyama:')
        self.check("Gamma0_4/",  'Gamma_0(4)')
        self.check("Gamma0_4_psi_4/",  'psi_4')
        self.check("Gamma0_4_half/",  'k-1/2')
        self.check("Sp4Z_j/10/10/", 'M_{10,10}')
        self.check("Sp4Z/10/", 'M_{10,0}')
        self.check("Sp4Z_2/10/", 'M_{10,2}')
        
    def test_dimension_tables(self):
        """
        Check dimension table pages
        """
        self.check("?col=Sp4Z_j&k=&j=&table=1", ["Cusp", "Non cusp"])
        self.check("?col=Sp4Z_j&k=&j=2&table=1", ["Cusp", "Non cusp"])
        self.check("?col=Gamma0_2&k=&j=&table=1", ["Cusp", "Non cusp"])
        self.check("?col=Gamma0_2&k=&j=2&table=1", ["Cusp", "Non cusp"])
        self.check("?col=Gamma1_2&k=&j=&table=1", ["111", "21"])
        self.check("?col=Gamma1_2&k=&j=2&table=1", ["111", "21"])
        self.check("?col=Gamma2_2&k=&j=&table=1", ["111111", "3111"])
        self.check("?col=Gamma2_2&k=&j=2&table=1", ["111111", "3111"])
        self.check("?col=Gamma0_3&k=&j=&table=1", ["Total", "74"])
        self.check("?col=Gamma0_3&k=&j=2&table=1", "should not be specified")
        self.check("?col=Gamma0_3_psi_3&k=&j&table=1", ["Total", "68"])
        self.check("?col=Gamma0_3_psi_3&k=&j=2&table=1", "should not be specified")
        self.check("?col=Gamma0_4&k=&j=&table=1", ["Total", "240"])
        self.check("?col=Gamma0_4&k=&j=2&table=1", "should not be specified"])
        self.check("?col=Gamma0_4_psi_4&k=&j&table=1", ["Total", "495"])
        self.check("?col=Gamma0_4_psi_4&k=&j=2&table=1", "should not be specified")
        self.check("?col=Gamma0_4_half&k=&j&table=1", ["Cusp", "129"])
        self.check("?col=Gamma0_4_half&k=&j=2&table=1", "should not be specified")
        self.check("?col=Sp6Z&k=&j&table=1", ["Miyawaki lifts", "conjectured"])
        self.check("?col=Sp6Z&k=&j=2&table=1", "should not be specified")
        self.check("?col=Sp6Z&k=&j&table=1", ["Ikeda lifts", "Miyawaki lifts"])
        self.check("?col=Sp6Z&k=&j=2&table=1", "should not be specified")

    def test_sample_pages(self):
        """
        Test every sample form home page (should take 10-20s on atkin)
        """
        errors = []
        samples = getDBConnection().siegel_modular_forms.experimental_samples
        data = samples.find({'collection':{'$exists':True},'name':{'$exists':True}},{'_id':False,'collection':True,'name':True})
        n = 0
        print ""
        for s in data:
            full_label = s['collection'][0] + "." + s['name']
            print "Checking home page for SMF sample " + full_label
            try:
                n = n+1
                self.check(full_label,[full_label,'Hecke eigenform'])
            except:
                print "Error on page " + url
                errors.append(url)
        if not errors:
            print "Tested %s pages with no errors" % n
        else:
            print "Tested %d pages with %d errors occuring on the following pages:" %(n,len(errors))
            for url in errors:
                print url
