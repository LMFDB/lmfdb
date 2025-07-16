
from lmfdb.tests import LmfdbTest

class HMFTest(LmfdbTest):
    def test_home(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/')
        assert 'Hilbert' in L.get_data(as_text=True)
        assert 'modular' in L.get_data(as_text=True)
        assert 'Browse' in L.get_data(as_text=True)
        assert 'Search' in L.get_data(as_text=True)
        assert 'Find' in L.get_data(as_text=True)
        assert r'\sqrt{2}' in L.get_data(as_text=True) #552

    def test_random(self): #993
        L = self.tc.get('/ModularForm/GL2/TotallyReal/random')
        assert 'edirect' in L.get_data(as_text=True)

    def test_EC(self): #778
        L = self.tc.get('ModularForm/GL2/TotallyReal/5.5.126032.1/holomorphic/5.5.126032.1-82.1-b')
        assert 'EllipticCurve/5.5.126032.1/82.1/b/' in L.get_data(as_text=True)

        L = self.tc.get('/ModularForm/GL2/TotallyReal/2.2.89.1/holomorphic/2.2.89.1-2.1-a')
        assert 'Elliptic curve' in L.get_data(as_text=True)
        assert 'EllipticCurve/2.2.89.1/2.1/a' in L.get_data(as_text=True)

    def test_typo(self): #771
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?field_label=2.2.5.1')
        assert 'Search again' in L.get_data(as_text=True)

    def test_large(self): #616
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?field_label=4.4.2000.1&count=1200')
        assert '719.2-c' in L.get_data(as_text=True)

    def test_range_search(self): #547
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?disc=1..100&count=100')
        assert '209.1-b' in L.get_data(as_text=True)
        assert 'Next' in L.get_data(as_text=True) #435

    def test_bad_input_search(self): #547
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?field_label=hello&count=100')
        assert 'not a valid input' in L.get_data(as_text=True)

    def test_search(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?start=0&deg=2..5&disc=60-200&level_norm=40-90&dimension=3..5&count=100')
        assert '70.1-o' in L.get_data(as_text=True)

    def test_search_CM(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?start=0&field_label=&deg=5&disc=&weight=2&level_norm=&dimension=&cm=only&bc=include&count=100')
        assert '121.1-b' in L.get_data(as_text=True)

    def test_search_base_change(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?start=0&field_label=&deg=5&disc=&cm=include&bc=exclude&count=100')
        assert '/ModularForm/GL2/TotallyReal/5.5.14641.1/holomorphic/5.5.14641.1-67.5-a' in L.get_data(as_text=True)

    def test_hmf_page(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/2.2.73.1/holomorphic/2.2.73.1-48.4-b')
        s = L.get_data(as_text=True).replace(" ", "")
        assert 'no' in s
        assert '-6' in s
        assert '2w+10' in s
        assert r'\Q' in s
        assert '[2,2]' in s

    def test_hmf_page_higherdim(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/2.2.60.1/holomorphic/2.2.60.1-44.1-c')
        s = L.get_data(as_text=True).replace(" ", "")
        assert '-2w-4' in s
        assert '2e' in s
        assert 'definingpolynomial' in s

    def test_by_field(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?field_label=4.4.725.1')
        assert 'w - 4' in L.get_data(as_text=True)

    def test_download_sage(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/4.4.725.1/holomorphic/4.4.725.1-31.1-a/download/sage')
        assert 'NN = ZF.ideal([31, 31, w^3 - 4*w + 1])' in L.get_data(as_text=True)
        assert '[89, 89, 3*w^3 - 2*w^2 - 7*w],\\' in L.get_data(as_text=True)
        assert 'hecke_eigenvalues_array = [4, -4,' in L.get_data(as_text=True)

    def test_Lfun_link(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a')
        assert 'L/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a' in L.get_data(as_text=True)

    def test_browse(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/browse/')
        assert 'by field degree' in L.get_data(as_text=True)
        assert 'database contains' in L.get_data(as_text=True)
        assert 'data is complete up to' in L.get_data(as_text=True)

    def test_browse_by_degree(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/browse/2/')
        assert 'Number of newforms' in L.get_data(as_text=True)

    def test_missing_AL(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/3.3.49.1/holomorphic/3.3.49.1-512.1-a')
        assert 'The Atkin-Lehner eigenvalues for this form are not in the database' in L.get_data(as_text=True)

    def test_level_one_AL(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/2.2.173.1/holomorphic/2.2.173.1-1.1-a')
        assert 'This form has no Atkin-Lehner eigenvalues' in L.get_data(as_text=True)

    def test_friends(self):
        for url, texts, notitself in [
                ('/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a',
                    ('Hilbert modular form 2.2.5.1-31.2-a',
                        'Elliptic curve 2.2.5.1-31.1-a',
                        'Elliptic curve 2.2.5.1-31.2-a'),
                    'Hilbert modular form 2.2.5.1-31.1-a'),
                ('/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.2-a',
                    ('Hilbert modular form 2.2.5.1-31.1-a',
                        'Elliptic curve 2.2.5.1-31.1-a',
                        'Elliptic curve 2.2.5.1-31.2-a'),
                    'Hilbert modular form 2.2.5.1-31.2-a'),
                ('/ModularForm/GL2/TotallyReal/2.2.497.1/holomorphic/2.2.497.1-1.1-a',
                    ('Elliptic curve 2.0.7.1-5041.1-CMa',
                        'Elliptic curve 2.0.7.1-5041.3-CMa',
                        'Elliptic curve 2.2.497.1-1.1-a',
                        'Modular form 497.2.b.a'),
                    'Hilbert modular form 2.2.497.1-1.1-a'),
                ('/ModularForm/GL2/TotallyReal/2.2.8.1/holomorphic/2.2.8.1-32.1-a',
                    ('Bianchi modular form 2.0.8.1-32.1-a',
                        'Elliptic curve 2.0.8.1-32.1-a',
                        'Elliptic curve 2.2.8.1-32.1-a'),
                    'Hilbert modular form 2.2.8.1-32.1-a')
                ]:
            L = self.tc.get(url)
            for t in texts:
                assert t in L.get_data(as_text=True)
            assert 'L-function' in L.get_data(as_text=True)

            # this test isn't very specific
            # but the goal is to test that itself doesn't show in the friends list
            assert notitself not in L.get_data(as_text=True)

    def test_download_magma(self):

        L = self.tc.get('/ModularForm/GL2/TotallyReal/4.4.725.1/holomorphic/4.4.725.1-31.1-a/download/magma').get_data(as_text=True)
        assert 'NN := ideal<ZF | {31, 31, w^3 - 4*w + 1}>;' in L
        assert '[89, 89, 3*w^3 - 2*w^2 - 7*w],' in L
        assert 'heckeEigenvaluesArray := [4, -4,' in L

        page = self.tc.get('ModularForm/GL2/TotallyReal/3.3.837.1/holomorphic/3.3.837.1-48.3-z/download/magma').get_data(as_text=True)
        assert 'No such form' in page

        # We run the following tests when magma is installed
        for field, label, expected in [
                ['2.2.28.1', '2.2.28.1-531.1-m',
                 'heckeEigenvaluesArray := [e, -1, -1, e^7 - 1/2*e^6 - 10*e^5 + 11/2*e^4 + 27*e^3 - 15*e^2 - 15*e + 4'],
                ['3.3.837.1', '3.3.837.1-2.1-b',
                 'heckeEigenvaluesArray := [1, e, e^2 - e - 7, -e^2 + 6, -e + 2, 2*e + 2, -e^2 + 2*e + 8, 2*e^2 - 4*e - 16'],
                ['4.4.725.1', '4.4.725.1-31.1-a',
                 'heckeEigenvaluesArray := [4, -4, -7, -4, 4, 2, -2, -1, -8, 2, 10']
        ]:
            page = self.tc.get('/ModularForm/GL2/TotallyReal/{}/holomorphic/{}/download/magma'.format(field, label)).get_data(as_text=True)
            assert expected in page
            assert 'make_newform' in page

            magma_code = page + '\n'
            magma_code += 'f, iso := Explode(make_newform());\n'
            magma_code += 'assert(&and([iso(heckeEigenvalues[P]) eq HeckeEigenvalue(f,P): P in primes[1..10]]));\n'
            magma_code += 'f;\n'
            self.assert_if_magma('success', magma_code, mode='in')

    def test_underlying_data(self):
        data = self.tc.get('/ModularForm/GL2/TotallyReal/data/2.2.5.1-31.1-a').get_data(as_text=True)
        assert ('hmf_forms' in data and 'level_bad_primes' in data
                and 'hmf_hecke' in data and 'AL_eigenvalues' in data
                and 'hmf_fields' in data and 'ideals' in data)
