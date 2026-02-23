
from lmfdb.tests import LmfdbTest

class HomePageTest(LmfdbTest):
    # The Lattice page
    def test_lattice(self):
        homepage = self.tc.get("/Lattice/").get_data(as_text=True)
        assert 'random' in homepage
        assert 'Gram' in homepage

    # The Genus page
    def test_genus(self):
        homepage = self.tc.get("/Lattice/Genus").get_data(as_text=True)
        assert 'random' in homepage
        assert 'Gram' in homepage

    def test_lattice_rank(self):
        L = self.tc.get("/Lattice/9.9.8.001.76.1").get_data(as_text=True)
        assert '115712' in L #coeff in theta series
        assert '1.58740105196819947475170563927' in L #Hermite number
        assert '11612160' in L #group order

    def test_genus_rank(self):
        L = self.tc.get("/Lattice/Genus/9.9.8.001.76").get_data(as_text=True)
        assert 'Even' in L # Parity
        assert '11612160' in L # group order of only lattice in genus

    def test_lattice_classnumber(self):
        L = self.tc.get("/Lattice/?class_number=1").get_data(as_text=True)
        assert '1.1.1.3.1' in L #label (class number 1)

    def test_lattice_classnumber_large(self):
        L = self.tc.get("/Lattice/6.6.671.121.1").get_data(as_text=True)
        assert '490' in L #test display genus representatives

    #def test_lattice_classnumber_large_download(self):
    #    L = self.tc.get("/Lattice/3.1942.3884.56.13/download/sage/genus_reps").get_data(as_text=True)
    #    assert 'Matrix([[2, 0, 0], [0, 14, -3], [0, -3, 70]]),' in L #test download genus representatives

    def test_lattice_search(self):
        L = self.tc.get("/Lattice/?rank=&det=&level=&gram=&minimum=&class_number=1&aut=&count=50").get_data(as_text=True)
        assert '56' in L # lattice search

    def test_genus_search(self):
        L = self.tc.get("/Lattice/Genus?rank=&det=&level=&gram=&class_number=1&count=50").get_data(as_text=True)
        assert '50' in L # genus search

    def test_lattice_search_next(self):
        L = self.tc.get("/Lattice/?start=50&rank=&det=&level=&gram=&minimum=&class_number=&aut=2&count=50").get_data(as_text=True)
        assert '146' in L #search on the next page

    def test_lattice_searchrank(self):
        L = self.tc.get("/Lattice/?rank=3").get_data(as_text=True)
        assert '3.1.1000.3.3.3b.1' in L # rank search

    def test_lattice_searchlevel(self):
        L = self.tc.get("/Lattice/?start=&rank=&det=&level=90&gram=&minimum=&class_number=&aut=").get_data(as_text=True)
        assert '1.1.45.01.3b.1' in L #level search

    def test_lattice_searchminvectlength(self):
        L = self.tc.get("/Lattice/?rank=&det=&level=&gram=&minimum=3&class_number=&aut=").get_data(as_text=True)
        assert '3.3.45.01.1b7.3' in L #search minimum vector length

    def test_lattice_searchGM(self):
        # auto-detect: 3 entries is triangular → upper tri → [[2,0],[0,5]]
        L = self.tc.get("/Lattice/?gram=[2%2C0%2C5]&gram_format=").get_data(as_text=True)
        assert '2.2.10.7b.1' in L

    def test_lattice_searchGM_upper(self):
        L = self.tc.get("/Lattice/?gram=[2%2C0%2C5]&gram_format=upper").get_data(as_text=True)
        assert '2.2.10.7b.1' in L

    def test_lattice_searchGM_full(self):
        L = self.tc.get("/Lattice/?gram=[2%2C0%2C0%2C5]&gram_format=full").get_data(as_text=True)
        assert '2.2.10.7b.1' in L

    def test_lattice_searchGM_lower(self):
        L = self.tc.get("/Lattice/?gram=[2%2C0%2C5]&gram_format=lower").get_data(as_text=True)
        assert '2.2.10.7b.1' in L

    def test_lattice_searchGM_diagonal(self):
        L = self.tc.get("/Lattice/?gram=[1%2C1%2C1]&gram_format=diagonal").get_data(as_text=True)
        assert '3.3.1' in L

    #def test_latticeZ2(self):
    #    L = self.tc.get("/Lattice/2.1.2.1.1").get_data(as_text=True)
    #    assert r'0.785398163397448309615660845820\dots' in L #Z2 lattice

    def test_latticeZ3(self):
        L = self.tc.get("/Lattice/3.3.1.7.1").get_data(as_text=True)
        assert r'0.523598775598298873077107230547' in L #Z3 lattice

    #def test_lattice_thetadisplay(self):
    #    L = self.tc.get("/Lattice/theta_display/7.576.18.1.1/40").get_data(as_text=True)
    #    assert '41' in L # theta display
    #    assert '1848' in L # theta display
    #    assert '11466' in L # theta display

    def test_lattice_random(self):
        L = self.tc.get("/Lattice/random").get_data(as_text=True)
        assert 'redirected automatically' in L # random lattice
        L = self.tc.get("/Lattice/random", follow_redirects=True)
        assert 'Normalized minimal vectors' in L.get_data(as_text=True) # check redirection

    def test_genus_random(self):
        L = self.tc.get("/Lattice/Genus/random").get_data(as_text=True)
        assert 'redirected automatically' in L # random genus page
        L = self.tc.get("/Lattice/Genus/random", follow_redirects=True)
        assert 'Genus Invariants' in L.get_data(as_text=True) # check redirection

    def test_downloadstring(self):
        L = self.tc.get("/Lattice/5.1.648.3.4.46.1").get_data(as_text=True)
        assert 'matrix' in L

    def test_downloadstring2(self):
        L = self.tc.get("/Lattice/3.3.156.2.3c5.1").get_data(as_text=True)
        assert 'vector' in L
        assert 'Underlying data' in L and 'data/3.3.156.2.3c5.1' in L

    def test_downloadstring_search(self):
        L = self.tc.get("/Lattice/?class_number=8").get_data(as_text=True)
        assert 'displayed columns' in L

    #def test_download_shortest(self):
    #    L = self.tc.get("/Lattice/13.14.28.8.1/download/magma/shortest_vectors").get_data(as_text=True)
    #    assert 'data := ' in L

    #def test_download_genus(self):
    #    L = self.tc.get("/Lattice/4.5.5.1.1/download/gp/genus_reps").get_data(as_text=True)
    #    assert ']~)' in L

    #def test_favorite(self):
    #    for elt in ['A2', 'Z2', 'D3', 'D3*', '3.1942.3884.56.1', 'A5',
    #                'E8', 'A14', 'Leech']:
    #        L = self.tc.get(
    #                "/Lattice/?label={}".format(elt),
    #                follow_redirects=True)
    #        assert elt in L.get_data(as_text=True)
    #        L = self.tc.get(
    #                "/Lattice/{}".format(elt),
    #                follow_redirects=True)
    #        assert elt in L.get_data(as_text=True)
