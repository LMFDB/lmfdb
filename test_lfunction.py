

from base import LmfdbTest
class LfunctionTest(LmfdbTest):
  def test_lfunc_pages(self):
    self.tc.get('/EllipticCurve/Q/j')
