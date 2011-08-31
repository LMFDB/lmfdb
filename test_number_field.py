from base import LmfdbTest

class NumberFieldTest(LmfdbTest):
  def test_sage_crashes(self):
    resp = self.tc.get('/L/NumberField/10.10.513087549389.1/')
    assert "513087549389" in resp.data
