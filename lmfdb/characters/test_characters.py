# -*- coding: utf-8 -*-
from lmfdb.base import LmfdbTest
from lmfdb.WebCharacter import WebDirichlet, WebHecke
from lmfdb.lfunctions.LfunctionDatabase import get_lfunction_by_url

class WebCharacterTest(LmfdbTest):

  def test_Dirichletmethods(self):
      modlabel, numlabel = 14, 5
      mod = WebDirichlet.label2ideal(modlabel)
      assert WebDirichlet.ideal2label(mod) == modlabel
      num = WebDirichlet.label2number(numlabel)
      assert WebDirichlet.number2label(num) == numlabel

  def test_Heckemethods(self):
      from sage.all import NumberField, var
      x = var('x')
      k = NumberField(x**3-x**2+x+1,'a')
      modlabel, numlabel = '128.1', '1.1'
      mod = WebHecke.label2ideal(k, modlabel)
      assert WebHecke.ideal2label(mod) == modlabel
      num = WebHecke.label2number(numlabel)
      assert WebHecke.number2label(num) == numlabel

class DirichletSearchTest(LmfdbTest):

    def test_condbrowse(self):
        W = self.tc.get('/Character/Dirichlet/?condbrowse=24-41')
        assert '(\\frac{40}{\\bullet}\\right)' in W.data

    def test_order(self):
        W = self.tc.get('/Character/Dirichlet/?order=19-23')
        assert '\chi_{25}(2' in W.data

    def test_modbrowse(self):
        W = self.tc.get('/Character/Dirichlet/?modbrowse=51-81')
        """
        curl -s '/Character/?modbrowse=51-81' | grep 'Dirichlet/[0-9][0-9]/27' | wc -l
        There are 20 characters of conductor 27 in this modulus range
        """
        import re
        assert len(re.findall('Dirichlet/[0-9][0-9]/27',W.data)) == 20

    def test_search(self):
        W = self.tc.get('/Character/Dirichlet/?conductor=15&order=4&limit=25')
        assert '\chi_{15}(2,' in W.data and '\chi_{195}(53,' in W.data
        W = self.tc.get('/Character/Dirichlet/?conductor=25-50&order=5-7&limit=25')
        assert '\chi_{25}(6,' in W.data and '\chi_{36}(7,' in W.data
        W = self.tc.get('/Character/Dirichlet/?conductor=25-50&order=5-7&primitive=Yes&limit=25')
        assert '\chi_{25}(6,' in W.data and '\chi_{36}(7,' in W.data
        W = self.tc.get('/Character/Dirichlet/?conductor=25-50&order=5-7&primitive=No&limit=25')
        assert '\chi_{50}(11,' in W.data and '\chi_{72}(7,' in W.data
        W = self.tc.get('/Character/Dirichlet/?conductor=25-50&order=5-7&primitive=No&parity=Odd&limit=25')
        assert '\chi_{56}(23,' in W.data and '\chi_{112}(79,' in W.data
        W = self.tc.get('/Character/Dirichlet/?conductor=25-50&order=5-7&primitive=No&parity=Even&limit=25')
        assert '\chi_{50}(11,' in W.data and '\chi_{75}(46,' in W.data

    def test_condsearch(self):
        W = self.tc.get('/Character/Dirichlet/?conductor=111&limit=100')
        assert '111/17' in W.data

    def test_nextprev(self):
        W = self.tc.get('/Character/Dirichlet/?start=200&count=25&order=3')
        assert '\chi_{169}(22,' in W.data and '\chi_{182}(113,' in W.data
        W = self.tc.get('/Character/Dirichlet/?start=100&count=25&order=3')
        assert '\chi_{97}(35,' in W.data and '\chi_{117}(40,' in W.data

class DirichletTableTest(LmfdbTest):

    def test_table(self):
        get='modulus=35&poly=\%28+x^{6}+\%29+-+\%28+x^{5}+\%29+-+\%28+7+x^{4}+\%29+%2B+\%28+2+x^{3}+\%29+%2B+\%28+7+x^{2}+\%29+-+\%28+2+x+\%29+-+\%28+1+\%29&char_number_list=1%2C4%2C9%2C11%2C16%2C29'
        W = self.tc.get('/Character/Dirichlet/grouptable?%s'%get)
        assert '35 }(29' in W.data

class DirichletCharactersTest(LmfdbTest):

    def test_navig(self):
        W = self.tc.get('/Character/', follow_redirects=True)
        assert 'Browse' in W.data and 'search' in W.data

    def test_dirichletfamily(self):
        W = self.tc.get('/Character/Dirichlet/')
        assert 'Find a specific' in W.data
        assert 'Dirichlet character \(\displaystyle\chi_{13}(2,&middot;)\)' in W.data

    def test_dirichletgroup(self):
        W = self.tc.get('/Character/Dirichlet/23', follow_redirects=True)
        assert 'Yes' in W.data
        assert 'DirichletGroup_conrey(23)' in W.data
        assert 'e\\left(\\frac{7}{11}\\right)' in W.data
        assert '/Character/Dirichlet/23/10' in W.data

        W = self.tc.get('/Character/Dirichlet/91', follow_redirects=True)
        assert 'Yes' in W.data
        assert 'Properties' in W.data, "properties box"
        assert 'DirichletGroup_conrey(91)' in W.data, "sage code example"
        assert '\chi_{91}(15,' in W.data and '\chi_{91}(66' in W.data, "generators"
        assert 'e\\left(\\frac{7}{12}\\right)' in W.data, "contents table"
        assert '/Character/Dirichlet/91/6' in W.data, "link in contents table"

        W = self.tc.get('/Character/Dirichlet/999999999', follow_redirects=True)
        assert 'Properties' in W.data, "properties box"
        assert '648646704' in W.data, "order"
        assert 'C_{333666}' in W.data, "structure"
        assert '\chi_{999999999}(234567902,' in W.data and '\chi_{999999999}(432432433,' in W.data and '\chi_{999999999}(332999668,' in W.data

    def test_dirichletchar11(self):
        W = self.tc.get('/Character/Dirichlet/1/1')
        assert  '/NumberField/1.1.1.1' in W.data

    def test_valuefield(self):
        W = self.tc.get('/Character/Dirichlet/13/2')
        assert  'Value Field' in W.data

    #@unittest2.skip("wait for new DirichletConrey")
    def test_dirichletcharbig(self):
        """ nice example to check the Conrey naming scheme
            for p = 40487, 5 generates Z/pZ but not Z/p^2Z
            the next one is OK, namely 10.
            This test also makes sure the code scales a little bit.
        """
        W = self.tc.get('/Character/Dirichlet/40487/5')
        assert '40486' in W.data
        assert '12409' in W.data, "log on generator"
        W = self.tc.get('/Character/Dirichlet/40487.5', follow_redirects=True)
        assert '40486' in W.data
        assert '12409' in W.data, "log on generator"

    def test_dirichletchar43(self):
        W = self.tc.get('/Character/Dirichlet/4/3')
        assert 'Kronecker symbol' in W.data
        assert '\\left(\\frac{-4}{\\bullet}\\right)' in W.data
        W = self.tc.get('/Character/Dirichlet/4.3', follow_redirects=True)
        assert 'Kronecker symbol' in W.data
        assert '\\left(\\frac{-4}{\\bullet}\\right)' in W.data

    def test_dirichlet_calc(self):
        W = self.tc.get('/Character/calc-gauss/Dirichlet/4/3?val=3')
        assert '-2.0i' in W.data, "calc gauss"
        assert '\Z/4\Z' in W.data

        W = self.tc.get('/Character/calc-kloosterman/Dirichlet/91/3?val=52,34')
        assert '3.774980868' in W.data, "kloosterman"

        W = self.tc.get('Character/calc-jacobi/Dirichlet/91/3?val=37')
        assert '-11 \\zeta_{12}^{2} + 5' in W.data

        W = self.tc.get('Character/calc-value/Dirichlet/107/7?val=32')
        assert 'frac{3}{106}' in W.data

    def test_dirichletchar531(self):
        W = self.tc.get('/Character/Dirichlet/531/40')
        assert '/Character/Dirichlet/531/247' in W.data
        assert '(356,235)' in W.data, "generators"
        #assert 'Kloosterman sum' in W.data
        assert  '(\\zeta_{87})' in W.data, "field of values"

    def test_dirichletchar6000lfunc(self):
        """ Check Sato-Tate group and L-function link for 6000/11  """
        W = self.tc.get('/Character/Dirichlet/6000/11')
        assert '/SatoTateGroup/0.1.100' in W.data
        assert 'L/Character/Dirichlet/6000/11' in W.data
        W = self.tc.get('/L/Character/Dirichlet/6000/11', follow_redirects=True)
        assert '1.076603021' in W.data

    def test_dirichletchar9999lfunc(self):
        """ Check that the L-function link for 9999/2 is displayed if and only if the L-function data is present"""
        W = self.tc.get('/Character/Dirichlet/9999/2')
        assert '/SatoTateGroup/0.1.300' in W.data
        b = get_lfunction_by_url('Character/Dirichlet/9999/2')
        assert bool(b) == ('L/Character/Dirichlet/9999/2' in W.data)

    def test_dirichletchar99999999999999999lfunc(self):
        """ Check Dirichlet character with very large modulus"""
        W = self.tc.get('/Character/Dirichlet/99999999999999999999/2')
        assert 'Odd' in W.data and '536870912' in W.data
        assert '/SatoTateGroup/0.1.3748806900' in W.data

class HeckeCharactersTest(LmfdbTest):

    def test_heckeexamples(self):
        W = self.tc.get('/Character/Hecke/')
        assert '2.2.8.1' in W.data

    def test_heckefamily(self):
        W = self.tc.get('/Character/Hecke/3.1.44.1')
        assert 'C_{5}' in W.data

    def test_heckegroup(self):
        W = self.tc.get('/Character/Hecke/3.1.44.1/4.1')
        assert 'Related objects' in W.data
        assert 'primitive' in W.data

    def test_heckechar(self):
        W = self.tc.get('/Character/Hecke/2.0.4.1/25.2/2')
        assert 'Related objects' in W.data
        assert 'Primitive' in W.data

    def test_hecke_calc(self):
        W = self.tc.get('/Character/calc-value/Hecke/2.0.4.1/25.2/1?val=13.2')
        assert '=-i' in W.data

