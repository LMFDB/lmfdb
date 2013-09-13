from lmfdb.base import LmfdbTest
from lmfdb.WebCharacter import *
from lmfdb.utils import url_character

class WebCharacterTest(LmfdbTest):

  def test_Dirichletmethods(self):
      modlabel, numlabel = 14, 5
      mod = WebDirichlet.label2ideal(modlabel)
      assert WebDirichlet.ideal2label(mod) == modlabel
      num = WebDirichlet.label2number(numlabel)
      assert WebDirichlet.number2label(num) == numlabel
    
  def test_Heckemethods(self):
      from sage.all import *
      x = var('x')
      k = NumberField(x**3-x**2+x+1,'a')
      modlabel, numlabel = '82.-5a0+1a2', '5.3.3'
      mod = WebHecke.label2ideal(k, modlabel)
      assert WebHecke.ideal2label(mod) == modlabel
      num = WebHecke.label2number(numlabel)
      assert WebHecke.number2label(num) == numlabel

class UrlCharacterTest(LmfdbTest):
  
    pass
    # FIXME: this test does not work, why ???
    #def test_url_character(self):
    #    assert url_character() == '/Character/'
    #    assert url_character(type='Hecke') == '/Character/Hecke'
    #    assert url_character(type='Dirichlet') == '/Character/Dirichlet'
    #    assert url_character(type='Dirichlet', modulus='132') == '/Character/Dirichlet/132'

class DirichletSearchTest(LmfdbTest):

    def test_condbrowse(self): 
        W = self.tc.get('/Character/?condbrowse=24-41')
        assert '(\\frac{40}{\\bullet}\\right)' in W.data
        
    def test_ordbrowse(self): 
        W = self.tc.get('/Character/?ordbrowse=17-23')
        assert '\chi_{ 191 }( 32' in W.data

    def test_modbrowse(self): 
        W = self.tc.get('/Character/?modbrowse=51-81')
        """
        curl '/Character/?modbrowse=51-81' | grep '27' | wc -l
        each 27 occurs twice
        """
        assert W.data.count('27') == 40

    def test_search(self):
        W = self.tc.get('/Character/?conductor=15&order=4')
        assert '\displaystyle \chi_{ 45}(17' in W.data

class DirichletCharactersTest(LmfdbTest):

    def test_navig(self):
        W = self.tc.get('/Character/')
        assert 'Browse' in W.data and 'search' in W.data

    def test_dirichletfamily(self):
        W = self.tc.get('/Character/Dirichlet/')
        assert '/Character/Dirichlet/11/3' in W.data, "7th first conductor"
        assert 'C_{2}\\times C_{2}' in W.data

    def test_dirichletgroup(self):
        W = self.tc.get('/Character/Dirichlet/23')
        assert 'Yes' in W.data
        assert 'DirichletGroup_conrey(23)' in W.data
        assert 'e\\left(\\frac{7}{11}\\right)' in W.data
        assert '/Character/Dirichlet/23/10' in W.data

        W = self.tc.get('/Character/Dirichlet/91')
        assert 'Yes' in W.data
        assert 'Properties' in W.data, "properties box"
        assert 'DirichletGroup_conrey(91)' in W.data, "sage code example"
        assert '66,15' in W.data, "generators"
        assert 'e\\left(\\frac{7}{12}\\right)' in W.data, "contents table"
        assert '/Character/Dirichlet/91/6' in W.data, "link in contents table"

    def test_dirichletchar11(self):
        W = self.tc.get('/Character/Dirichlet/1/1')
        assert 'Character group' in W.data
        assert '/Character/Dirichlet/0/1' not in W.data, "prev link"
        assert '/Character/Dirichlet/2/1' in W.data, "next link"
        assert  '/NumberField/1.1.1.1' in W.data
     
    def test_dirichletchar43(self):
        W = self.tc.get('/Character/Dirichlet/4/3')
        assert 'Kronecker symbol' in W.data
        assert '\\left(\\frac{4}{\\bullet}\\right)' in W.data

    def test_dirichlet_calc(self):
        W = self.tc.get('/Character/calc-gauss/Dirichlet/4/3?val=3')
        assert '-2.0i' in W.data, "calc gauss"
        assert '\mathbb{Z}/4\mathbb{Z}' in W.data
        
        W = self.tc.get('/Character/calc-kloosterman/Dirichlet/91/3?val=52,34')
        assert '3.774980868' in W.data, "kloosterman"

        W = self.tc.get('Character/calc-jacobi/Dirichlet/91/3?val=37')
        assert '-5 \\zeta_{12}^{2} - 6' in W.data

        W = self.tc.get('Character/calc-value/Dirichlet/107/7?val=32')
        assert 'frac{3}{106}' in W.data

    def test_dirichletchar(self):
        W = self.tc.get('/Character/Dirichlet/531/40')
        assert 'Character group' in W.data
        assert '/Character/Dirichlet/531/391' in W.data
        assert '(119,415)' in W.data, "generators"
        assert 'Kloosterman sum' in W.data
        assert '/Character/Dirichlet/531/38' in W.data, "prev navigation"
        assert  '(\\zeta_{87})' in W.data, "field of values"

class HeckeCharactersTest(LmfdbTest):


    def test_heckeexamples(self):
        W = self.tc.get('/Character/Hecke/')
        assert '2.2.8.1' in W.data

    def test_heckefamily(self):
        W = self.tc.get('/Character/Hecke/3.1.44.1')
        assert 'C_{5}' in W.data

    def test_heckegroup(self):
        W = self.tc.get('/Character/Hecke/3.1.44.1/4.0')
        assert 'Related objects' in W.data
        assert 'primitive' in W.data

    def test_heckechar(self):
        #W = self.tc.get('/Character/Hecke/7.3.674057.1')
        W = self.tc.get('/Character/Hecke/2.0.4.1/5./2')
        assert 'Related objects' in W.data
        assert 'primitive' in W.data

    def test_hecke_calc(self):
        W = self.tc.get('/Character/calc-value/Hecke/2.0.4.1/5./1?val=1-a')
        assert '(1-a)=i' in W.data

