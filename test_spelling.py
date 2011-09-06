

from base import LmfdbTest
class SpellingTest(LmfdbTest):
  # this tests the spelling on the website
  
  
  def test_zeroes_spelling(self):
    """
        'zeroes' should be 'zeros'
    """
    for rule in self.app.url_map.iter_rules():
      
      if "GET" in rule.methods:
        try:
          tc = self.app.test_client()
          res = tc.get(rule.rule)
          assert not ("zeroes" in res.data), "rule %s failed " % rule
        except KeyError:
          pass

  def test_maass_spelling(self):
    """
        'Maass', not anything else
    """
    for rule in self.app.url_map.iter_rules():
      
      if "GET" in rule.methods:
        try:
          tc = self.app.test_client()
          res = tc.get(rule.rule)
          assert not ("maas" in res.data), "rule %s failed " % rule
          assert not ("mass" in res.data), "rule %s failed " % rule
          assert not ("Maas" in res.data), "rule %s failed " % rule
          assert not ("Mass" in res.data), "rule %s failed " % rule
        except KeyError:
          pass
