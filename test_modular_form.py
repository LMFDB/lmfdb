

from base import LmfdbTest
class ModularFormTest(LmfdbTest):
  
  def test_Maass(self):
    self.url = "/ModularForm/GL2/Q/Maass/"
    tc = self.app.test_client()
    res = tc.get(self.url)
    assert "Maass" in res.data

    
  def test_Siegel(self):
    self.url = "ModularForm/GSp4/Q"
    tc = self.app.test_client()
    res = tc.get(self.url)
    assert "Siegel" in res.data
  
