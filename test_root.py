
from base import LmfdbTest
class RootTest(LmfdbTest):

  def test_root(self):
    root = self.tc.get("/")
    assert "DataBase" in root.data

  def test_robots(self):
    r = self.tc.get("/robots.txt")
    assert "Disallow: /" in r.data

  def test_favicon(self):
    assert len(self.tc.get("/favicon.ico").data) > 10

  def test_db(self):
    assert self.C != None
    known_dbnames = self.C.database_names()
    expected_dbnames = ['Lfunctions', 'ellcurves', 'numberfields', 
                        'MaassWaveForm', 'HTPicard', 'Lfunction', 
                        'upload', 'knowledge', 'hmfs', 'userdb', 'quadratic_twists', 
                        'modularforms']
    for dbn in expected_dbnames:
      assert dbn in known_dbnames, 'db "%s" missing' % dbn

  def test_url_map(self):
    for rule in self.app.url_map.iter_rules():
      if "GET" in rule.methods:
        tc = self.app.test_client()
        res = tc.get(rule.rule)
        assert "LMFDB" in res.data, "rule %s failed" % rule
