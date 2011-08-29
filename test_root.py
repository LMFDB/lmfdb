
from base import LmfdbTest
class RootTest(LmfdbTest):

  def test_root(self):
    root = self.app.get("/")
    assert "Index" in root.data

  def test_robots(self):
    r = self.app.get("/robots.txt")
    assert "Disallow: /" in r.data

  def test_favicon(self):
    assert len(self.app.get("/favicon.ico").data) > 10

  def test_db(self):
    assert self.C != None
    known_dbnames = self.C.database_names()
    expected_dbnames = ['Lfunctions', 'ellcurves', 'numberfields', 
                        'MaassWaveForm', 'HTPicard', 'Lfunction', 
                        'upload', 'knowledge', 'hmfs', 'userdb', 'quadratic_twists', 
                        'modularforms']
    for dbn in expected_dbnames:
      assert dbn in known_dbnames, 'db "%s" missing' % dbn


