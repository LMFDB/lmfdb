from urllib.parse import parse_qsl

from lmfdb import db
from lmfdb.tests import LmfdbTest
from lmfdb.characters.main import common_parse
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

    def test_primitive_search(self):
        # A primitive character has modulus equal to its conductor, which is
        # used to answer these searches from the (conductor, modulus, orbit)
        # index; see issue #6733
        W = self.tc.get('/Character/Dirichlet/?conductor=17&is_primitive=yes')
        data = W.get_data(as_text=True)
        assert 'Results (4 matches)' in data
        for label in ['17.b', '17.c', '17.d', '17.e']:
            assert label in data
        W = self.tc.get('/Character/Dirichlet/?conductor=17,61&is_primitive=yes')
        data = W.get_data(as_text=True)
        assert '17.e' in data and '61.b' in data
        W = self.tc.get('/Character/Dirichlet/?modulus=61&is_primitive=yes')
        assert '61.h' in W.get_data(as_text=True)
        W = self.tc.get('/Character/Dirichlet/?conductor=17&modulus=10-20&is_primitive=yes')
        assert '17.e' in W.get_data(as_text=True)

    def test_contradictory_search(self):
        # Searches that provably have no results are answered without
        # scanning the table; see issues #6733 and #6422
        queries = ['order=3&parity=odd',  # odd order forces even parity
                   'order=3,5&parity=odd',  # the same, as a comma separated list
                   'order=3&parity=odd&is_primitive=yes&is_real=no',
                   'is_real=yes&order=5',  # real characters have order at most 2
                   'is_real=yes&order=3,5',
                   'is_real=no&order=1-2',
                   'modulus=100&conductor=17',  # conductor divides modulus
                   'modulus=17&conductor=17&is_primitive=no',
                   'conductor=17&modulus=18-20&is_primitive=yes',
                   'inducing=3.b&order=3',  # 3.b has order 2
                   'inducing=3.b&order=3,5',
                   'inducing=3.b&parity=even',  # 3.b is odd
                   'inducing=3.b&is_real=no',  # 3.b is real
                   'inducing=3.b&conductor=5',  # induced characters have conductor 3
                   'inducing=3.b&conductor=5,7']
        for q in queries:
            W = self.tc.get('/Character/Dirichlet/?' + q)
            data = W.get_data(as_text=True)
            assert 'This search returns no results because' in data, q
            assert 'No matches' in data, q

    def test_no_results_search_modes(self):
        # A search with no results must behave in every search mode; the
        # count is fetched by an ajax call that should not leave a flashed
        # message behind for the next page the user visits.
        self.tc.get('/Character/Dirichlet/')  # display any pending message
        W = self.tc.get('/Character/Dirichlet/?order=3,5&parity=odd&result_count=1')
        assert W.json == {'nres': '0'}
        W = self.tc.get('/Character/Dirichlet/?modulus=35')
        assert 'This search returns no results because' not in W.get_data(as_text=True)
        W = self.tc.get('/Character/Dirichlet/?order=3,5&parity=odd&search_type=Random')
        data = W.get_data(as_text=True)
        assert 'This search returns no results because' in data
        assert 'No matches' in data

    def test_inducing_search(self):
        W = self.tc.get('/Character/Dirichlet/?inducing=3.b&modulus=1-100')
        data = W.get_data(as_text=True)
        assert '6.b' in data and '15.c' in data
        # compatible constraints on inherited quantities are harmless
        W = self.tc.get('/Character/Dirichlet/?inducing=3.b&modulus=1-100&order=2&parity=odd&is_real=yes')
        assert '15.c' in W.get_data(as_text=True)

    def test_nextprev(self):
        W = self.tc.get('/Character/Dirichlet/?start=200&count=25&order=3')
        assert r'288.i' in W.get_data(as_text=True)
        W = self.tc.get('/Character/Dirichlet/?start=100&count=25&order=3')
        assert r'169.c' in W.get_data(as_text=True)


class DirichletSearchQueryTest(LmfdbTest):
    """
    The searches below are rewritten by the parser using mathematical
    relations between the search columns, so that postgres is not asked to
    filter a large part of the table on a sparse boolean (issues #6733 and
    #6422).  These tests check the rewritten query itself: the page a search
    produces does not show whether the boolean was removed, which is the
    point of the rewriting.
    """

    # a query that provably has no results is replaced by this one, which is
    # answered instantly from the hash index on label
    no_results = {'label': ''}

    def parsed(self, query_string):
        """The database query that a search url is turned into."""
        query = {}
        with self.app.test_request_context():
            common_parse(dict(parse_qsl(query_string)), query)
        return query

    def labels(self, query):
        return set(db.char_dirichlet.search(query, projection='label'))

    def test_real_becomes_an_order_constraint(self):
        # a character is real if and only if its order is at most 2, and
        # there is no index on is_real
        assert self.parsed('is_real=yes') == {'order': {'$lte': 2}}
        assert self.parsed('is_real=no') == {'order': {'$gte': 3}}
        assert self.parsed('is_real=yes&order=1-100') == {'order': {'$gte': 1, '$lte': 2}}
        assert self.parsed('is_real=no&order=1-100') == {'order': {'$gte': 3, '$lte': 100}}
        assert self.parsed('conductor=17&is_real=yes') == {'conductor': 17, 'order': {'$lte': 2}}
        assert self.parsed('is_real=yes&order=5') == self.no_results
        assert self.parsed('is_real=no&order=1-2') == self.no_results
        # comma separated orders are stored in $or branches
        assert self.parsed('is_real=yes&order=3,5') == self.no_results
        assert self.parsed('is_real=yes&order=2,3') == {'order': 2}

    def test_odd_order_forces_even_parity(self):
        assert self.parsed('order=3&parity=odd') == self.no_results
        assert self.parsed('order=3,5&parity=odd') == self.no_results
        assert self.parsed('order=2,3&parity=odd') == {'order': 2, 'is_even': False}
        # asking for even parity is redundant once the order is odd
        assert self.parsed('order=3&parity=even') == {'order': 3}
        assert self.parsed('order=3,5&parity=even') == {'$or': [{'order': 3}, {'order': 5}]}
        # both parities occur in order 2
        assert self.parsed('order=2&parity=odd') == {'order': 2, 'is_even': False}

    def test_inducing_order(self):
        # 3.b has order 2, and induces characters of order 2 and conductor 3
        induced = {'conductor': 3, 'primitive_orbit': 2, 'order': 2}
        assert self.parsed('inducing=3.b') == induced
        assert self.parsed('inducing=3.b&order=1-2,5') == induced
        assert self.parsed('inducing=3.b&order=3,5') == self.no_results
        assert self.parsed('inducing=3.b&conductor=5,7') == self.no_results

    def test_primitive_mirrors_conductor_and_modulus(self):
        assert self.parsed('conductor=17&is_primitive=yes') == {'conductor': 17, 'modulus': 17}
        assert self.parsed('modulus=61&is_primitive=yes') == {'conductor': 61, 'modulus': 61}
        assert self.parsed('conductor=17&modulus=10-20&is_primitive=yes') == {'conductor': 17, 'modulus': 17}
        assert self.parsed('conductor=17&modulus=18-20&is_primitive=yes') == self.no_results
        assert self.parsed('conductor=17,61&is_primitive=yes') == {
            'is_primitive': True,
            '$or': [{'conductor': 17, 'modulus': 17}, {'conductor': 61, 'modulus': 61}]}

    def test_rewritten_searches_agree(self):
        # each rewritten query must select exactly the characters that the
        # boolean predicate it replaces would have selected
        def small(**kwds):
            return dict({'modulus': {'$gte': 1, '$lte': 40}}, **kwds)
        for query_string, unrewritten in [
                ('modulus=1-40&is_real=yes', small(is_real=True)),
                ('modulus=1-40&is_real=no&order=1-100',
                 small(is_real=False, order={'$gte': 1, '$lte': 100})),
                ('modulus=1-40&order=2,3&parity=odd',
                 small(is_even=False, **{'$or': [{'order': 2}, {'order': 3}]})),
                ('modulus=1-40&order=3,5&parity=even',
                 small(is_even=True, **{'$or': [{'order': 3}, {'order': 5}]})),
                ('modulus=1-40&is_primitive=yes', small(is_primitive=True)),
                ('conductor=17&modulus=1-1000&is_real=yes',
                 {'conductor': 17, 'modulus': {'$gte': 1, '$lte': 1000}, 'is_real': True})]:
            found = self.labels(self.parsed(query_string))
            assert found and found == self.labels(unrewritten), query_string


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
