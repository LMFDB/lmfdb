from lmfdb.tests import LmfdbTest


class StubTable():
    """
    Stands in for a table and its statistics backend, with a controlled set of
    counts, so that tests of the statistics framework do not depend on which
    statistics happen to be cached in the database.

    INPUT:

    - ``counts`` -- the counts, as a dictionary from tuples of stored values, or
      as a list of (tuple of stored values, count) pairs when those values are
      unhashable (a bucketed column is stored as a range)
    - ``records`` -- the number of records satisfying the constraint, which
      exceeds the total when the column is not computed for some of them.
      Defaults to the number counted.
    """
    def __init__(self, counts, records=None):
        self.counts = list(counts.items() if isinstance(counts, dict) else counts)
        self.records = records
        # the same object serves as the table, its statistics and its counts
        self.stats = self.table = self

    def _get_values_counts(self, cols, constraint, split_list, formatter,
                           query_formatter, base_url, buckets=None):
        from psycodict.utils import KeyedDefaultDict
        headers = [[] for _ in cols]
        data = KeyedDefaultDict(lambda key: {'count': 0, 'query': '', 'proportion': ''})
        for values, cnt in self.counts:
            for val, header in zip(values, headers):
                header.append(val)
            key = tuple(formatter[col](val) for col, val in zip(cols, values))
            data[key if len(cols) > 1 else key[0]] = {'count': cnt, 'query': '', 'proportion': ''}
        return (headers, data) if len(cols) > 1 else (headers[0], data)

    def _get_total_avg(self, cols, constraint, avg, split_list):
        # as in psycodict, records where the column is null are left out
        return sum(cnt for values, cnt in self.counts if values[0] is not None), False

    def count(self, query):
        if self.records is not None:
            return self.records
        return sum(cnt for _values, cnt in self.counts)


class LocalFieldTest(LmfdbTest):

    # All tests should pass
    #
    def test_search_ramif_cl_deg(self):
        L = self.tc.get('/padicField/?n=8&c=24&gal=8T5&p=2&e=8&count=20')
        assert '4 matches' in L.get_data(as_text=True)

    def test_search_f(self):
        L = self.tc.get('/padicField/?n=6&p=2&f=3')
        dat = L.get_data(as_text=True)
        assert '2.2.3.4a1.1' not in dat
        assert '2.3.2.6a1.2' in dat

    def test_search_top_slope(self):
        L = self.tc.get('/padicField/?p=2&topslope=3.5')
        assert '2.1.4.9a1.1' in L.get_data(as_text=True) # number of matches
        L = self.tc.get('/padicField/?p=2&topslope=3.4..3.55')
        assert '2.1.4.9a1.1' in L.get_data(as_text=True) # number of matches
        L = self.tc.get('/padicField/?p=2&topslope=7/2')
        assert '2.1.4.9a1.1' in L.get_data(as_text=True) # number of matches

    def test_stats_pages(self):
        # The browse page and statistics page link to dynamic statistics
        L = self.tc.get('/padicField/')
        assert 'dynamic_stats' in L.get_data(as_text=True)
        L = self.tc.get('/padicField/stats')
        dat = L.get_data(as_text=True)
        assert 'create your own' in dat and 'dynamic_stats' in dat

    def test_dynamic_stats(self):
        # A combination whose statistics are precomputed: degree x ramification index for p=2
        # (there are 6 totally ramified quadratic extensions of Q_2)
        L = self.tc.get('/padicField/dynamic_stats?p=2&col1=n&totals1=yes&col2=e&proportions=rows&search_type=DynStats')
        dat = L.get_data(as_text=True)
        assert 'n=2&amp;e=2' in dat and '>6<' in dat
        # Galois groups for p=2, n=4 (also precomputed); 12 of the 59 quartic
        # 2-adic fields are cyclic
        L = self.tc.get('/padicField/dynamic_stats?p=2&n=4&col1=galois_label&proportions=none&search_type=DynStats')
        dat = L.get_data(as_text=True)
        assert 'C_4' in dat and '>12<' in dat
        # All column options render (values for most combinations are computed and
        # cached on demand, so against a read-only database the tables may be empty,
        # but the pages should not error)
        for col in ['p', 'n', 'e', 'f', 'c', 'galois_label', 'aut', 'u', 't', 'top_slope',
                    'slopes', 'visible', 'hidden', 'ind_of_insep', 'associated_inertia', 'jump_set']:
            L = self.tc.get('/padicField/dynamic_stats?col1=%s&proportions=recurse&search_type=DynStats' % col)
            assert L.status_code == 200
            other = 'p' if col == 'n' else 'n'
            L = self.tc.get('/padicField/dynamic_stats?col1=%s&col2=%s&totals1=yes&totals2=yes&proportions=rows&search_type=DynStats' % (col, other))
            assert L.status_code == 200

    def test_dynamic_stats_null_query_formatters(self):
        # Not-computed / empty values have no search representation, so their
        # query_formatters return the NO_SEARCH_QUERY sentinel and the drill-down link
        # is suppressed rather than pointing at an unfiltered search (LMFDB#6542).
        from lmfdb.local_fields.main import (
            LFStats, NO_SEARCH_QUERY, galquery, bracket_query, content_query,
            nullable_int_query, formatbracketcol, topslope_query)
        # Null / empty -> sentinel; genuine values -> a real search fragment
        assert galquery(None) == NO_SEARCH_QUERY
        assert galquery('1T1') == 'gal=1T1'
        assert nullable_int_query('u')(None) == NO_SEARCH_QUERY
        assert nullable_int_query('u')(2) == 'u=2'
        assert bracket_query('associated_inertia')(None) == NO_SEARCH_QUERY
        assert bracket_query('associated_inertia')([1, 2]) == 'associated_inertia=[1, 2]'
        # an empty jump set is searchable, unlike one that is not computed
        assert bracket_query('jump_set')([]) == 'jump_set=[]'
        cq = content_query('slopes', 'slopes_quantifier')
        assert cq(None) == NO_SEARCH_QUERY and cq([]) == NO_SEARCH_QUERY and cq('[]') == NO_SEARCH_QUERY
        assert cq('[2, 2]') == 'slopes=[2, 2]&slopes_quantifier=exactly'
        assert LFStats.query_formatters['hidden'](None) == NO_SEARCH_QUERY
        assert LFStats.query_formatters['hidden']('') == NO_SEARCH_QUERY
        assert topslope_query(None) == NO_SEARCH_QUERY
        # None array columns render as "not computed", never a literal $None$ (P3)
        assert formatbracketcol(None) == 'not computed'
        assert formatbracketcol('') == 'not computed'
        assert formatbracketcol([]) == r'$[\ ]$'
        assert formatbracketcol([1, 2]) == '$[1, 2]$'
        # a not-computed jump set and an empty one are distinct values, so they must
        # not share a row of the table under one ambiguous label
        assert LFStats.formatters['jump_set'](None) != LFStats.formatters['jump_set']([])
        # and the empty one is a search that works, so its count stays linked
        from lmfdb import db
        assert self._url_count('/padicField/?jump_set=[]') == db.lf_fields.count({'jump_set': []})
        # display_data blanks a sentinel-bearing drill-down while keeping real ones
        base = '/padicField/?'
        data = {'counts': [
            {'value': 'not computed', 'count': 5, 'query': base + NO_SEARCH_QUERY},
            {'value': 'C_4', 'count': 7, 'query': base + 'gal=4T1'}]}
        LFStats._suppress_unsearchable(data)
        assert data['counts'][0]['query'] == ''
        assert data['counts'][1]['query'] == base + 'gal=4T1'
        grid = {'grid': [('C_4', [
            {'count': 1, 'query': base + 'gal=4T1&' + NO_SEARCH_QUERY},
            {'count': 2, 'query': base + 'gal=4T1&e=2'}])]}
        LFStats._suppress_unsearchable(grid)
        assert grid['grid'][0][1][0]['query'] == ''
        assert grid['grid'][0][1][1]['query'] == base + 'gal=4T1&e=2'

    def test_dynamic_stats_null_bucket(self):
        # A not-computed Galois group (3996 fields) cannot be expressed as a search, so
        # its statistics bucket is shown without a drill-down link -- clicking it must
        # not open an unfiltered search returning every field (LMFDB#6542 review).
        import re
        empty_link = re.compile(r"href='[^']*[?&][A-Za-z_]+=(?:&amp;|')")
        for col, param in [('galois_label', 'gal'), ('slopes', 'slopes'), ('hidden', 'hidden')]:
            L = self.tc.get('/padicField/dynamic_stats?col1=%s&proportions=none&search_type=DynStats' % col)
            assert L.status_code == 200
            dat = L.get_data(as_text=True)
            assert 'not computed' in dat                  # the null bucket is displayed...
            assert "?%s='" % param not in dat             # ...with no empty-parameter link
            assert empty_link.search(dat) is None         # no drill-down has an empty value
            assert '\x00' not in dat                       # the sentinel never leaks to output
        # Non-null buckets still link to a correctly-filtered search (12 cyclic quartics)
        L = self.tc.get('/padicField/dynamic_stats?p=2&n=4&col1=galois_label&proportions=none&search_type=DynStats')
        dat = L.get_data(as_text=True)
        assert 'gal=4T1' in dat and empty_link.search(dat) is None

    ############################################################################
    # Drill-down links on the dynamic statistics page must describe exactly the
    # records that were counted.  The helpers below read the table off the page
    # and count what each link actually selects, by running its parameters
    # through the same parser the search page uses.
    ############################################################################

    @staticmethod
    def _stat_rows(dat):
        """The rows of a 2d statistics table, as (header, [(count, url), ...])."""
        import re
        dat = dat.replace('&amp;', '&')
        rows = []
        for header, body in re.findall(r'<th class="rhead nowrap" rowspan=2>(.*?)</th>(.*?)</tr>', dat, re.S):
            cells = [(int(cnt) if cnt else 0, url) for url, cnt in
                     re.findall(r"<td class=\"cnt[^\"]*\">(?:<a href='([^']*)'>)?(\d*)", body)]
            rows.append((re.sub('<[^>]*>', '', header).strip(), cells))
        return rows

    @staticmethod
    def _stat_counts(dat):
        """
        The counts of a 1d statistics table, as (label, count, url).

        Such a table is transposed: a row of values, then the row of counts
        underneath it, for each block of ten values.
        """
        import re
        dat = dat.replace('&amp;', '&')
        counts, labels = [], None
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', dat, re.S):
            head = re.match(r'\s*<th[^>]*>(.*?)</th>', row, re.S)
            if head is None:
                continue
            title = re.sub('<[^>]*>', '', head.group(1)).strip()
            cells = row[head.end():]
            if title == 'count':
                for label, (url, cnt) in zip(labels or [], re.findall(
                        r"<td>(?:<a href='([^']*)'>)?(\d+)(?:</a>)?</td>", cells)):
                    counts.append((label, int(cnt), url))
                labels = None
            elif title != 'proportion' and labels is None:
                labels = [re.sub('<[^>]*>', '', cell).strip()
                          for cell in re.findall(r'<td>(.*?)</td>', cells, re.S)]
        return counts

    def _url_count(self, url):
        """How many fields the search page returns for a drill-down url."""
        from urllib.parse import urlparse, parse_qsl
        from lmfdb import db
        from lmfdb.local_fields.main import common_parse
        from lmfdb.utils import to_dict
        parsed = urlparse(url)
        assert parsed.path == '/padicField/', url
        info = to_dict(dict(parse_qsl(parsed.query, keep_blank_values=True)))
        query = {}
        with self.app.test_request_context():
            common_parse(info, query)
            # the search page flashes an error and sets 'err' for input it rejects
            assert 'err' not in info, "search page rejects %s" % url
        return db.lf_fields.count(query)

    def test_dynamic_stats_2d_links(self):
        # In a sparse grid, the cells with no fields must constrain the search the
        # same way the nonempty ones do, so that intersecting the cells of a row
        # leaves the row's own constraint in the total's link (LMFDB#6542 review).
        L = self.tc.get('/padicField/dynamic_stats?p=2&col1=galois_label&col2=n&totals1=yes&proportions=none&search_type=DynStats')
        assert L.status_code == 200
        rows = self._stat_rows(L.get_data(as_text=True))
        assert rows, "no statistics available for Galois group by degree"
        sparse = 0
        for header, cells in rows:
            counts, total = cells[:-1], cells[-1]
            if not any(cnt for cnt, _ in counts) or all(cnt for cnt, _ in counts):
                continue  # not a sparse row
            sparse += 1
            label = header.split('as ')[1].rstrip(')')  # eg '$C_4$ (as 4T1)' -> '4T1'
            # the cells with fields in them constrain both the group and the degree
            for cnt, url in counts:
                if cnt:
                    assert 'gal=%s' % label in url and 'n=' in url, (header, url)
                    assert '$' not in url and '<' not in url, url
            # the total is over the whole row, empty cells included, so its link
            # keeps the group but not any one degree
            assert 'gal=%s' % label in total[1] and 'n=' not in total[1], (header, total)
            assert total[0] == sum(cnt for cnt, _ in counts)
            if sparse <= 3:
                assert self._url_count(total[1]) == total[0], total
        assert sparse >= 10, "expected a sparse grid, found %s sparse rows" % sparse

    def test_dynamic_stats_2d_zero_cell_urls(self):
        # The same invariant, checked directly on display_data so that it does not
        # depend on which statistics happen to be cached in the database.  The
        # formatter for slopes produces TeX, which is not valid search input, so an
        # empty cell built from the displayed value rather than the stored one is
        # visibly wrong (and its row's total would lose the constraint entirely).
        from lmfdb.local_fields.main import LFStats
        from lmfdb.utils import totaler

        # slopes [2] occurs only in degree 2, and is not computed for some fields
        table = StubTable({('[2]', 2): 5, ('[2, 2]', 4): 7, ('[2, 2]', 8): 3, (None, 2): 11})
        with self.app.test_request_context('/padicField/'):
            data = LFStats().display_data(
                cols=['slopes', 'n'], table=table, proportioner=False,
                totaler=totaler(row_counts=True, col_counts=False))
        grid = dict(data['grid'])
        assert data['col_headers'] == ['2', '4', '8', 'Total']
        # the empty cells of the [2] row carry the same slopes constraint as its
        # nonempty cell, built from the stored value rather than the displayed one
        row = grid['$[2]$']
        assert [D['count'] for D in row] == [5, 0, 0, 5]
        for D, n in zip(row, [2, 4, 8]):
            assert D['query'] == '/padicField/?slopes=[2]&slopes_quantifier=exactly&n=%s' % n
        assert row[-1]['query'] == '/padicField/?slopes=[2]&slopes_quantifier=exactly'
        # a row spanning two degrees keeps only the row constraint in its total
        assert [D['count'] for D in grid['$[2, 2]$']] == [0, 7, 3, 10]
        assert grid['$[2, 2]$'][-1]['query'] == '/padicField/?slopes=[2, 2]&slopes_quantifier=exactly'
        # slopes that are not computed cannot be searched for, so neither the cells
        # of that row nor its total are linked
        assert [D['count'] for D in grid['not computed']] == [11, 0, 0, 11]
        assert all(D['query'] == '' for D in grid['not computed'])

    def test_dynamic_stats_1d_totals(self):
        # The Total of a one-dimensional table counts the fields where the column
        # is computed, which is not something the search page can ask for, so it is
        # only linked when that is every field matching the constraint.  Of the 3784
        # fields with p=7 and n=21, only 1324 have a computed Galois group.
        from lmfdb import db
        L = self.tc.get('/padicField/dynamic_stats?p=7&n=21&col1=galois_label'
                        '&totals1=yes&proportions=none&search_type=DynStats')
        assert L.status_code == 200
        counts = self._stat_counts(L.get_data(as_text=True))
        assert counts, "no statistics available for Galois groups with p=7, n=21"
        total = [c for c in counts if c[0] == 'Total']
        assert len(total) == 1, counts
        _label, count, url = total[0]
        assert count == db.lf_fields.count({'p': 7, 'n': 21, 'galois_label': {'$exists': True}})
        assert count < db.lf_fields.count({'p': 7, 'n': 21})
        assert url == '', url        # a link here would return the other 2460 too
        # where the column is computed for every field, the total is the constraint
        # itself, and is linked
        L = self.tc.get('/padicField/dynamic_stats?p=2&n=8&col1=galois_label'
                        '&totals1=yes&proportions=none&search_type=DynStats')
        counts = self._stat_counts(L.get_data(as_text=True))
        total = [c for c in counts if c[0] == 'Total'][0]
        assert total[2] and 'galois_label' not in total[2], total
        assert self._url_count(total[2]) == total[1] == db.lf_fields.count({'p': 2, 'n': 8})
        # a total over buckets covers only the buckets displayed, so it is not
        # linked, while the buckets themselves still are
        L = self.tc.get('/padicField/dynamic_stats?col1=top_slope&buckets1=0-1,1-2'
                        '&totals1=yes&proportions=none&search_type=DynStats')
        counts = self._stat_counts(L.get_data(as_text=True))
        assert [label for label, _cnt, _url in counts] == ['$0$-$1$', '$1$-$2$', 'Total']
        assert counts[-1][2] == '', counts
        assert [url for _label, _cnt, url in counts[:2]] == [
            '/padicField/?topslope=0-1', '/padicField/?topslope=1-2']

    def test_dynamic_stats_1d_totals_policy(self):
        # The same rule, on a controlled set of counts.  A column that is not
        # computed for every field, a total over part of the column, and a total
        # over the entries of lists rather than over fields all go unlinked.
        from lmfdb.local_fields.main import LFStats
        stats = LFStats()
        with self.app.test_request_context('/padicField/'):
            def total_of(table, **kwds):
                counts = stats.display_data(table=table, totaler={'avg': False},
                                            proportioner=False, **kwds)['counts']
                assert counts[-1]['value'] == 'Total'
                return counts[-1]['count'], counts[-1]['query']
            # every field has a Galois group here, so the total is the whole search
            assert total_of(StubTable({('4T1',): 5, ('4T3',): 11}), cols=['galois_label'],
                            link_constraint='p=2&n=4') == (16, '/padicField/?p=2&n=4')
            # here it is not computed for 11 of the 27, which no search expresses
            assert total_of(StubTable({('4T1',): 5, ('4T3',): 11, (None,): 11}, records=27),
                            cols=['galois_label'], link_constraint='p=2&n=4') == (16, '')
            # a total over buckets covers only the buckets shown
            assert total_of(StubTable([(({'$gte': 0, '$lte': 1},), 7),
                                       (({'$gte': 2, '$lte': 3},), 9)]),
                            cols=['c'], buckets={'c': ['0-1', '2-3']}) == (16, '')
            # a constraint on the column being displayed is left out of the urls,
            # since each count constrains that column itself, so the total would
            # describe more fields than it counted
            assert total_of(StubTable({(2,): 5, (4,): 11}), cols=['n'],
                            constraint={'p': 2, 'n': {'$lte': 4}},
                            link_constraint='p=2') == (16, '')
        # and a split-list total counts entries of lists rather than fields
        assert LFStats._total_url('/padicField/?', [], None, ['cm_discs'], {}, 16, {}, True) == ''

    def test_dynamic_stats_public_urls(self):
        # A constraint entered on the dynamic statistics page has to survive
        # clicking a count.  The parsed query uses internal columns (slopes_tmp and
        # friends) that the search page does not accept, so the links are built from
        # the search boxes instead, and must reproduce the same query (LMFDB#6542
        # review).
        from urllib.parse import urlparse, parse_qsl
        from lmfdb.local_fields.main import LFStats, common_parse
        from lmfdb.utils import to_dict
        constraints = [
            'slopes=[2, 2]&slopes_quantifier=exactly',
            'slopes=[2]&slopes_quantifier=include',
            'slopes=[2]&slopes_quantifier=exclude',
            'slopes=[2, 2]&slopes_quantifier=subset',
            'visible=[2]&visible_quantifier=exactly',
            'visible=[2]&visible_quantifier=include',
            'ind_of_insep=[1, 0]&insep_quantifier=exactly',
            'ind_of_insep=[1, 0]&insep_quantifier=subset',
            'topslope=1-2&p=2',
            'jump_set=[1]&associated_inertia=[1, 1]',
        ]
        stats = LFStats()
        for constraint in constraints:
            info = to_dict(dict(parse_qsl(constraint)))
            info.update({'col1': 'n', 'totals1': 'yes', 'search_type': 'DynStats'})
            query = {}
            with self.app.test_request_context():
                stats.dynamic_parse(info, query)
                link = stats.dynamic_link_constraint(info, ['n'])
                # the parameters of the link, parsed as the search page parses them
                reparsed_info = to_dict(dict(parse_qsl(link)))
                reparsed = {}
                common_parse(reparsed_info, reparsed)
                assert 'err' not in reparsed_info, (constraint, link)
            assert '_tmp' not in link, (constraint, link)
            assert '=None' not in link, (constraint, link)
            assert reparsed == query, (constraint, link, reparsed, query)
            # the quantifier is part of what the user asked for, so it is kept
            for key, val in parse_qsl(constraint):
                if key.endswith('quantifier'):
                    assert '%s=%s' % (key, val) in link, (constraint, link)
            # and every drill-down link is built from those fragments.  Statistics
            # for a constrained column are computed on demand, so the page itself
            # has nothing to show against a read-only database; the counts are
            # supplied here so that the check does not depend on the cache.
            with self.app.test_request_context('/padicField/'):
                counts = stats.display_data(cols=['n'], table=StubTable({(2,): 5, (4,): 7}),
                                            proportioner=False, link_constraint=link)['counts']
            assert [D['count'] for D in counts] == [5, 7]
            for D, n in zip(counts, [2, 4]):
                assert D['query'] == '/padicField/?%s&n=%s' % (link, n), (constraint, D['query'])
        # the pages themselves render, and never expose an internal column
        for constraint in constraints:
            url = ('/padicField/dynamic_stats?%s&col1=n&totals1=yes&proportions=none'
                   '&search_type=DynStats' % constraint)
            L = self.tc.get(url)
            assert L.status_code == 200, constraint
            dat = L.get_data(as_text=True)
            assert 'is not a valid input' not in dat, constraint
            assert '_tmp' not in dat and '=None' not in dat, constraint
            for _label, cnt, link in self._stat_counts(dat):
                if link:
                    assert urlparse(link).path == '/padicField/', link
                    if cnt:
                        assert self._url_count(link) == cnt, (constraint, link, cnt)

    def test_dynamic_stats_topslope_buckets(self):
        # top_slope is stored as a fixed-width decimal prefix followed by the exact
        # rational, so that the database sorts it numerically.  Bucket endpoints
        # must be encoded the same way before being compared, and decoded again for
        # display and for links (LMFDB#6542 review).
        import re
        from lmfdb import db
        from lmfdb.local_fields.main import ratproc
        url = ('/padicField/dynamic_stats?col1=top_slope&buckets1=0-1,1-2,2-'
               '&totals1=yes&proportions=none&search_type=DynStats')
        L = self.tc.get(url)
        assert L.status_code == 200
        dat = L.get_data(as_text=True)
        # the buckets are labeled and linked with exact rationals, not with the
        # encoding, and an endpoint is never dropped (which produced 'topslope=-')
        assert '$0$-$1$' in dat and '$1$-$2$' in dat and '$2$-' in dat
        assert '00.0000000000' not in dat and 'topslope=-' not in dat
        links = {h.replace('&amp;', '&') for h in re.findall(r"href='(/padicField/\?[^']*)'", dat)}
        assert {'/padicField/?topslope=0-1', '/padicField/?topslope=1-2',
                '/padicField/?topslope=2-'} <= links, sorted(links)
        # each bucket's link selects exactly the fields the bucket counts: the
        # comparison the statistics backend makes, on the encoded endpoints
        for bucket, query in [('0-1', {'$gte': ratproc('0'), '$lte': ratproc('1')}),
                              ('1-2', {'$gte': ratproc('1'), '$lte': ratproc('2')}),
                              ('2-', {'$gte': ratproc('2')})]:
            assert self._url_count('/padicField/?topslope=%s' % bucket) == db.lf_fields.count({'top_slope': query})
        # the counts shown agree too, wherever the statistics have been computed
        for label, cnt, link in self._stat_counts(dat):
            if cnt and link:
                assert self._url_count(link) == cnt, (label, link, cnt)
        # buckets compose with the two-dimensional grid and its totals
        L = self.tc.get('/padicField/dynamic_stats?col1=top_slope&buckets1=0-1,1-2,2-'
                        '&col2=n&totals1=yes&proportions=none&search_type=DynStats')
        assert L.status_code == 200
        for header, cells in self._stat_rows(L.get_data(as_text=True)):
            for cnt, link in cells:
                if link:
                    assert 'topslope=' in link and '00.00' not in link, (header, link)
        # an endpoint that is not a rational number is rejected with the usual
        # message, rather than silently counting nothing
        L = self.tc.get('/padicField/dynamic_stats?col1=top_slope&buckets1=0-junk&search_type=DynStats')
        assert L.status_code == 200
        assert 'not a non-negative rational number' in L.get_data(as_text=True)

    def test_dynamic_stats_bucket_coverage(self):
        # Every field has to land in some bucket, so the last bucket of each column
        # with defaults is unbounded above
        from lmfdb import db
        from lmfdb.local_fields.main import LFStats
        for col in LFStats.buckets:
            buckets = LFStats.buckets[col]
            assert buckets[-1].endswith('-'), (col, buckets)
            assert db.lf_fields.count({col: {'$lt': int(buckets[0])}}) == 0, col

    def test_field_page(self):
        L = self.tc.get('/padicField/11.6.4.2', follow_redirects=True)
        assert '11.2.3.4a1.1' in L.get_data(as_text=True)
        assert 'x^{2} + 7 x + 2' in L.get_data(as_text=True) # bad (not robust) test, but it's the best i was able to find...
        assert 'x^{3} + 44 t + 99' in L.get_data(as_text=True) # bad (not robust) test, but it's the best i was able to find...

    def test_global_splitting_models(self):
        # The first one will have to change if we compute a GSM for it
        L = self.tc.get('/padicField/163.1.8.7a1.2')
        assert 'not computed' in L.get_data(as_text=True)
        L = self.tc.get('/padicField/2.8.1.0a1.1')
        assert 'Does not exist' in L.get_data(as_text=True)

    def test_underlying_data(self):
        page = self.tc.get('/padicField/11.2.3.4a1.2').get_data(as_text=True)
        assert 'Underlying data' in page and 'data/11.2.3.4a1.2' in page

    def test_search_download(self):
        page = self.tc.get('/padicField/?Submit=gp&download=1&query=%7B%27p%27%3A+2%2C+%27n%27%3A+2%7D&n=2&p=2').get_data(as_text=True)
        assert '''columns = ["label", "coeffs", "p", "f", "e", "c", "gal", "slopes"];
data = {[
["2.2.1.0a1.1", [1, 1, 1], 2, 2, 1, 0, [2, 1], [[], 1, 2]],
["2.1.2.2a1.1", [2, 2, 1], 2, 1, 2, 2, [2, 1], [[2], 1, 1]],
["2.1.2.2a1.2", [6, 2, 1], 2, 1, 2, 2, [2, 1], [[2], 1, 1]],
["2.1.2.3a1.1", [2, 0, 1], 2, 1, 2, 3, [2, 1], [[3], 1, 1]],
["2.1.2.3a1.2", [10, 0, 1], 2, 1, 2, 3, [2, 1], [[3], 1, 1]],
["2.1.2.3a1.3", [2, 4, 1], 2, 1, 2, 3, [2, 1], [[3], 1, 1]],
["2.1.2.3a1.4", [10, 4, 1], 2, 1, 2, 3, [2, 1], [[3], 1, 1]]
]};

create_record(row) =
{
    out = Map(["label",row[1];"coeffs",row[2];"p",row[3];"f",row[4];"e",row[5];"c",row[6];"gal",row[7];"slopes",row[8]]);
    field = Polrev(mapget(out, "coeffs"));
    mapput(~out, "field", field);
    return(out);''' in page

    def test_families_search_download(self):
        # Absolute families: download should produce a file (not just refresh the page).  Issue #6829.
        r = self.tc.get('/padicField/?Submit=sage&download=1&query=%7B%27n0%27%3A+1%2C+%27p%27%3A+2%2C+%27n%27%3A+2%7D&p=2&n=2&search_type=Families')
        assert 'attachment' in r.headers.get('Content-Disposition', '')
        page = r.get_data(as_text=True)
        assert '"2.2.1.0a"' in page
        assert '"2.1.2.2a"' in page
        # Relative families: download should also work and include the base field label.
        r = self.tc.get('/padicField/?Submit=sage&download=1&query=%7B%27base%27%3A+%272.2.1.0a1.1%27%2C+%27n%27%3A+2%7D&n=2&base=2.2.1.0a1.1&relative=1&search_type=Families')
        assert 'attachment' in r.headers.get('Content-Disposition', '')
        page = r.get_data(as_text=True)
        assert '"2.2.1.0a1.1"' in page
