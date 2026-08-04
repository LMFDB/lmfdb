from lmfdb.tests import LmfdbTest

class EllCurveTest(LmfdbTest):

    # All tests should pass
    #
    def test_minimal_eqn(self):
        r"""
        Check that the elliptic curve/#field tells about (non)existence of a global minimal model
        """
        L = self.tc.get('/EllipticCurve/2.2.89.1/81.1/a/1')
        assert 'This is a <a title="Global minimal model' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/2.2.229.1/9.3/a/2')
        assert 'This is not a <a title="Global minimal model' in L.get_data(as_text=True)
        assert 'at all primes except' in L.get_data(as_text=True)

    def test_base_field(self):
        r"""
        Check that the elliptic curve/#field tells about its base field
        """
        L = self.tc.get('/EllipticCurve/3.1.23.1/89.1/A/1')
        assert '3.1.23.1' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/2.2.5.1/49.1/a/2')
        assert r'\phi' in L.get_data(as_text=True)

    def test_bad_red(self):
        r"""
        Check that the elliptic curve/#field tells about its bad reduction primes
        """
        L = self.tc.get('/EllipticCurve/2.2.5.1/31.2/a/3')
        assert 'Non-split multiplicative' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/2.2.5.1/64.1/a/1')
        assert 'Additive' in L.get_data(as_text=True)

    def test_weierstrass(self):
        r"""
        Check that the elliptic curve/#field tells about its Weirstrass eqn
        """
        L = self.tc.get('/EllipticCurve/2.0.4.1/225.2/a/2')
        assert '396' in L.get_data(as_text=True)
        assert '2982' in L.get_data(as_text=True)

    def test_conductor(self):
        r"""
        Check that the elliptic curve/#field tells about its conductor
        and discriminant
        """
        L = self.tc.get('/EllipticCurve/2.0.7.1/10000.5/a/1')
        assert '10000' in L.get_data(as_text=True)
        assert '15625000000000000' in L.get_data(as_text=True)
        assert '87890625' in L.get_data(as_text=True)
        assert '25^{9}' in L.get_data(as_text=True)
        assert '12' in L.get_data(as_text=True)

    def test_j(self):
        r"""
        Check that the elliptic curve/#field tells about its j invariant
        """
        L = self.tc.get('/EllipticCurve/2.0.4.1/5525.5/b/9')
        assert '226834389543384' in L.get_data(as_text=True)
        assert '1490902050625' in L.get_data(as_text=True)
        L = self.tc.get('EllipticCurve/2.2.89.1/81.1/a/1') # Test factorisation
        assert '8798344145175011328000' in L.get_data(as_text=True)

    def test_download(self):
        r"""
        Check that the code download links work
        """
        L = self.tc.get('/EllipticCurve/2.0.4.1/5525.5/b/9')
        assert 'Magma commands' in L.get_data(as_text=True)
        assert 'SageMath commands' in L.get_data(as_text=True)
        assert 'PariGP commands' in L.get_data(as_text=True)
        L = self.tc.get('EllipticCurve/2.2.89.1/81.1/a/1/download/magma')
        assert 'Magma code for working with elliptic curve 2.2.89.1-81.1-a1' in L.get_data(as_text=True)
        L = self.tc.get('EllipticCurve/2.2.89.1/81.1/a/1/download/sage')
        assert 'SageMath code for working with elliptic curve 2.2.89.1-81.1-a1' in L.get_data(as_text=True)
        L = self.tc.get('EllipticCurve/2.2.89.1/81.1/a/1/download/gp')
        assert 'Pari/GP code for working with elliptic curve 2.2.89.1-81.1-a1' in L.get_data(as_text=True)

    def test_search_download(self):
        r"""
        Check downloading search results (issue #7004)
        """
        # The base field 3.3.1849.1 is not monogenic, so these curves have
        # Weierstrass coefficients with non-integral rational coordinates
        base = '/EllipticCurve/?download=1&query=%7B%27field_label%27%3A+%273.3.1849.1%27%2C+%27conductor_norm%27%3A+1%7D&Submit='
        for lang in ['sage', 'gp', 'magma', 'text', 'csv']:
            L = self.tc.get(base + lang)
            data = L.get_data(as_text=True)
            assert '[-25097, -6233/2, 3859/2]' in data
            assert 'unable to convert' not in data
        # In Julia, -3/2 is floating point division, so rationals must be downloaded as -3//2
        L = self.tc.get(base + 'oscar')
        data = L.get_data(as_text=True)
        assert '[-25097, -6233//2, 3859//2]' in data
        # For curves whose rank is not known, the rank bounds should be
        # downloaded rather than a LaTeX string such as "0 \le r \le 1"
        base = '/EllipticCurve/?download=1&query=%7B%27field_label%27%3A+%272.0.868.1%27%2C+%27conductor_norm%27%3A+2%7D&Submit='
        for lang in ['sage', 'gp', 'magma', 'text', 'csv', 'oscar']:
            L = self.tc.get(base + lang)
            data = L.get_data(as_text=True)
            # The columns preceding the Sato-Tate group are the two labels, the base
            # field with its defining polynomial, the conductor norm, the rank and the
            # torsion, so [0, 1] can only be the bounds on the rank of this curve
            row = [line for line in data.split('\n') if '2.1-b1' in line][0]
            assert '[0, 1]' in row.split('1.2.A.1.1a')[0]
            assert r'\le r' not in row

    def test_download_field_polys(self):
        r"""
        Check that the base field defining polynomials used when downloading
        search results are loaded in a single query (issue #7004)
        """
        from unittest.mock import patch
        from lmfdb.ecnf.main import ECNFDownloader
        downloader = ECNFDownloader()
        rows = [{'field_label': label, 'ainvs': '0,0,0;0,0,0;0,0,0;0,0,0;0,0,0'}
                for label in ['3.3.1849.1', '2.0.868.1', '3.3.1849.1']]
        with patch.object(self.db.nf_fields, 'search', wraps=self.db.nf_fields.search) as search, \
             patch.object(self.db.nf_fields, 'lookup', wraps=self.db.nf_fields.lookup) as lookup:
            polys = [downloader.postprocess(row, {}, {})['field_coeffs'] for row in rows]
            # All of the defining polynomials are fetched by the first row, in bulk
            assert search.call_count == 1
            assert lookup.call_count == 0
            # and the dictionary they were saved in is reused afterwards
            assert downloader.field_polys is downloader.field_polys
            assert search.call_count == 1
        assert polys[0] is polys[2]
        for row, poly in zip(rows, polys):
            assert poly.degree() == int(row['field_label'].split('.')[0])

    def test_search(self):
        r"""
        Check ecnf search results
        """
        # Conductor 1
        L = self.tc.get('/EllipticCurve/?start=0&count=50&conductor_norm=1&include_isogenous=on&include_base_change=on')
        assert '2115 a - 13286543' in L.get_data(as_text=True)
        # 4*4 torsion
        L = self.tc.get('/EllipticCurve/?start=0&count=50&include_isogenous=on&include_base_change=on&torsion=&torsion_structure=[4%2C4]')
        assert '/EllipticCurve/2.0.4.1/5525.5/b/9' in L.get_data(as_text=True)
        # 13 torsion
        L = self.tc.get('/EllipticCurve/?torsion=13')
        assert '2745' in L.get_data(as_text=True)
        assert '3.3.49.1' in L.get_data(as_text=True)
        #field (see what I did here?)
        L = self.tc.get('/EllipticCurve/?field=Qsqrt-11&include_base_change=on&conductor_norm=&include_isogenous=on&torsion=&torsion_structure=&count=')
        assert '2.0.11.1' in L.get_data(as_text=True)
        assert '1681' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/?jinv=0,1728')
        t = L.get_data(as_text=True)
        assert '729.1-CMb1' in t and '1024.1-a1' in t and '73.1-a1' not in t
        L = self.tc.get('/EllipticCurve/?field=2.0.11.1&jinv=~-52893159101157376/11')
        assert '11.1-a1' not in L.get_data(as_text=True)

    def test_browse(self):
        r"""
        Check that degree browse pages display correctly
        """
        for n, cnt in [(2, 77095), (3, 4416), (4, 4064), (5, 792), (6, 537)]:
            self.check_args(f"/EllipticCurve/browse/{n}", str(cnt))

    def test_isodeg(self):
        r"""
        Test that searching for isogeny degree works
        """
        L = self.tc.get('/EllipticCurve/?start=0&isodeg=2')
        assert '73.1-a1' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/?start=0&torsion=1&isodeg=2')
        assert 'No matches' in L.get_data(as_text=True)

    def test_cm_disc_search(self):
        r"""
        Test that searching for CM field discriminant works
        """
        self.check_args('/EllipticCurve/?cm_disc=-4','1024.1-a1')
        self.not_check_args('/EllipticCurve/?cm_disc=-4','1.0.1-a1')

        # make sure it works with 4-way PCM, CM, PCMnoCM, noCM switch
        self.check_args('/EllipticCurve/?cm_disc=-11&include_cm=PCMnoCM','14641.1-a1')
        self.not_check_args('/EllipticCurve/?cm_disc=-11&include_cm=PCMnoCM','9.1-CMa1')

    def test_related_objects(self):
        for url, text in [('/EllipticCurve/2.0.8.1/324.3/a/1',
                ['Isogeny class 324.3-a',
                 'Twists',
                 'Base change of 36.a4',
                 'Base change of 576.f3',
                 'Bianchi modular form 2.0.8.1-324.3-a',
                 'Hilbert modular form 2.2.24.1-36.1-a',
                 'Elliptic curve 2.2.24.1-36.1-a',
                 'Genus 2 curve 20736.i',
                 'L-function']),
                ('/EllipticCurve/2.0.11.1/256.1/b/1',
                    ['Isogeny class 256.1-b',
                     'Twists',
                     'Bianchi modular form 2.0.11.1-256.1-a',
                     'Bianchi modular form 2.0.11.1-256.1-b',
                     'Hilbert modular form 2.2.44.1-16.1-a',
                     'Hilbert modular form 2.2.44.1-16.1-c',
                     'Elliptic curve 2.0.11.1-256.1-a',
                     'Elliptic curve 2.2.44.1-16.1-a',
                     'Elliptic curve 2.2.44.1-16.1-c',
                     'L-function'])]:
            L = self.tc.get(url).get_data(as_text=True)
            for t in text:
                assert t in L
