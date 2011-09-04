
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
    """
      
    """
    for rule in self.app.url_map.iter_rules():
      if "GET" in rule.methods:
        tc = self.app.test_client()
        res = tc.get(rule.rule)
        assert "LMFDB" in res.data, "rule %s failed " % rule
          

  def test_some_latex_error(self):
    """
      Tests for latex errors, but fails at the moment because of other errors
    """
    for rule in self.app.url_map.iter_rules():
      if "GET" in rule.methods:
        try:
          tc = self.app.test_client()
          res = tc.get(rule.rule)        
          assert not ("Undefined control sequence" in res.data), "rule %s failed" % rule
        except KeyError:
          pass

  random_urls = ["/ModularForm/GL2/Q/Maass/"]
