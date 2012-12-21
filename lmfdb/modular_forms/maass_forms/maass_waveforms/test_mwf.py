r"""
Tests for Maass waveforms.

"""
from base import LmfdbTest

class MwfTest(LmfdbTest):
    def test_sl2z(self):
        table=self.tc.get("/ModularForm/GL2/Q/Maass/?weight=0&level=&browse=1")
        assert '9.53369526135' in table.data," The table of eigenvalues of the Laplacian is incomplete!"

    def test_gamma_0_3maass(self):
        table=self.tc.get("/ModularForm/GL2/Q/Maass/4cb8502658bca9141c00002a?db=FS")
        assert 'Fourier' in table.data," The table of eigenvalues of the Laplacian is incomplete!"

