from lmfdb.base import LmfdbTest
from lmfdb.WebCharacter import *
import unittest2

class WebCharacterTest(LmfdbTest):

  def test_Dirichletmethods(self):
      modlabel, numlabel = 14, 5
      mod = WebDirichlet.label2ideal(modlabel)
      assert WebDirichlet.ideal2label(mod) == modlabel
      num = WebDirichlet.label2number(numlabel)
      assert WebDirichlet.number2label(num) == numlabel
    
  def test_Heckemethods(self):
      from sage.all import NumberField
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
    #    assert url_for('characters.render_characterNavigation') == '/Character/'
    #    assert url_character(type='Hecke') == '/Character/Hecke'
    #    assert url_character(type='Dirichlet') == '/Character/Dirichlet'
    #    assert url_for('characters.render_Dirichletwebpage', modulus='132') == '/Character/Dirichlet/132'

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
        curl -s '/Character/?modbrowse=51-81' | grep 'Dirichlet/[0-9][0-9]/27' | wc -l
        There are 20 characters of conductor 27 in this modulus range
        """
        import re
        assert len(re.findall('Dirichlet/[0-9][0-9]/27',W.data)) == 20

    def test_search(self):
        W = self.tc.get('/Character/?conductor=15&order=4')
        assert '\displaystyle \chi_{ 45}(17' in W.data

class DirichletTableTest(LmfdbTest):

    def test_table(self):
        get='modulus=35&poly=\%28+x^{6}+\%29+-+\%28+x^{5}+\%29+-+\%28+7+x^{4}+\%29+%2B+\%28+2+x^{3}+\%29+%2B+\%28+7+x^{2}+\%29+-+\%28+2+x+\%29+-+\%28+1+\%29&char_number_list=1%2C4%2C9%2C11%2C16%2C29'
        W = self.tc.get('/Character/Dirichlet/grouptable?%s'%get)
        assert '35 }(29' in W.data

class DirichletCharactersTest(LmfdbTest):

    def test_navig(self):
        W = self.tc.get('/Character/')
        assert 'Browse' in W.data and 'search' in W.data

    def test_dirichletfamily(self):
        W = self.tc.get('/Character/Dirichlet/')
        assert 'Find a specific' in W.data
        assert 'Dirichlet character \(\displaystyle\chi_{13}(2,&middot;)\)' in W.data

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
        assert '15,66' in W.data, "generators"
        assert 'e\\left(\\frac{7}{12}\\right)' in W.data, "contents table"
        assert '/Character/Dirichlet/91/6' in W.data, "link in contents table"

    def test_dirichletchar11(self):
        W = self.tc.get('/Character/Dirichlet/1/1')
        assert 'Character group' in W.data
        #assert '/Character/Dirichlet/0/1' not in W.data, "prev link"
        #assert '/Character/Dirichlet/2/1' in W.data, "next link"
        assert  '/NumberField/1.1.1.1' in W.data
     
    #@unittest2.skip("wait for new DirichletConrey")
    def test_dirichletcharbig(self):
        """ nice example to check the Conrey naming scheme
            for p = 40487, 5 generates Z/pZ but not Z/p^2Z
            the next one is OK, namely 10.
            This test also makes sure the code scales a little bit.
        """
        W = self.tc.get('/Character/Dirichlet/40487/5')
        assert 'Character group' in W.data
        assert '40486' in W.data
        assert '12409' in W.data, "log on generator"
        #assert '/Character/Dirichlet/40487/6' in W.data, "next link"

    def test_dirichletchar43(self):
        W = self.tc.get('/Character/Dirichlet/4/3')
        assert 'Kronecker symbol' in W.data
        assert '\\left(\\frac{4}{\\bullet}\\right)' in W.data

    def test_dirichlet_calc(self):
        W = self.tc.get('/Character/calc-gauss/Dirichlet/4/3?val=3')
        assert '-2.0i' in W.data, "calc gauss"
        assert '\Z/4\Z' in W.data
        
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
        #assert '(119,415)' in W.data, "generators"
        assert '(356,235)' in W.data, "generators"
        assert 'Kloosterman sum' in W.data
        # next line commented out as homepage.html no longer diplays
        #these (deliberately) as they were not useful, and possibly
        #confusing!
        #assert '/Character/Dirichlet/531/38' in W.data, "prev navigation"
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

