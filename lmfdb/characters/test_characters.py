from lmfdb.tests import LmfdbTest
from lmfdb.characters.web_character import WebDirichlet, parity_string, bool_string
from lmfdb.lfunctions.LfunctionDatabase import get_lfunction_by_url
from lmfdb.utils import comma


class WebCharacterTest(LmfdbTest):

    def test_Dirichletmethods(self):
        modlabel, numlabel = 14, 5
        mod = WebDirichlet.label2ideal(modlabel)
        assert WebDirichlet.ideal2label(mod) == modlabel
        num = WebDirichlet.label2number(numlabel)
        assert WebDirichlet.number2label(num) == numlabel


class DirichletSearchTest(LmfdbTest):
    def test_nchars(self):
        from lmfdb import db
        nchars = db.char_dirichlet.sum('degree')
        W = self.tc.get('/Character/Dirichlet/')
        assert comma(nchars) in W.get_data(as_text=True)

    def test_order(self):
        W = self.tc.get('/Character/Dirichlet/?order=19-23')
        assert r'25.f' in W.get_data(as_text=True)

    def test_even_odd(self):
        W = self.tc.get('/Character/Dirichlet/?modulus=35')
        assert '>%s</t' % (parity_string(1)) in W.get_data(as_text=True)
        assert '>%s</t' % (parity_string(-1)) in W.get_data(as_text=True)

    def test_modbrowse(self):
        W = self.tc.get('/Character/Dirichlet/?modulus=41-60')
        assert '46.d' in W.get_data(as_text=True)

    def test_search(self):
        W = self.tc.get('/Character/Dirichlet/?conductor=15&order=4')
        assert r'15.e' in W.get_data(as_text=True)
        W = self.tc.get('/Character/Dirichlet/?conductor=25-50&order=5-7')
        assert r'25.d' in W.get_data(as_text=True)
        W = self.tc.get('/Character/Dirichlet/?conductor=25-50&order=5-7&primitive=Yes')
        assert r'25.d' in W.get_data(as_text=True)
        W = self.tc.get('/Character/Dirichlet/?conductor=25-50&order=5-7&primitive=No')
        assert r'50.d' in W.get_data(as_text=True)
        W = self.tc.get('/Character/Dirichlet/?conductor=25-50&order=5-7&primitive=No&parity=Odd')
        assert r'56.n' in W.get_data(as_text=True)
        W = self.tc.get('/Character/Dirichlet/?conductor=25-50&order=5-7&primitive=No&parity=Even')
        assert r'50.d' in W.get_data(as_text=True)

    def test_condsearch(self):
        W = self.tc.get('/Character/Dirichlet/?conductor=111')
        assert '111.m' in W.get_data(as_text=True)

    def test_nextprev(self):
        W = self.tc.get('/Character/Dirichlet/?start=200&count=25&order=3')
        assert r'288.i' in W.get_data(as_text=True)
        W = self.tc.get('/Character/Dirichlet/?start=100&count=25&order=3')
        assert r'169.c' in W.get_data(as_text=True)

    def test_field_columns(self):
        # The kernel and value field columns are computed in a batched
        # postprocessing step (see issue #6008)
        W = self.tc.get('/Character/Dirichlet/?search_type=List')
        data = W.get_data(as_text=True)
        # value field knowls for Q and Q(zeta_3)
        assert 'label=1.1.1.1' in data
        assert 'label=2.0.3.1' in data
        # kernel field knowl for Q(zeta_5)
        assert 'label=4.0.125.1' in data
        # The order 4 characters of modulus 13 cut out 4.0.2197.1, which is
        # not the value field of any character, so this pins down the kernel
        # field column (and is a quartic field whose pretty name needs more
        # than the label)
        W = self.tc.get('/Character/Dirichlet/?modulus=13&order=4&search_type=List&showcol=first')
        data = W.get_data(as_text=True)
        assert 'label=4.0.2197.1' in data
        assert r'\(\Q(\sqrt{-26 -6 \sqrt{13}})\)' in data
        # kernel fields that are not in the database
        W = self.tc.get('/Character/Dirichlet/?modulus=5002&order=12&search_type=List&showcol=first')
        assert 'knowl="nf.field.missing"' in W.get_data(as_text=True)
        # value fields that are not in the database
        W = self.tc.get('/Character/Dirichlet/?order=47&search_type=List')
        assert r'$\Q(\zeta_{47})$' in W.get_data(as_text=True)
        # kernel fields are not computed for orders larger than 12
        W = self.tc.get('/Character/Dirichlet/?order=13-100&search_type=List')
        assert 'not computed' in W.get_data(as_text=True)

    def test_field_columns_no_lookups(self):
        # Once character_postprocess has run, displaying the kernel field must
        # not go back to the database: it is the per-field record lookups that
        # issue #6008 is about.
        from unittest.mock import patch
        from lmfdb import db
        from lmfdb.characters.main import character_postprocess, display_kernel_field
        from lmfdb.number_fields.web_number_field import field_pretty

        res = list(db.char_dirichlet.search({'modulus': 13, 'order': 4}))
        res = character_postprocess(res, {}, {})
        assert [rec['kernel_field_data']['label'] for rec in res] == ['4.0.2197.1']

        def no_lookup(*args, **kwargs):
            raise AssertionError("number field record lookup while displaying a kernel field")

        # field_pretty caches by label, so a lookup made by an earlier test
        # would otherwise hide one made here
        field_pretty.clear_cache()
        with patch.object(db.nf_fields, 'lookup', no_lookup), \
             patch.object(db.nf_fields, 'lucky', no_lookup), \
             patch.object(db.nf_fields_extra, 'lookup', no_lookup):
            displayed = [display_kernel_field(rec['modulus'], rec['first'], rec['order'],
                                              rec['kernel_poly'], rec['kernel_field_data'])
                         for rec in res]
        assert 'label=4.0.2197.1' in displayed[0]
        assert r'\(\Q(\sqrt{-26 -6 \sqrt{13}})\)' in displayed[0]

    def test_field_columns_download(self):
        # The virtual columns added by character_postprocess must not leak into
        # downloads: the kernel field column downloads as [modulus, first, order]
        # and the value field column as the raw order
        url = ('/Character/Dirichlet/?query=%7B%27order%27%3A+4%2C+%27modulus%27%3A+13%7D'
               '&Submit=text&download=1&search_type=List&showcol=first')
        data = self.tc.get(url).get_data(as_text=True)
        assert '[Orbit label, Conrey labels, Modulus, Conductor, Order, Kernel field,' in data
        assert '"13.d"\t[13, 5, 8, 2]\t13\t13\t4\t[13, 5, 4]\t' in data

class DirichletTableTest(LmfdbTest):

    def test_table(self):
        get = r'modulus=35&poly=x%5E6+-+x%5E5+-+7%2Ax%5E4+%2B+2%2Ax%5E3+%2B+7%2Ax%5E2+-+2%2Ax+-+1&char_number_list=1%2C4%2C9%2C11%2C16%2C29'
        W = self.tc.get('/Character/Dirichlet/grouptable?%s' % get)
        assert '35 }(29' in W.get_data(as_text=True)

class DirichletCharactersTest(LmfdbTest):

    def test_navig(self):
        W = self.tc.get('/Character/', follow_redirects=True)
        assert 'Browse' in W.get_data(as_text=True) and 'search' in W.get_data(as_text=True)

    def test_dirichletfamily(self):
        W = self.tc.get('/Character/Dirichlet/')
        assert 'Find' in W.get_data(as_text=True)
        assert r'13.2' in W.get_data(as_text=True)

    def test_dirichletgroup(self):
        W = self.tc.get('/Character/Dirichlet/23', follow_redirects=True)
        assert bool_string(True) in W.get_data(as_text=True)
        assert 'DirichletGroup(23)' in W.get_data(as_text=True)
        assert 'e\\left(\\frac{7}{11}\\right)' in W.get_data(as_text=True)
        assert '\\chi_{23}(10,\\cdot)' in W.get_data(as_text=True)

        W = self.tc.get('/Character/Dirichlet/91', follow_redirects=True)
        assert bool_string(True) in W.get_data(as_text=True)
        assert 'Properties' in W.get_data(as_text=True), "properties box"
        assert 'DirichletGroup(91)' in W.get_data(as_text=True), "sage code example"
        assert r'\chi_{91}(15,' in W.get_data(as_text=True) and r'\chi_{91}(66' in W.get_data(as_text=True), "generators"
        assert r'e\left(\frac{7}{12}\right)' in W.get_data(as_text=True), "contents table"
        assert '/Character/Dirichlet/91/6' in W.get_data(as_text=True), "link in contents table"

        W = self.tc.get('/Character/Dirichlet/999999999', follow_redirects=True)
        assert 'Properties' in W.get_data(as_text=True), "properties box"
        assert '648646704' in W.get_data(as_text=True), "order"
        assert 'C_{333666}' in W.get_data(as_text=True), "structure"
        assert r'\chi_{999999999}(234567902,' in W.get_data(as_text=True) and r'\chi_{999999999}(432432433,' in W.get_data(as_text=True) and r'\chi_{999999999}(332999668,' in W.get_data(as_text=True)

    def test_dirichletgalorbs(self):
        W = self.tc.get('/Character/Dirichlet/289/j').get_data(as_text=True)
        assert r'&rarr; <a href="/Character/Dirichlet/289/j"> j</a>' in W
        table_row = (r'<td class="center">\(-1\)</td>  '
                    r'<td class="center">\(1\)</td>  '
                    r'<td class="center">\(e\left(\frac{57}{136}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{191}{272}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{57}{68}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{219}{272}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{33}{272}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{229}{272}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{35}{136}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{55}{136}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{61}{272}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{41}{272}\right)\)</td>')
        assert table_row in W
        assert "Underlying data" in W and "data/289.j" in W

        W = self.tc.get('/Character/Dirichlet/7145/da')
        assert r'&rarr; <a href="/Character/Dirichlet/7145/da"> da</a>' in W.get_data(as_text=True)
        table_row = (r'<td class="center">\(-1\)</td>  '
                    r'<td class="center">\(1\)</td>  '
                    r'<td class="center">\(e\left(\frac{19}{84}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{481}{714}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{19}{42}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{1285}{1428}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{341}{357}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{19}{28}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{124}{357}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{779}{1428}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{15}{119}\right)\)</td>  '
                    r'<td class="center">\(e\left(\frac{115}{714}\right)\)</td>')
        assert table_row in W.get_data(as_text=True)

        # Tests for URL behaviour of characters

        W = self.tc.get('/Character/Dirichlet/5489/banana/100', follow_redirects=True)
        assert bool_string(True) in W.get_data(as_text=True)
        assert r"The URL has been duly corrected." in W.get_data(as_text=True)

        W = self.tc.get('/Character/Dirichlet/254/banana', follow_redirects=True)
        assert 'Error: No Galois orbit of Dirichlet characters with' in W.get_data(as_text=True)

        W = self.tc.get('/Character/Dirichlet/10001/banana/100', follow_redirects=True)
        assert r'10001.i' in W.get_data(as_text=True)

        W = self.tc.get('/Character/Dirichlet/9999999999/banana', follow_redirects=True)
        assert 'Error: Galois orbits have only been computed for modulus up to 100,000' in W.get_data(as_text=True)

        W = self.tc.get('/Character/Dirichlet/58589/50021', follow_redirects=True)
        assert 'Number field defined by a degree 1428 polynomial' in W.get_data(as_text=True)

    def test_dirichletchar11(self):
        W = self.tc.get('/Character/Dirichlet/1/1')
        assert '/NumberField/1.1.1.1' in W.get_data(as_text=True)

    def test_dirichletchar21(self):
        W = self.tc.get('/Character/Dirichlet/2/1')
        assert '/NumberField/1.1.1.1' in W.get_data(as_text=True)

    def test_valuefield(self):
        W = self.tc.get('/Character/Dirichlet/13/2')
        assert 'Value field' in W.get_data(as_text=True)

    def test_dirichletcharbig(self):
        """ nice example to check the Conrey naming scheme
            for p = 40487, 5 generates Z/pZ but not Z/p^2Z
            the next one is OK, namely 10.
            This test also makes sure the code scales a little bit.
        """
        W = self.tc.get('/Character/Dirichlet/40487/5')
        assert '40486' in W.get_data(as_text=True), "order"
        assert '12409' in W.get_data(as_text=True), "log on generator"
        assert '20243' in W.get_data(as_text=True), "field of values"
        W = self.tc.get('/Character/Dirichlet/40487.5', follow_redirects=True)
        assert '40486' in W.get_data(as_text=True), "order"
        assert '20243' in W.get_data(as_text=True), "field of values"

    def test_dirichletchar43(self):
        W = self.tc.get('/Character/Dirichlet/4/3')
        assert 'Kronecker symbol' in W.get_data(as_text=True)
        assert r'\left(\frac{-4}{\bullet}\right)' in W.get_data(as_text=True)
        W = self.tc.get('/Character/Dirichlet/4.3', follow_redirects=True)
        assert 'Kronecker symbol' in W.get_data(as_text=True)
        assert r'\left(\frac{-4}{\bullet}\right)' in W.get_data(as_text=True)

    def test_dirichlet_calc(self):
        W = self.tc.get('/Character/calc-gauss/Dirichlet/4/3?val=3')
        assert '-2.0i' in W.get_data(as_text=True), "calc gauss"
        assert r'\Z/4\Z' in W.get_data(as_text=True)

        W = self.tc.get('/Character/calc-kloosterman/Dirichlet/91/3?val=52,34')
        assert '3.774980868' in W.get_data(as_text=True), "kloosterman"

        W = self.tc.get('Character/calc-jacobi/Dirichlet/91/3?val=37')
        assert r'-11 \zeta_{6} + 5' in W.get_data(as_text=True)

        W = self.tc.get('Character/calc-value/Dirichlet/107/7?val=32')
        assert 'frac{3}{106}' in W.get_data(as_text=True)

    def test_dirichletchar531(self):
        W = self.tc.get('/Character/Dirichlet/531/40')
        assert '/Character/Dirichlet/531/247' in W.get_data(as_text=True)
        assert '(119,415)' in W.get_data(as_text=True), "generators"
        assert 'Kloosterman sum' in W.get_data(as_text=True)
        assert r'(\zeta_{87})' in W.get_data(as_text=True), "field of values"

    def test_dirichletchar6000lfunc(self):
        """ Check Sato-Tate group and L-function link for 6000/11  """
        W = self.tc.get('/Character/Dirichlet/6000/11')
        assert '/SatoTateGroup/0.1.100' in W.get_data(as_text=True)
        assert 'L/1-6000-6000.11-r0-0-0' in W.get_data(as_text=True)
        W = self.tc.get('L/1-6000-6000.11-r0-0-0', follow_redirects=True)
        assert '1.076603021' in W.get_data(as_text=True)

    def test_dirichletchar9999lfunc(self):
        """ Check that the L-function link for 9999/2 is displayed if and only if the L-function data is present"""
        W = self.tc.get('/Character/Dirichlet/9999/2')
        assert '/SatoTateGroup/0.1.300' in W.get_data(as_text=True)
        b = get_lfunction_by_url('Character/Dirichlet/9999/2')
        assert bool(b) == ('L/Character/Dirichlet/9999/2' in W.get_data(as_text=True))

    def test_dirichletchar99999999999999999lfunc(self):
        """ Check Dirichlet character with very large modulus"""
        W = self.tc.get('/Character/Dirichlet/99999999999999999999/2')
        assert r'e\left(\frac{881}{1818}\right)' in W.get_data(as_text=True), "value on a generator is wrong"
        assert r'\(e\left(\frac{782530507}{937201725}\right)\)' in W.get_data(as_text=True), "one of the first values is wrong"
        assert r'$\Q(\zeta_{3748806900})$' in W.get_data(as_text=True), "field of values is wrong"
        assert r'/SatoTateGroup/0.1.3748806900' in W.get_data(as_text=True), "Sato-Tate related object link is wrong"

    def test_sage_code_gens(self):
        """Test that the sage code stubs generate the correct character. This
           is important because the same logic for generating the display code
           is used to generate the character for computing gauss/kloosterman
           sums etc. The three tests below have been chosen for issues
           identified with previous versions of the sage generating code.
        """
        W = self.tc.get('/Character/Dirichlet/163/4')
        assert 'H = DirichletGroup(163, base_ring=CyclotomicField(162))' in W.get_data(as_text=True), "sage code group is wrong"
        assert 'chi = DirichletCharacter(H, M([2]))' in W.get_data(as_text=True), "sage code generator is wrong"

        W = self.tc.get('/Character/Dirichlet/16/15')
        assert 'H = DirichletGroup(16, base_ring=CyclotomicField(2))' in W.get_data(as_text=True), "sage code group is wrong"
        assert 'chi = DirichletCharacter(H, M([1,0]))' in W.get_data(as_text=True), "sage code generator is wrong"

        W = self.tc.get('/Character/Dirichlet/91/3')
        assert 'H = DirichletGroup(91, base_ring=CyclotomicField(6))' in W.get_data(as_text=True), "sage code group is wrong"
        assert 'chi = DirichletCharacter(H, M([1,2]))' in W.get_data(as_text=True), "sage code generator is wrong"

    def test_underlying_data(self):
        W = self.tc.get('/Character/Dirichlet/data/289.j.7').get_data(as_text=True)
        assert 'is_minimal' in W and 'last' in W
        W = self.tc.get('/Character/Dirichlet/data/289.j').get_data(as_text=True)
        assert 'is_minimal' in W
