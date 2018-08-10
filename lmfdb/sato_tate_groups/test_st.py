# -*- coding: utf-8 -*-
from lmfdb.base import LmfdbTest
from lmfdb.db_backend import db

class SatoTateGroupTest(LmfdbTest):

    # All tests should pass
    #
    def test_main(self):
        L = self.tc.get('/SatoTateGroup/')
        assert 'Browse' in L.data and 'SO(1)' in L.data and 'U(1)_2' in L.data  and 'SU(2)' in L.data and 'Rational' in L.data
        
    def test_by_label(self):
        L = self.tc.get('/SatoTateGroup/?label=1.4.10.1.1a', follow_redirects=True)
        assert 'USp(4)' in L.data and '223412' in L.data
        L = self.tc.get('/SatoTateGroup/?label=1.4.USp(4)', follow_redirects=True)
        assert '1.4.10.1.1a' in L.data and '223412' in L.data
        L = self.tc.get('/SatoTateGroup/?label=1.2.N(U(1))', follow_redirects=True)
        assert '1.2.1.2.1a' in L.data and '462' in L.data
        L = self.tc.get('/SatoTateGroup/?label=0.1.37', follow_redirects=True)
        assert '0.1.37' in L.data and 'mu(185)' in L.data
        L = self.tc.get('/SatoTateGroup/?label=0.1.mu(37)', follow_redirects=True)
        assert '0.1.37' in L.data and 'mu(185)' in L.data
        L = self.tc.get('/SatoTateGroup/?label=0.1.mu(100000000000000000001)', follow_redirects=True)
        assert 'too large' in L.data

    def test_direct_access(self):
        L = self.tc.get('/SatoTateGroup/1.4.G_{3,3}', follow_redirects=True)
        assert '1.4.6.1.1a' in L.data
        L = self.tc.get('/SatoTateGroup/1.4.6.1.1a')
        assert 'G_{3,3}' in L.data
        L = self.tc.get('/SatoTateGroup/0.1.mu(37)', follow_redirects=True)
        assert '0.1.37' in L.data
        L = self.tc.get('/SatoTateGroup/0.1.37')
        assert 'mu(37)' in L.data

    def test_browse(self):
        L = self.tc.get('/SatoTateGroup/?identity_component=U(1)')
        assert 'both matches' in L.data
        L = self.tc.get('/SatoTateGroup/?weight=1&degree=4&&components=48')
        assert 'unique match' in L.data
        L = self.tc.get('SatoTateGroup/?components=48')
        assert 'both matches' in L.data
        L = self.tc.get('SatoTateGroup/?degree=1&start=1000&count=25')
        assert 'matches 1001-1025' in L.data
        L = self.tc.get('SatoTateGroup/?degree=1&rational_only=yes')
        assert 'both matches' in L.data

    def test_moments(self):
        L = self.tc.get('/SatoTateGroup/1.4.6.1.1a')
        assert '187348' in L.data

    def test_subgroups(self):
        L = self.tc.get('/SatoTateGroup/1.4.1.6.1a')
        assert 'C_2' in L.data and 'C_3' in L.data and 'D_{6,1}' in L.data and 'D_6' in L.data and 'J(D_3)' in L.data and 'O' in L.data

    def test_event_probabilities(self):
        L = self.tc.get('/SatoTateGroup/1.4.1.48.48a')
        assert '33' in L.data

    def test_completeness(self):
        import sys
        L = self.tc.get('/SatoTateGroup/?weight=1&degree=2')
        assert '3 matches' in L.data
        data = list(db.gps_sato_tate.search({'weight':int(1),'degree':int(2)}, projection='label'))
        assert len(data) == 3
        print ""
        for label in data:
            sys.stdout.write("{}...".format(label))
            sys.stdout.flush()
            L = self.tc.get('/SatoTateGroup/' + label)
            assert label in L.data and 'Moment Statistics' in L.data
        L = self.tc.get('/SatoTateGroup/?weight=1&degree=4')
        assert 'of 52' in L.data
        data = list(db.gps_sato_tate.search({'weight':int(1),'degree':int(4)}, projection='label'))
        assert len(data) == 52

        for label in data:
            sys.stdout.write("{}...".format(label))
            sys.stdout.flush()
            L = self.tc.get('/SatoTateGroup/' + label)
            assert label in L.data and 'Moment Statistics' in L.data
        L = self.tc.get('/SatoTateGroup/?components=999999999')
        assert 'unique match'  in L.data and 'mu(999999999)' in L.data

    def test_trace_zero_density(self):
        L = self.tc.get('/SatoTateGroup/?trace_zero_density=1')
        assert '0 matches'
        L = self.tc.get('/SatoTateGroup/?trace_zero_density=1/4')
        assert '1.4.3.4.1a' in L.data
        L = self.tc.get('/SatoTateGroup/?trace_zero_density=19/24')
        assert '1.4.1.24.14a' in L.data
        
    def test_favourites(self):
        for label in [ '1.2.1.2.1a','1.2.3.1.1a', '1.4.1.12.4d', '1.4.3.6.2a', '1.4.6.1.1a', '1.4.10.1.1a' ]:
            L = self.tc.get('/SatoTateGroup/'+label)
            assert "Moment Statistics" in L.data

