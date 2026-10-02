from math import gcd, sqrt

from lmfdb.tests import LmfdbTest
from lmfdb.characters.TinyConrey import ConreyCharacter
from lmfdb.characters.portraits import (
    PORTRAIT_CACHE_SIZE,
    PORTRAIT_MAX_MODULUS,
    paint_portrait,
    partial_gauss_sums,
    portrait_complexity,
    portrait_data,
    portrait_is_enabled,
    portrait_properties,
)
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
        # Each filter is checked in both directions, so a parameter that stops
        # being parsed widens the search and trips a negative assertion.
        # Conductor 16, order 4 has a primitive even orbit (16.e), a primitive
        # odd one (16.f), and imprimitive counterparts at modulus 32.  Labels
        # carry their tags, since a bare '16.e' also matches '416.e'.
        page = self.tc.get('/Character/Dirichlet/?conductor=15&order=4').get_data(as_text=True)
        assert '>15.e<' in page
        page = self.tc.get('/Character/Dirichlet/?conductor=16&order=4&is_primitive=no').get_data(as_text=True)
        assert '>32.e<' in page and '>32.f<' in page
        assert '>16.e<' not in page and '>16.f<' not in page
        page = self.tc.get('/Character/Dirichlet/?conductor=16&order=4&parity=even').get_data(as_text=True)
        assert '>16.e<' in page and '>32.e<' in page
        assert '>16.f<' not in page and '>32.f<' not in page
        page = self.tc.get('/Character/Dirichlet/?conductor=16&order=4&parity=odd').get_data(as_text=True)
        assert '>16.f<' in page and '>32.f<' in page
        assert '>16.e<' not in page and '>32.e<' not in page
        page = self.tc.get('/Character/Dirichlet/?conductor=16&order=4&is_primitive=no&parity=odd').get_data(as_text=True)
        assert '>32.f<' in page
        assert '>16.e<' not in page and '>16.f<' not in page and '>32.e<' not in page
        # A conductor range matches no index prefix, so this one reads every
        # orbit of conductor 25-50 before it can sort; allow the timeout page.
        self.check_args_with_timeout(
            '/Character/Dirichlet/?conductor=25-50&order=5-7', '>25.d<')

    def test_condsearch(self):
        W = self.tc.get('/Character/Dirichlet/?conductor=111')
        assert '111.m' in W.get_data(as_text=True)

    def test_nextprev(self):
        W = self.tc.get('/Character/Dirichlet/?start=200&count=25&order=3')
        assert r'288.i' in W.get_data(as_text=True)
        W = self.tc.get('/Character/Dirichlet/?start=100&count=25&order=3')
        assert r'169.c' in W.get_data(as_text=True)

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

        # Tests for URL behavior of characters

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

    def test_portrait(self):
        # The Gauss-sum portrait (issue #3996) is embedded in the properties
        # box, computed on the fly, and explained in the Learn more box.
        W = self.tc.get('/Character/Dirichlet/27/8')
        page = W.get_data(as_text=True)
        assert 'class="dirichlet-character-portrait"' in page, "portrait present"
        assert 'alt="Gauss-sum portrait of the Dirichlet character 27.8"' in page
        assert 'src="data:image/png;base64,' in page
        assert 'Picture description' in page

    def test_portrait_page(self):
        W = self.tc.get('/Character/Dirichlet/Pictures')
        assert 'Pictures for Dirichlet characters' in W.get_data(as_text=True)

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


class DirichletPortraitTest(LmfdbTest):
    """Unit tests for the Gauss-sum portraits of issue #3996.

    ``add_portrait`` swallows every exception, so a regression in the math
    below would silently turn into a missing picture rather than a failing
    page; these tests check the data the picture is drawn from directly.
    """

    def test_complete_gauss_sums(self):
        """The last partial sum is the complete Gauss sum computed by pari."""
        for modulus, number in [(4, 3),     # primitive, real, odd
                                (5, 2),     # primitive, order 4, not real
                                (15, 4),    # imprimitive, of conductor 5
                                (12, 11)]:  # composite modulus, 8 nonunits
            chi = ConreyCharacter(modulus, number)
            _, sums = partial_gauss_sums(modulus, number)
            for a in range(modulus):
                tau = complex(chi.gauss_sum_numerical(a))
                assert abs(sums[a, -1] - tau) < 1e-10, \
                    "tau_%s of %s.%s" % (a, modulus, number)

    def test_primitive_radius(self):
        """The invariant the picture is drawn to expose: for a primitive
        character the dots with gcd(a, N) = 1 lie on the circle of radius
        sqrt(N), and all the other dots sit at the origin."""
        modulus, number = 27, 2
        assert ConreyCharacter(modulus, number).conductor() == modulus
        _, sums = partial_gauss_sums(modulus, number)
        for a in range(modulus):
            if gcd(a, modulus) == 1:
                assert abs(abs(sums[a, -1]) - sqrt(modulus)) < 1e-10, \
                    "|tau_%s| = sqrt(%s)" % (a, modulus)
            else:
                assert abs(sums[a, -1]) < 1e-10, "tau_%s = 0" % a

    def test_modulus_one(self):
        """The trivial character has no partial sums at all: its portrait is
        the single complete Gauss sum tau_0 = 1."""
        segments, _, dots, _ = portrait_data(1, 1)
        assert segments.shape == (0, 2, 2)
        assert dots.shape == (1, 2)
        assert abs(dots[0][0] - 1) < 1e-10 and abs(dots[0][1]) < 1e-10
        assert paint_portrait(1, 1).startswith('data:image/png;base64,')

    def test_workload_cutoff(self):
        """Portraits are limited by the work they take, not by the modulus:
        the prime 293 needs 293*292 segments, while the larger 300 needs only
        300*phi(300) = 300*80."""
        assert portrait_complexity(293) == 85556
        assert portrait_complexity(300) == 24000
        assert not portrait_is_enabled(293)
        assert portrait_is_enabled(300)
        assert not portrait_is_enabled(PORTRAIT_MAX_MODULUS + 1)
        # a character we decline to draw is a quiet None, not an error
        assert paint_portrait(293, 17) is None
        assert portrait_properties(40487, 5) is None

    def test_cache(self):
        """Completed portraits are cached, in a cache of bounded size."""
        paint_portrait.cache_clear()
        first = paint_portrait(3, 2)
        assert paint_portrait.cache_info().hits == 0
        second = paint_portrait(3, 2)
        info = paint_portrait.cache_info()
        assert second is first
        assert info.hits == 1
        assert info.maxsize == PORTRAIT_CACHE_SIZE
        # characters with no portrait never reach the cache
        paint_portrait(293, 17)
        assert paint_portrait.cache_info().misses == info.misses
