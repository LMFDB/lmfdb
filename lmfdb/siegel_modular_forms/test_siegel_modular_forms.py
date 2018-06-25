# -*- coding: utf-8 -*-
from lmfdb.base import LmfdbTest
from lmfdb.db_backend import db

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
        Test 3 random sample pages
        """
        self.check("random", "Hecke eigenform")
        self.check("random", "Hecke eigenform")
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
        self.check("Gamma0_3_psi_3/",  'Gamma_0(3)')
        self.check("Gamma0_4/",  'Gamma_0(4)')
        self.check("Gamma0_4_psi_4/", 'Gamma_0(4)')
        self.check("Gamma0_4_half/",  'k-1/2')
        self.check("Sp4Z_j/10/10/", 'M_{10,10}')
        self.check("Sp4Z/10/", 'M_{10,0}')
        self.check("Sp4Z_2/10/", 'M_{10,2}')
        
    def test_dimension_tables(self):
        """
        Test dimension table pages
        """
        self.check("?family=Sp4Z_j&k=&j=&table=1", ["Cusp", "Non cusp"])
        self.check("?family=Sp4Z_j&k=&j=2&table=1", ["Cusp", "Non cusp"])
        self.check("?family=Gamma0_2&k=&j=&table=1", ["Cusp", "Non cusp"])
        self.check("?family=Gamma0_2&k=&j=2&table=1", ["Cusp", "Non cusp"])
        self.check("?family=Gamma1_2&k=&j=&table=1", ["111", "21"])
        self.check("?family=Gamma1_2&k=&j=2&table=1", ["111", "21"])
        self.check("?family=Gamma_2&k=&j=&table=1", ["111111", "3111"])
        self.check("?family=Gamma_2&k=&j=2&table=1", ["111111", "3111"])
        self.check("?family=Gamma0_3&k=&j=&table=1", ["Total", "74"])
        self.check("?family=Gamma0_3&k=&j=2&table=1", "should not be specified")
        self.check("?family=Gamma0_3_psi_3&k=&j&table=1", ["Total", "68"])
        self.check("?family=Gamma0_3_psi_3&k=&j=2&table=1", "should not be specified")
        self.check("?family=Gamma0_4&k=&j=&table=1", ["Total", "240"])
        self.check("?family=Gamma0_4&k=&j=2&table=1", "should not be specified")
        self.check("?family=Gamma0_4_psi_4&k=&j&table=1", ["Total", "495"])
        self.check("?family=Gamma0_4_psi_4&k=&j=2&table=1", "should not be specified")
        self.check("?family=Gamma0_4_half&k=&j&table=1", ["Cusp", "129"])
        self.check("?family=Gamma0_4_half&k=&j=2&table=1", "should not be specified")
        self.check("?family=Sp6Z&k=&j&table=1", ["Miyawaki lifts", "conjectured"])
        self.check("?family=Sp6Z&k=&j=2&table=1", "should not be specified")
        self.check("?family=Sp8Z&k=&j&table=1", ["Ikeda lifts", "Miyawaki lifts"])
        self.check("?family=Sp8Z&k=&j=2&table=1", "should not be specified")

    def test_sample_page_Q(self):
        """
        Test eigenvalue, Fourier coefficient, and modulus selction on a sample page with coefficent field Q
        """
        self.check("Sp4Z.24_E",["35184384671745", "19664276334286895123835070363311360", "..."])
        self.check("Sp4Z.24_E?ev_index=19&fc_det=0&modulus=&update=1", ["3498743002442937227729601361394364486949008189359690164120", "3398215376663749994606261280", "(0, 0, 25)"])
        self.check("Sp4Z.24_E/?ev_index=&fc_det=&modulus=1000000007&update=1", ["384425457", "(1, 1, 1)", "384425457"])

    def test_sample_page_nf(self):
        """
        Test eigenvalue, Fourier coefficient, and modulus selction on a sample page with quadratic coefficent field
        """
        self.check("Sp4Z.18_Maass/",["Maass spezialschaar", "x^{2} - x - 589050", "$-144 a + 135840$", "$10 a - 8340$"])
        self.check("Sp4Z.18_Maass/?ev_index=&fc_det=&modulus=17%2Ca%2B1&update=1", "is the unit ideal, please specify")
        self.check("Sp4Z.18_Maass/?ev_index=&fc_det=&modulus=65537&update=1", ["$5$", "$-1378 a - 22820$", "(2, 2, 2)", "$32016 a + 5274$"])
        
    def test_huge_sample(self):
        """
        Test sample page with defining equation and explicit formula too large to display
        """
        self.check("Sp4Z.56_Ups", ["interesting cusp form", "6085 bytes", "7912968 bytes"])

    def test_all_sample_pages(self):
        """
        Verify that every sample form home page loads OK (should take under 10s on atkin)
        """
        errors = []
        data = list(db.smf_samples.search({'collection':{'$exists':True},'name':{'$exists':True}},['collection','name']))
        assert len(data) >= 129
        n = 0
        print ""
        import sys
        for s in data:
            full_label = s['collection'][0] + "." + s['name']
            sys.stdout.write("Checking {}...".format(full_label))
            sys.stdout.flush()
            try:
                n = n+1
                self.check(full_label,[full_label,'Hecke eigenform'])
            except:
                print "\nError on page " + full_label
                errors.append(full_label)
        if not errors:
            print "\nTested %s SMF pages with no errors" % n
        else:
            print "\nTested %d pages with %d errors occuring on the following pages:" %(n,len(errors))
            for label in errors:
                print label
