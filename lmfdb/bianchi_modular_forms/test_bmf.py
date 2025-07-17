
from lmfdb.tests import LmfdbTest
from sage.all import Integer

base_url = '/ModularForm/GL2/ImaginaryQuadratic/'

class BMFTest(LmfdbTest):
    # All tests should pass
    #
    def test_home_page(self):
        r"""
        Check that the home page loads
        """
        L = self.tc.get(base_url)
        assert 'Bianchi modular forms' in L.get_data(as_text=True)

    # Link to random newform
    def test_random(self):
        r"""
        Check that the link to a random curve works.
        """
        homepage = self.tc.get(base_url).get_data(as_text=True)
        self.check(homepage, base_url+"random", 'Hecke eigenvalues')

    # Browsing links
    def test_browse(self):
        r"""
        Check that the browsing links work.
        """
        homepage = self.tc.get(base_url).get_data(as_text=True)
        t = "?field_label=2.0.3.1"
        assert t in homepage
        self.check_args(base_url+t, "/ModularForm/GL2/ImaginaryQuadratic/2.0.3.1/124.1/a/")
        t = "?field_label=2.0.4.1"
        assert t in homepage
        self.check_args(base_url+t, "/ModularForm/GL2/ImaginaryQuadratic/2.0.4.1/164.1")
        t = "gl2dims/2.0.4.1"
        assert t in homepage
        self.check_args(base_url+t,'show both the dimension $d$ of the space of cusp forms of weight')
        t = '2.0.4.1/100.2/a/'
        self.check_args(base_url+t,'Base change')

    # Jump to specific newform
    def test_jump(self):
        r"""
        Check that jumping to a specific newform by label works.
        """
        self.check_args(base_url+"?jump=2.0.4.1-65.2-a", 'Analytic rank')

    # Various search combinations
    def test_search(self):
        r"""
        Check that various search combinations work.
        """
        self.check_args(base_url+"?field_label=2.0.7.1&level_norm=322&count=10", 'Results (4 matches)')
        self.check_args(base_url+"?start=0&include_base_change=off&include_cm=only&count=100", 'ModularForm/GL2/ImaginaryQuadratic/2.0.1007.1/9.1/a/')

    # tests for newspace pages
    def test_newspace(self):
        r"""
        Check newspace pages
        """
        self.check_args(base_url+'2.0.3.1/77283.1', 'contains the following\nnewforms')
        self.check_args(base_url+'2.0.11.1/207.6', 'Dimension of new cuspidal subspace:')
        # I don't know why the following fails, as the text was copied from the page source:
        #self.check_args(base_url+'2.0.11.1/207.6', r'\((2 a + 13) = (\left(a - 1\right))^{2} \cdot (\left(a - 5\right)) \)')

    #
    # tests for individual newform pages
    def test_newform(self):
        r"""
        Check newform pages
        """
        base_url = '/ModularForm/GL2/ImaginaryQuadratic/'
        self.check_args(base_url+'2.0.11.1/207.6/b', 'Base change')
        self.check_args(base_url+'2.0.11.1/207.6/b', '2.0.11.1-207.6-b')
        self.check_args(base_url+'2.0.3.1/44332.1/a/', 'Elliptic curve 2.0.3.1-44332.1-a')
        self.check_args(base_url+'2.0.3.1/44332.1/a/', '44332.1')
        self.check_args(base_url+'2.0.11.1/256.1/a/', 'no, but is a twist of the base change of a form over')
        self.check_args(base_url+'2.0.11.1/256.1/a/', 'Elliptic curve 2.0.11.1-256.1-a')
        # A dimension 2 example
        # self.check_args(base_url+'2.0.4.1/377.1/a2', r'The Hecke eigenfield is \(\Q(z)\) where  $z$ is a root of the defining')

    def test_friends(self):
        for url, texts, notitself in [
                ('/ModularForm/GL2/ImaginaryQuadratic/2.0.7.1/44.3/a/',
                    ('Bianchi modular form 2.0.7.1-44.4-a',
                        'Elliptic curve 2.0.7.1-44.3-a',
                        'Elliptic curve 2.0.7.1-44.4-a'),
                    'Bianchi modular form 2.0.7.1-44.3-a'),
                ('/ModularForm/GL2/ImaginaryQuadratic/2.0.7.1/44.4/a/',
                    ('Bianchi modular form 2.0.7.1-44.3-a',
                        'Elliptic curve 2.0.7.1-44.3-a',
                        'Elliptic curve 2.0.7.1-44.4-a'),
                    'Bianchi modular form 2.0.7.1-44.4-a'),
                ('/ModularForm/GL2/ImaginaryQuadratic/2.0.8.1/32.1/a/',
                    ('Hilbert modular form 2.2.8.1-32.1-a',
                        'Elliptic curve 2.0.8.1-32.1-a',
                        'Elliptic curve 2.2.8.1-32.1-a'),
                    'Bianchi modular form 2.0.8.1-32.1-a')
                    ]:
            L = self.tc.get(url)
            for t in texts:
                assert t in L.get_data(as_text=True)
            assert 'L-function' in L.get_data(as_text=True)

            # this test isn't very specific
            # but the goal is to test that itself doesn't show in the friends list
            assert notitself not in L.get_data(as_text=True)

    def test_download_sage(self):

        # A dimension 1 example
        L1_sage_code = self.tc.get('/ModularForm/GL2/ImaginaryQuadratic/2.0.3.1/18333.3/a/download/sage').get_data(as_text=True)
        L1_variables = self.check_sage_compiles_and_extract_variables(L1_sage_code)
        assert L1_variables['NN'].norm() == Integer(18333)
        a = L1_variables['a']
        ZF = L1_variables['ZF']
        assert L1_variables['NN'] == ZF.ideal((6111, 3*a + 5052))
        for gens in [(27*a-22,),(-29*a+15,),(-29*a+14,),(29*a-11,),(-29*a+18,),(-29*a+9,)]:
            assert ZF.ideal(gens) in L1_variables['hecke_eigenvalues']
        hecke_av_start = [0, -1, 2, -1, 1, -3, 4, 0, -2, -8, 7, -9, -8, -4, -9, 8, 10, -11]
        assert L1_variables['hecke_eigenvalues_array'][:len(hecke_av_start)] == hecke_av_start

        # A dimension 2 example (no longer available)
        # L2_sage_code = self.tc.get('/ModularForm/GL2/ImaginaryQuadratic/2.0.4.1/377.1/a2/download/sage').get_data(as_text=True)
        # L2_variables = self.check_sage_compiles_and_extract_variables(L2_sage_code)

        # i = L2_variables['F'].gen()
        # z = L2_variables['z']
        # ZF = L2_variables['ZF']

        # assert L2_variables['NN'] == ZF.ideal((16*i - 11)), "level doesn't match"  # the level displayed on BMF homepage

        # for gens in [(2*i+3,),(i+4,),(i-4,),(-2*i+5,),(2*i+5,),(i+6,)]:
        #     assert ZF.ideal(gens) in L2_variables['hecke_eigenvalues']
        # hecke_av_start = [-z, 2*z, -1, 2*z+2, "not known", 2*z-1, 4, 2*z+3, "not known", 2*z+1, -2*z-5, -4*z+5, -4*z+5, 2*z+1, 2*z]
        # assert L2_variables['hecke_eigenvalues_array'][:len(hecke_av_start)] == hecke_av_start

    def test_download_magma(self):
        # A dimension 1 example
        L = self.tc.get('/ModularForm/GL2/ImaginaryQuadratic/2.0.7.1/88.5/a/download/magma').get_data(as_text=True)
        assert 'NN := ideal<ZF | {44, 2*a + 30}>;' in L
        assert '[263,a+123],' in L

        page = self.tc.get('ModularForm/GL2/ImaginaryQuadratic/159.0.7.1/30.5/a/download/magma').get_data(as_text=True)
        assert 'Bianchi newform not found' in page

        # We run magma when it is installed
        for label, expected in [
                ['2.0.4.1/100.2/a',
                 'ALEigenvalues[ideal<ZF | {i + 1}>] := -1;'],
                ['2.0.11.1/933.1/a',
                 'ideal<ZF | {a + 30, 933}>;']
        ]:
            page = self.tc.get('/ModularForm/GL2/ImaginaryQuadratic/{}/download/magma'.format(label)).get_data(as_text=True)
            assert expected in page
            assert 'make_newform' in page

            magma_code = page + '\n'
            magma_code += 'f, iso := Explode(make_newform());\n'
            magma_code += 'for P in primes[1..15] do;\n if Valuation(NN,P) eq 0 then;\n  assert iso(heckeEigenvalues[P]) eq HeckeEigenvalue(f,P);\n end if;\nend for;\n'
            magma_code += 'f;\n'
            self.assert_if_magma('success', magma_code, mode='in')

    def test_underlying_data(self):
        # We just check for the existence of the link, since it use the api
        page = self.tc.get("/ModularForm/GL2/ImaginaryQuadratic/2.0.7.1/88.5/a", follow_redirects=True).get_data(as_text=True)
        assert "Underlying data" in page and "data/2.0.7.1-88.5-a" in page
