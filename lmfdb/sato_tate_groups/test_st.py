# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest, getDBConnection
import math
import unittest2

class SatoTateGroupTest(LmfdbTest):

    # All tests should pass
    #
    def test_main(self):
        L = self.tc.get('/SatoTateGroup/')
        assert 'Browse' in L.data and 'U(1)_2' in L.data  and 'SU(2)' in L.data and 'Maximum number' in L.data
        
    def test_by_label(self):
        L = self.tc.get('/SatoTateGroup/1.4.10.1.1a')
        assert 'USp(4)' in L.data
        L = self.tc.get('/SatoTateGroup/?label=USp%284%29')
        assert 'USp(4)' in L.data
        
    def test_direct_access(self):
        L = self.tc.get('/SatoTateGroup/1.4.G_{3,3}')
        assert '1.4.6.1.1a' in L.data
        L = self.tc.get('/SatoTateGroup/1.4.6.1.1a')
        assert 'G_{3,3}' in L.data
        
    def test_browse(self):
        L = self.tc.get('/SatoTateGroup/?identity_component=U(1)')
        assert 'all 2 matches' in L.data
        L = self.tc.get('/SatoTateGroup/?weight=1&degree=4&&components=48')
        assert 'unique match' in L.data

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
        print ""
        L = self.tc.get('/SatoTateGroup/?weight=1&degree=2')
        assert '3 matches' in L.data
        L = self.tc.get('/SatoTateGroup/U(1)')
        assert '1.2.1.1.1a' in L.data
        L = self.tc.get('/SatoTateGroup/N(U(1))')
        assert '1.2.1.2.1a' in L.data
        L = self.tc.get('/SatoTateGroup/SU(2)')
        assert '1.2.3.1.1a' in L.data
        stdb = getDBConnection().sato_tate_groups.st_groups
        data = stdb.find({'weight':int(1),'degree':int(2)})
        assert data.count() == 3
        for r in data:
            print 'Checking Sato-Tate group ' + r['label']
            L = self.tc.get('/SatoTateGroup/?label='+r['label'])
            assert r['label'] in L.data and 'Moment Statistics' in L.data
        L = self.tc.get('/SatoTateGroup/?weight=1&degree=4')
        assert 'of 52' in L.data
        data = stdb.find({'weight':int(1),'degree':int(4)})
        assert data.count() == 52
        for r in data:
            print 'Checking Sato-Tate group ' + r['label']
            L = self.tc.get('/SatoTateGroup/?label='+r['label'])
            assert r['label'] in L.data and 'Moment Statistics' in L.data
        
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

