from math import gcd, sqrt
from unittest.mock import patch
from urllib.parse import parse_qsl

from lmfdb import db
from lmfdb.tests import LmfdbTest
from lmfdb.characters.main import common_parse
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


class DirichletSearchQueryTest(LmfdbTest):
    """
    The searches below are rewritten by the parser using mathematical
    relations between the search columns, so that postgres is not asked to
    filter a large part of the table on a sparse boolean (issues #6733 and
    #6422).  These tests check the rewritten query itself: the page a search
    produces does not show whether the boolean was removed, which is the
    point of the rewriting.

    The parser keeps the original query when its count is cached (see
    ``prefer_cached_count``), so ``parsed`` hides the count cache, which
    would otherwise make these tests depend on which counts are cached.
    """

    # a query that provably has no results is replaced by this one, which is
    # answered instantly from the hash index on label
    no_results = {'label': ''}

    def parsed(self, query_string, cached_count=None):
        """
        The database query that a search url is turned into, when the
        count of the original query is ``cached_count``.
        """
        query = {}
        with patch.object(db.char_dirichlet.stats, 'quick_count', return_value=cached_count):
            with self.app.test_request_context():
                common_parse(dict(parse_qsl(query_string)), query)
        return query

    def parsed_with_cache(self, query_string):
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
        # only the trivial character, of conductor 1, has order 1, so the
        # conductor pins down the order of a real character; a range on the
        # order would make postgres sort all the real characters of conductor 17
        assert self.parsed('conductor=17&is_real=yes') == {'conductor': 17, 'order': 2}
        assert self.parsed('conductor=2-&is_real=yes') == {'conductor': {'$gte': 2}, 'order': 2}
        assert self.parsed('conductor=1&is_real=yes') == {'conductor': 1, 'order': 1}
        assert self.parsed('conductor=1-17&is_real=yes') == {'conductor': {'$gte': 1, '$lte': 17}, 'order': {'$lte': 2}}
        assert self.parsed('conductor=17,61&is_real=yes') == {
            'order': {'$lte': 2},
            '$or': [{'conductor': 17, 'order': 2}, {'conductor': 61, 'order': 2}]}
        assert self.parsed('conductor=17&order=1&is_real=yes') == self.no_results
        assert self.parsed('conductor=1&order=2&is_real=yes') == self.no_results
        assert self.parsed('conductor=1,17&order=1&is_real=yes') == {'conductor': 1, 'order': 1}
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
                 {'conductor': 17, 'modulus': {'$gte': 1, '$lte': 1000}, 'is_real': True}),
                ('conductor=1,17&modulus=1-100&is_real=yes',
                 {'$or': [{'conductor': 1}, {'conductor': 17}],
                  'modulus': {'$gte': 1, '$lte': 100}, 'is_real': True})]:
            found = self.labels(self.parsed(query_string))
            assert found and found == self.labels(unrewritten), query_string

    def test_cached_counts_are_kept(self):
        # The statistics page links to searches whose counts are cached under
        # the query as parsed; rewriting them would lose the cached count, and
        # counting them is very slow.
        for query_string in ['modulus=100001-1000000&is_real=no',
                             'modulus=100001-1000000&is_primitive=yes',
                             'is_real=yes']:
            query = self.parsed_with_cache(query_string)
            assert db.char_dirichlet.stats.quick_count(query) is not None, query_string
        assert self.parsed('modulus=1-40&is_real=yes', cached_count=4) == {
            'modulus': {'$gte': 1, '$lte': 40}, 'is_real': True}
        assert self.parsed('modulus=17&is_primitive=yes', cached_count=4) == {
            'modulus': 17, 'is_primitive': True}
        # but constraints on the conductor are rewritten regardless, since
        # retrieving the results needs the rewritten query (issue #6733)
        assert self.parsed('conductor=17&is_primitive=yes', cached_count=4) == {
            'conductor': 17, 'modulus': 17}
        assert self.parsed('conductor=17,61&is_real=yes', cached_count=4)['order'] == {'$lte': 2}
        # and contradictions are still detected
        assert self.parsed('order=3&parity=odd', cached_count=0) == self.no_results


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
