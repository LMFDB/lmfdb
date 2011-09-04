r"""
Tests for Maass waveforms.

"""
from base import LmfdbTest

class MwfTest(LmfdbTest):
    def test_sl2z(self):
        table=self.tc.get("/ModularForm/GL2/Q/Maass/?weight=0&level=&browse=1")
        assert '9.53369526135' in table," The table of eigenvalues of the Laplacian is incomplete!"
