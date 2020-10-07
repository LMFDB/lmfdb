r"""
Tests for Maass waveforms.

"""
from lmfdb.tests import LmfdbTest


class MaassTest(LmfdbTest):
    def test_index(self):
        L = self.tc.get("/ModularForm/GL2/Q/Maass/")
        assert 'database currently contains' in L.get_data(as_text=True)

    def test_browse_1_10_0_10(self):
        L = self.tc.get("https://blue.lmfdb.xyz/ModularForm/GL2/Q/Maass/BrowseGraph/1/10/0/10/")
        assert 'In the plot below each dot is linked' in L.get_data(as_text=True)

    def test_browse_1_15_0_15(self):
        L = self.tc.get("https://blue.lmfdb.xyz/ModularForm/GL2/Q/Maass/BrowseGraph/1/15/0/15/")
        assert 'In the plot below each dot is linked' in L.get_data(as_text=True)

    def test_browse_10_100_0_4(self):
        L = self.tc.get("https://blue.lmfdb.xyz/ModularForm/GL2/Q/Maass/BrowseGraph/10/100/0/4/")
        assert 'In the plot below each dot is linked' in L.get_data(as_text=True)

    def test_browse_100_1000_0_1(self):
        L = self.tc.get("https://blue.lmfdb.xyz/ModularForm/GL2/Q/Maass/BrowseGraph/100/1000/0/1/")
        assert 'In the plot below each dot is linked' in L.get_data(as_text=True)

    def test_search_all(self):
        L = self.tc.get("http://127.0.0.1:37778/ModularForm/GL2/Q/Maass/?search_type=List&all=1")
        assert "9.533695" in L.get_data(as_text=True) and "19.48471" in L.get_data(as_text=True)

    def test_search_N_101(self):
        L = self.tc.get("http://127.0.0.1:37778/ModularForm/GL2/Q/Maass/?hst=List&level=101&search_type=List")
        assert "0.453759" in L.get_data(as_text=True) and "1.11356" in L.get_data(as_text=True)

    def test_search_R_40_50(self):
        L = self.tc.get("http://127.0.0.1:37778/ModularForm/GL2/Q/Maass/?spectral_parameter=40-50&search_type=List")
        assert "40.54335" in L.get_data(as_text=True) and "49.961696" in L.get_data(as_text=True)

    def test_search_R_1234(self):
        L = self.tc.get("http://127.0.0.1:37778/ModularForm/GL2/Q/Maass/?hst=List&spectral_parameter=12.34&search_type=List")
        assert "12.34000" in L.get_data(as_text=True)

    def test_form_1234(self):
        L = self.tc.get("http://127.0.0.1:37778/ModularForm/GL2/Q/Maass/541192fdacf756021f2c6e39")
        assert "coefficients" in L.get_data(as_text=True) and "-1.236693" in L.get_data(as_text=True) and "1.858211" in L.get_data(as_text=True)
