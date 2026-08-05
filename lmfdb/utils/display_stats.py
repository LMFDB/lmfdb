from collections import defaultdict
from urllib.parse import quote

from flask import url_for
from sage.all import UniqueRepresentation, lazy_attribute, infinity

from .utilities import format_percentage, flash_error
from .web_display import display_knowl
from psycodict.utils import KeyedDefaultDict, SearchParsingError, range_formatter

# Included in a drill-down url by a query formatter when the value being counted
# cannot be expressed as a search: a not-computed (NULL) value for example.
# ``display_data`` shows the count of such a cell without a link, rather than
# linking to a search that returns the wrong records (an empty url parameter is
# ignored by the search parsers, so it would return everything).  A NUL byte
# cannot occur in a url, which makes the marker unambiguous, and it is a url
# fragment in its own right, so it survives the intersection that ``totaler``
# uses to build the link for a row or column total.
NO_SEARCH_QUERY = "\x00"

# Characters left alone when a search box value is copied into a drill-down url.
# Brackets, commas and slashes are common in LMFDB search input and are safe in a
# query string; everything else that is special (notably '&', '=', '#', '%', '+'
# and spaces) is escaped.
URL_SAFE = "[](),/:"

def _hashable(val):
    """
    A hashable canonical form of a value as stored in the database, used to match
    up the counts returned by the statistics backend with the rows and columns of
    the table being displayed.  Distinct values always get distinct keys, unlike
    the strings produced by the formatters.
    """
    if isinstance(val, dict):
        return ("$dict",) + tuple((key, _hashable(val[key])) for key in sorted(val))
    elif isinstance(val, (list, tuple)):
        return ("$list",) + tuple(_hashable(x) for x in val)
    return val

class StatHeader():
    """
    One row or column of a statistics table.

    Separating the three roles of a value keeps drill-down links correct even
    when displaying a value loses information: ``label`` is shown to the user,
    ``keys`` are used to look up counts, and ``fragment`` constrains a search to
    this value and is built from the value as stored in the database.

    INPUT:

    - ``label`` -- the string displayed as the header
    - ``value`` -- a value taken on by the column, as stored in the database
      (or the bucket string, for a bucketed column)
    - ``key`` -- the key under which the statistics backend stores counts for ``value``
    - ``fragment`` -- url fragment(s) constraining a search to ``value``
    """
    def __init__(self, label, value, key, fragment):
        self.label = label
        self.value = value
        self.keys = [key]
        self.fragment = fragment

    def add(self, key, fragment):
        """
        Include another value in this header.

        Two values that display identically have to share a row, since the user
        cannot tell them apart; their counts are added.  A link is only shown if
        they also constrain the search in the same way, since a search for the
        union of two values usually cannot be expressed.
        """
        self.keys.append(key)
        if fragment != self.fragment:
            self.fragment = NO_SEARCH_QUERY

    def count(self, data, other=None):
        """
        The number of rows with this value (and ``other``'s value, in the 2d case),
        given the ``data`` returned by the statistics backend.
        """
        if other is None:
            keys = self.keys
        else:
            keys = [(key, okey) for key in self.keys for okey in other.keys]
        # data is a KeyedDefaultDict, so we must avoid looking up absent keys
        return sum(data[key]["count"] for key in keys if key in data)

class formatters():
    @classmethod
    def boolean(cls, value):
        return 'True' if value else 'False'

    @classmethod
    def yesno(cls, value):
        return 'yes' if value else 'no'

    @classmethod
    def boolean_unknown(cls, value):
        if value == 1:
            return 'True'
        elif value == -1:
            return 'False'
        else:
            return 'Unknown'

def _format_percentage(cnt, total, show_zero=False):
    """
    Variant of format_percentage that returns blanks for 0 and includes the % sign.
    """
    if total == 0 or (cnt == 0 and not show_zero):
        return ""
    else:
        return format_percentage(cnt, total) + '%'

class proportioners():
    ##################################################################
    #                     Proportion strategies                      #
    ##################################################################
    # We collect functions for computing proportions for 2-d         #
    # statistics grids.  To use them, include them in an item on the #
    # stat_list in the ``proportioner`` field.                       #
    # Some are parameterized (eg taking a query as a static input).  #
    # Each takes as input                                            #
    #   * a grid (list of lists) of dictionaries giving counts       #
    #   * a list giving unformatted row headers                      #
    #   * a list giving unformatted row headers                      #
    #   * a StatsDisplay                                             #
    # and modifies the grid to include proportions                   #
    ##################################################################

    @classmethod
    def per_total(cls, grid, row_headers, col_headers, stats):
        total = sum(D['count'] for row in grid for D in row)
        for row in grid:
            for D in row:
                D['proportion'] = _format_percentage(D['count'], total)

    @classmethod
    def per_row_total(cls, grid, row_headers, col_headers, stats):
        """
        Total is determined as the sum of the current row.
        """
        for row in grid:
            total = sum(D['count'] for D in row)
            for D in row:
                D['proportion'] = _format_percentage(D['count'], total)

    @classmethod
    def per_row_query(cls, query):
        """
        Total is determined by row, given by the result of a query based on the row header.

        Warning: this will execute a database query for each row in the grid.

        INPUT:

        - ``query`` -- a function that takes in the row header
            and returns a dictionary for input to the ``count`` method.

        OUTPUT:

        A function for use as a proportioner.
        """
        def inner(grid, row_headers, col_headers, stats):
            for row, header in zip(grid, row_headers):
                total = stats._tmp_table.count(query(header))
                for D in row:
                    D['proportion'] = _format_percentage(D['count'], total)
        return inner

    @classmethod
    def per_col_total(cls, grid, row_headers, col_headers, stats):
        """
        Total is determined as the sum of the current column.
        """
        cls.per_row_total(list(zip(*grid)), col_headers, row_headers, stats)

    @classmethod
    def per_col_query(cls, query):
        """
        Total is determined by column, given by the result of a query based on the column header.

        Warning: this will execute a database query for each column in the grid.

        INPUT:

        - ``query`` -- a function that takes in the column header
            and returns a dictionary for input to the ``count`` method.

        OUTPUT:

        A function for use as a proportioner.
        """
        def inner(grid, row_headers, col_headers, stats):
            cls.per_row_query(query)(list(zip(*grid)), col_headers, row_headers, stats)
        return inner

    @classmethod
    def per_grid_query(cls, query):
        """
        Total is determined by a query determined by both row and column headers.

        Warning: this will execute a database query for each cell in the grid.

        INPUT:

        - ``query`` -- a function that takes in the row and column headers and returns
            a dictionary for input to the ``count`` method.

        OUTPUT:

        A function for use as a proportioner.
        """
        def inner(grid, row_headers, col_headers, stats):
            for row, row_head in zip(grid, row_headers):
                for D, col_head in zip(row, col_headers):
                    total = stats._tmp_table.count(query(row_head, col_head))
                    D['proportion'] = _format_percentage(D['count'], total)
        return inner

    @classmethod
    def per_grid_recurse(cls, attr):
        """
        Total is determined by a recursive call to display_data,
        with ``constraint`` and ``proportioner`` removed.

        INPUT:

        - ``attr`` -- a dictionary, as in the ``StatsDisplay.stats_list``.

        OUTPUT:

        A function for use as a proportioner.
        """
        attr = dict(attr)
        attr['base_url'] = '' # urls aren't used below
        attr['constraint'] = {}
        attr['link_constraint'] = None
        attr['proportioner'] = False
        attr['totaler'] = False

        def inner(grid, row_headers, col_headers, stats):
            total_data = stats.display_data(**attr)
            total_grid = total_data['grid']
            total_cols = total_data['col_headers']
            # Row headers have been zipped into the grid
            total_rows = [r[0] for r in total_grid]
            total_grid = [r[1] for r in total_grid]
            # Align the total_grid with our grid
            col_positions = [total_cols.index(col) for col in col_headers]
            row_positions = [total_rows.index(row) for row in row_headers]
            total_grid = [[total_grid[i][j] for j in col_positions] for i in row_positions]
            # make the total_grid available to totalers
            stats._total_grid = total_grid
            for row, trow in zip(grid, total_grid):
                for D, tD in zip(row, trow):
                    D['proportion'] = _format_percentage(D['count'], tD['count'])
        return inner

    ##################################################################
    #              1-d Proportioner/Totaler strategies               #
    ##################################################################
    # In 1-d, the function takes just headers as input, rather than  #
    # both row and column headers.                                   #
    ##################################################################

    @classmethod
    def recurse_1d(cls, attr):
        attr = dict(attr)
        attr['base_url'] = ''
        attr['constraint'] = None
        attr['link_constraint'] = None
        attr['proportioner'] = False
        attr['totaler'] = False

        def inner(counts, headers, stats):
            total_counts = stats.display_data(**attr)['counts']
            for D, tD in zip(counts, total_counts):
                D['proportion'] = _format_percentage(D['count'], tD['count'], show_zero=True)
        return inner

    @classmethod
    def ratio_1d(cls, query):
        def inner(counts, headers, stats):
            if query is not None:
                stats._overall = stats._tmp_table.count(query)
            # Otherwise stats._overall was set by display_data()
            overall = stats._overall
            for D in counts:
                D['proportion'] = _format_percentage(D['count'], overall, show_zero=True)
        return inner

class totaler():
    ##################################################################
    #                     Totaler strategies                         #
    ##################################################################
    # We collect functions for computing totals for 2-d              #
    # statistics grids.  To use them, include them in an item on the #
    # stat_list in the ``totaler`` field.                            #
    # Some are parameterized (eg options for including proportions). #
    # Each takes as input                                            #
    #   * a grid (list of lists) of dictionaries giving counts       #
    #   * a list giving unformatted row headers                      #
    #   * a list giving unformatted row headers                      #
    #   * a StatsDisplay                                             #
    # and modifies the grid to include proportions                   #
    ##################################################################

    @classmethod
    def common_link(cls, link_list):
        """
        Takes a nonempty list of links to search pages and returns the link with search options
        the intersection of the search options.  The initial part of the link must be the same for all.

        The options are kept in the order they appear in the first link, so that
        the same table always produces the same urls.
        """
        def _split(link):
            H, T = link.split('?')
            return H, [frag for frag in T.split('&') if frag]
        head, tail = _split(link_list[0])
        common = set(tail)
        for link in link_list[1:]:
            H, T = _split(link)
            if H != head:
                raise ValueError("Cannot vary main url")
            common.intersection_update(T)
        seen = set()
        fragments = [frag for frag in tail
                     if frag in common and not (frag in seen or seen.add(frag))]
        return head + '?' + '&'.join(fragments)

    def __init__(self, row_counts=True, row_proportions=True, col_counts=True, col_proportions=True, corner_count=None, corner_proportion=None, include_links=True, row_total_label='Total', col_total_label='Total'):
        if corner_count and not (row_counts and col_counts):
            raise ValueError
        if corner_count is None:
            corner_count = (row_counts and col_counts)
        self.row_counts = row_counts
        self.row_proportions = row_proportions
        self.col_counts = col_counts
        self.col_proportions = col_proportions
        self.corner_count = corner_count
        self.corner_proportion = corner_proportion
        self.include_links = include_links
        self.row_total_label = row_total_label
        self.col_total_label = col_total_label

    def __call__(self, grid, row_headers, col_headers, stats):
        if not grid or not grid[0]:
            # No cells to total, which happens when no statistics are available
            return
        row_counts = self.row_counts
        row_proportions = self.row_proportions
        col_counts = self.col_counts
        col_proportions = self.col_proportions
        corner_count = self.corner_count
        corner_proportion = self.corner_proportion
        include_links = self.include_links
        row_total_label = self.row_total_label
        col_total_label = self.col_total_label

        num_cols = len(grid[0])
        recursive_prop = (stats._total_grid is not None)
        if corner_proportion is None:
            corner_prop = recursive_prop
        else:
            corner_prop = corner_proportion
        if corner_count or (row_proportions or col_proportions) and not recursive_prop:
            overall = sum(D['count'] for row in grid for D in row)
        if row_counts:
            col_headers.append(row_total_label)
            for i, row in enumerate(grid):
                total = sum(D['count'] for D in row)
                query = self.common_link([D['query'] for D in row]) if include_links else None
                if query is not None and query[-1] == '?':
                    # No search options are common to the whole row, so a link
                    # would return every record rather than the ones counted
                    query = None
                if recursive_prop:
                    overall = sum(D['count'] for D in stats._total_grid[i])
                    if corner_count:
                        # Make the sums available for the column proportions
                        stats._total_grid[i].append({'count':overall})
                proportion = _format_percentage(total, overall) if col_proportions else ''
                D = {'count':total, 'query':query, 'proportion':proportion, 'extraclass':'totalcol', 'propclass':'totalcol'}
                row.append(D)
        if col_counts:
            row_headers.append(col_total_label)
            if recursive_prop:
                total_grid_cols = list(zip(*stats._total_grid))
            row = []
            for i, col in enumerate(zip(*grid)):
                # We've already totaled rows, so have to skip if we don't want the corner
                if i == num_cols:
                    if not corner_count:
                        break
                    extraclasses = {'extraclass': 'totalcorner', 'propclass': 'totalcol'}
                else:
                    extraclasses = {'extraclass': 'totalrow'}
                total = sum(elt['count'] for elt in col)
                if total == 0:
                    query = None
                else:
                    query = self.common_link([elt['query'] for elt in col if elt['count'] > 0]) if include_links else '?'
                    if query[-1] == '?': # no common search queries
                        query = None
                if recursive_prop:
                    overall = sum(D['count'] for D in total_grid_cols[i])
                proportion = _format_percentage(total, overall) if (col_proportions and i != num_cols or corner_prop and i == num_cols) else ''
                D = {'count':total, 'query':query, 'proportion':proportion}
                D.update(extraclasses)
                row.append(D)
            grid.append(row)
        #if corner_count and row_counts and not col_counts:
        #    # Have to add the corner specially
        #    row_headers.append(col_total_label)
        #    row = [{'count':'', 'query':None, 'proportion':''} for _ in range(num_cols)]
        #    query = self.common_link([r[-1]['query'] for r in grid]) if include_links else '?'
        #    if query[-1] == '?':
        #        query = None
        #    if recursive_prop:
        #        # We've stored the row sums in the last entries of grid and _total_grid
        #        total = sum(r[-1]['count'] for r in grid)
        #        if corner_prop:
        #            overall = sum(r[-1]['count'] for r in stats._total_grid)
        #    else:
        #        total = overall
        #    proportion = _format_percentage(total,overall) if corner_prop else ''
        #    D = {'count':total, 'query':query, 'proportion':proportion}
        #    row.append(D)
        #    grid.append(row)

def default_sort_key(val):
    if val is None:
        return -infinity
    return val

class StatsDisplay(UniqueRepresentation):
    """
    A class for displaying statistics in a uniform way.

    It is used in conjunction with the display_stats.html template.
    You should inherit from this class, providing

    - a ``summary`` attribute, which is displayed at the top of the page
    - a ``table`` attribute, which is a PostgresTable
    - a ``stat_list`` attribute, which is a list of
      dictionaries with the following keys (optional except ``cols``):

      - ``cols`` -- a list of columns to analyze.
      - ``constraint`` -- a query dictionary, giving constraints on the items included.
      - ``buckets`` -- a dictionary with columns as keys and list of strings such as '2-10' as values.
      - ``table`` -- a PostgresStatsTable containing the columns.
      - ``top_title`` -- a list of pairs (text, knowl) for the header of this statistics block.
          Defaults to zipping the contents of the ``top_title`` and ``knowls`` dictionaries (described below).
      - ``avg`` -- whether to display the average (1d only, default False)
      - ``totaller`` -- When ``cols`` has length 1 (1d case), a query for determining the
          denominator on proportions.  Defaults to the number of rows in the table
          where the columns are non-null.  When ``cols`` has length 2 (2d case),
          a function that adds row/column totals to the grid (see examples above).
      - ``proportioner`` -- A function that adds proportions to the grid (2d only, see examples above).
      - ``url_extras`` -- text to add to the urls after the '?'.
      - ``title_joiner`` -- Text used to join the ``top_title`` list.  Defaults to ' ' or ' and ', depending on whether every text is paired with a knowl.
      - ``intro`` -- Text displayed after the title of this stat block.

    You can also set defaults for many options by adding the following attributes, each of which should be a dictionary with column names as keys.

      - ``top_titles`` -- strings as values. Text to be displayed in titles, paired with knowls.
      - ``knowls`` -- strings as values.  Id for the knowl associated to this column.
      - ``short_display`` -- strings as values.  Text to be displayed as a row label.
      - ``buckets`` -- lists of strings as values.  For dividing values up into intervals
          when there are too many for individual display.  Entries should be either single
          values or ranges like '2-10'.
      - ``formatters`` -- callables as values.  Input a database value or bucket,
          output the text to display in the header.
      - ``query_formatters`` -- callables as values.  Input a database value or bucket,
          output the text to insert into the url, such as 'level=2-10'.  The input is
          never the output of a formatter, so a formatter is free to produce TeX or
          html that could not be parsed as search input.  Return ``NO_SEARCH_QUERY``
          for a value that cannot be searched for, such as a value that is not
          computed; its count is then displayed without a link.
      - ``bucket_encoders`` -- callables as values.  Input an endpoint of a bucket, as
          typed into the search box for that column, output the corresponding value
          to compare against the database.  Needed for a column whose database
          representation does not sort in the same way as the values shown to users.
      - ``url_params`` -- lists of strings as values.  The parameters of the search
          page that constrain this column, if they are not just the column name.
          Used to avoid constraining a column that is being displayed.
      - ``sort_keys`` -- callables as values.  Custom sorting for this column (as in ``sorted``)
      - ``reverses`` -- boolean values.  Whether to reverse the order of the header (as in ``sorted``)
      - ``split_lists`` -- boolean values.  Whether to count entries from lists individually.
          For example, a column with value [2,4,8] would increment the count of 2, 4 and 8
          rather than [2,4,8].  An example is cm_discs in classical modular forms.


    This object is then passed into the display_stats.html template as ``info``.
    """
    @property
    def _formatters(self):
        A = defaultdict(lambda: range_formatter)
        A.update(getattr(self, 'formatters', {}))
        return A

    @property
    def _query_formatters(self):
        def default_qformatter(col):
            return lambda x: '{0}={1}'.format(col, self._formatters[col](x))
        A = KeyedDefaultDict(default_qformatter)
        A.update(getattr(self, 'query_formatters', {}))
        return A

    @property
    def _buckets(self):
        A = defaultdict(lambda: None)
        A.update(getattr(self, 'buckets', {}))
        return A

    @property
    def _bucket_encoders(self):
        A = defaultdict(lambda: None)
        A.update(getattr(self, 'bucket_encoders', {}))
        return A

    @property
    def _url_params(self):
        A = KeyedDefaultDict(lambda col: [col])
        A.update(getattr(self, 'url_params', {}))
        return A

    @property
    def _dynamic_cols(self):
        return [('none', 'None')] + [(col, self._short_display[col]) for col in self.dynamic_cols]

    @property
    def _default_buckets(self):
        return [(col, ','.join(self._buckets.get(col, []))) for col, label in self._dynamic_cols]

    @property
    def _sort_keys(self):
        # We want None (unknown) to show up at the beginning
        A = defaultdict(lambda: default_sort_key)
        A.update(getattr(self, 'sort_keys', {}))
        return A

    @property
    def _reverses(self):
        A = defaultdict(bool)
        A.update(getattr(self, 'reverses', {}))
        return A

    @property
    def _top_titles(self):
        def _default(col):
            rtitle = self._short_display[col]
            if rtitle and rtitle[-1] != 's':
                return rtitle + 's'
            else:
                return rtitle
        A = KeyedDefaultDict(_default)
        A.update(getattr(self, 'top_titles', {}))
        return A

    @property
    def _short_display(self):
        A = KeyedDefaultDict(lambda col: col.replace('_', ' '))
        A.update(getattr(self, 'short_display', {}))
        return A

    @property
    def _knowls(self):
        A = defaultdict(lambda: None)
        A.update(getattr(self, 'knowls', {}))
        return A

    @property
    def _split_lists(self):
        A = defaultdict(bool)
        A.update(getattr(self, 'split_lists', {}))
        return A

    # It's useful to have info.stats access this object for both dynamic and static stats
    @property
    def stats(self):
        return self

    def _bucket_endpoints(self, bucket):
        """
        Split a bucket into its endpoints, using the same syntax as the statistics
        backend: '2' is a single value, '2-10' a closed range and '10-' a range
        unbounded above.

        OUTPUT:

        A pair (endpoints, rebuild), where ``rebuild`` reassembles a bucket from a
        list of endpoints of the same length.
        """
        if bucket[-1] == '-':
            return [bucket[:-1]], (lambda L: L[0] + '-')
        elif '-' not in bucket[1:]:
            return [bucket], (lambda L: L[0])
        elif bucket[0] == '-':
            # a negative lower endpoint, as in '-10-5'
            L = bucket[1:].split('-')
            L[0] = '-' + L[0]
        else:
            L = bucket.split('-')
        if len(L) != 2:
            raise SearchParsingError("%s is not a single value or a range such as 2-10." % bucket)
        return L, (lambda L: '%s-%s' % tuple(L))

    def _encode_buckets(self, buckets):
        """
        Rewrite bucket strings into the form used to compare against the database.

        This is the identity for a column with no entry in ``bucket_encoders``,
        which covers every column whose database representation sorts in the same
        way as the values shown to users.
        """
        encoded = {}
        for col, bucket_list in buckets.items():
            encoder = self._bucket_encoders[col]
            if encoder is None:
                encoded[col] = bucket_list
                continue
            encoded[col] = elist = []
            for bucket in bucket_list:
                endpoints, rebuild = self._bucket_endpoints(bucket)
                endpoints = [encoder(endpoint) for endpoint in endpoints]
                if any('-' in endpoint for endpoint in endpoints):
                    raise ValueError("Bucket encoder for %s produced a '-'" % col)
                elist.append(rebuild(endpoints))
        return encoded

    def _bucket_key(self, bucket):
        """
        The key under which the statistics backend stores the counts for a bucket.

        It normalizes a range with equal endpoints, since the backend stores such
        a bucket as a single value.
        """
        endpoints, _ = self._bucket_endpoints(bucket)
        if len(endpoints) == 2 and endpoints[0] == endpoints[1]:
            return endpoints[0]
        return bucket

    def _make_headers(self, col, values, buckets):
        """
        Assemble the headers for the rows or columns of a statistics table.

        INPUT:

        - ``col`` -- the column being displayed
        - ``values`` -- the values it takes on, as stored in the database
          (ignored when the column is bucketed)
        - ``buckets`` -- the list of buckets for this column, or None if it is not bucketed

        OUTPUT:

        A list of ``StatHeader`` objects, in the order they should be displayed.
        """
        formatter = self._formatters[col]
        query_formatter = self._query_formatters[col]
        if buckets is None:
            # Distinct values can display the same way, so deduplicate on the values
            # themselves, keeping one of each to build the header and its links from
            distinct = {}
            for val in values:
                distinct.setdefault(_hashable(val), val)
            pairs = sorted(distinct.items(), key=lambda kv: self._sort_keys[col](kv[1]),
                           reverse=self._reverses[col])
        else:
            encoded = self._encode_buckets({col: buckets})[col]
            pairs = [(self._bucket_key(bucket), public)
                     for public, bucket in zip(buckets, encoded)]
        headers = []
        by_label = {}
        for key, val in pairs:
            label = formatter(val)
            fragment = query_formatter(val)
            if label in by_label:
                by_label[label].add(key, fragment)
            else:
                by_label[label] = header = StatHeader(label, val, key, fragment)
                headers.append(header)
        return headers

    @staticmethod
    def _total_url(base_url, extras, table, cols, constraint, total, buckets, split_list):
        """
        The url for the total of a one-dimensional table, or the empty string when
        the records it counts cannot be described by a search.

        The only aggregate a search page can express here is the constraint itself,
        which is the right one exactly when every record satisfying the constraint
        is included in the total.  That fails in four ways:

        - a total over buckets covers only the buckets displayed, which need not
          exhaust the column, and a union of buckets is not a search anyway;
        - a total over a column whose lists are split counts the entries of those
          lists rather than records;
        - the statistics backend leaves out records where the column is null, so a
          column that is not computed for every record is totalled over only some
          of them;
        - a constraint on the column being displayed is left out of the urls, since
          each cell constrains that column itself, so the total would claim more
          records than it counted.

        The column name on its own used to be appended as a marker, but an empty
        parameter is ignored by the search parsers, so such a link silently
        returned every record rather than the ones counted (and the parameter is
        often not one the search page accepts, as with galois_label and gal).
        """
        constraint = constraint or {}
        if buckets or split_list or any(col in constraint for col in cols):
            return ''
        if total != table.table.count(constraint):
            # Some records have no value in this column, and no search selects
            # exactly the ones that do
            return ''
        return base_url + '&'.join(extras)

    @staticmethod
    def _suppress_unsearchable(data):
        """
        Blank the url of any cell whose value cannot be searched for, so that its
        count is displayed without a link.
        """
        def fix(cells):
            for cell in cells:
                if cell.get('query') and NO_SEARCH_QUERY in cell['query']:
                    cell['query'] = ''
        fix(data.get('counts', []))
        for _row_header, row in data.get('grid', []):
            fix(row)
        return data

    def display_data(self, cols, table=None, constraint=None, avg=None,
                     buckets=None, totaler=None, proportioner=None,
                     baseurl_func=None, url_extras=None, link_constraint=None, **kwds):
        """
        Returns statistics data in a common format that is used by page templates.

        INPUT:

        - ``table`` -- a ``PostgresStatsTable``
        - ``cols`` -- a list of column names
        - ``constraint`` -- a dictionary giving constraints on other columns.
            Only rows satisfying those constraints are included in the counts.
        - ``avg`` -- whether to include the average value of cols[0]
            (cols must be of length 1 with no bucketing)
        - ``buckets`` -- a dictionary whose keys are columns, and whose values are lists of strings such as '5' or '2-7'.
        - ``totaler`` -- (1d-case) a query giving the denominator for the proportions.
                      -- (2d-case) a function taking inputs the grid, row headers, col headers
                         and this object, which adds some totals to the grid
        - ``proportioner`` -- a function for adding proportions
            See examples at the top of display_stats.py.
        - ``baseurl_func`` -- a base url, to which url_for is applied and then col=value tags are appended.
            Defaults to the url for ``self.baseurl_func``.
        - ``url_extras`` -- Text to add to the url after the '?'.
        - ``link_constraint`` -- url fragments expressing ``constraint`` in terms of
            the search page's parameters, used in place of ``constraint`` when
            building urls.  Needed when the query used for counting is not in terms
            of the columns accepted by the search page.
        - ``kwds`` -- used to discard unused extraneous arguments.

        OUTPUT:

        A dictionary.

        In the 1d case, it has one key, ``counts``, with value a list of dictionaries, each with four keys:

        - ``value`` -- a tuple of values taken on by the given columns.
        - ``count`` -- The number of rows with that tuple of values.
        - ``query`` -- a url resulting in a list of entries with the given tuple of values.
        - ``proportion`` -- the fraction of rows having this tuple of values,
          as a string formatted as a percentage.

        In the 2d case, it has two keys, ``grid`` and ``col_headers``:

        - ``grid`` is a list of pairs, the first being a row header and the second
          being a list of dictionaries as above.
        - ``col_headers`` is a list of column headers.
        """
        if isinstance(cols, str):
            cols = [cols]
        if buckets is None:
            buckets = {col: self._buckets[col] for col in cols if self._buckets[col]}
        elif isinstance(buckets, list):
            if len(cols) == 1:
                buckets = {cols[0]: buckets}
            else:
                raise ValueError("buckets should be a dictionary with columns as keys")
        else:
            buckets = {col: buckets[col] for col in cols if col in buckets}
        if any(col not in cols for col in buckets):
            raise ValueError("Bucket keys must be a subset of columns")
        buckets = {col: [bucket for bucket in bucket_list if bucket]
                   for col, bucket_list in buckets.items()}
        buckets = {col: bucket_list for col, bucket_list in buckets.items() if bucket_list}
        if baseurl_func is None:
            baseurl_func = self.baseurl_func
        base_url = url_for(baseurl_func) + '?'
        # Url fragments shared by every cell of the table.  Each cell's url is
        # assembled from these together with the fragments for its row and column,
        # so that a totaler can recover the constraint on a row or column by
        # intersecting the urls of its cells.
        extras = [frag for frag in (url_extras or '').split('&') if frag]
        if link_constraint is not None:
            extras.extend(frag for frag in link_constraint.split('&') if frag)
        elif constraint:
            extras.extend(self._query_formatters[col](val)
                          for col, val in constraint.items() if col not in cols)

        def cell_url(*headers):
            return base_url + '&'.join(extras + [header.fragment for header in headers])

        if table is None:
            table = self.table
        self._tmp_table = table = table.stats
        # The backend indexes its counts by the output of ``formatter``, so we give
        # it functions that are injective on database values rather than the ones
        # used for display, which may not be.  Urls are built here instead, from the
        # values themselves, so we do not ask it to build any.
        keyer = {col: (range_formatter if col in buckets else _hashable) for col in cols}
        no_urls = KeyedDefaultDict(lambda col: (lambda val: ''))
        db_buckets = self._encode_buckets(buckets)

        if len(cols) == 1:
            avg = totaler.get('avg', False) if totaler else False
            show_total = bool(totaler)
            col = cols[0]
            split_list = self._split_lists[col]
            if buckets and (split_list or avg):
                raise ValueError("Unsupported option")
            values, data = table._get_values_counts(cols, constraint, split_list=split_list, formatter=keyer, query_formatter=no_urls, base_url='', buckets=db_buckets)
            headers = self._make_headers(col, values, buckets.get(col))
            counts = [{'count': header.count(data),
                       'query': cell_url(header),
                       'proportion': "      0.00%",  # overridden below for nonzero counts
                       'value': header.label}
                      for header in headers]
            if 'addl_row_title' in kwds:
                addl_row_title = kwds['addl_row_title']
                for D, header in zip(counts, headers):
                    D['value2'] = self._formatters[addl_row_title](header.value)
            if show_total or proportioner is None:
                if buckets:
                    total = sum(D['count'] for D in counts)
                else:
                    total, avg = table._get_total_avg(cols, constraint, avg, split_list)
                self._overall = total
            if proportioner is None or isinstance(proportioner, dict):
                proportioner = proportioners.ratio_1d(proportioner)
            if proportioner:
                proportioner(counts, [header.label for header in headers], self)
            else:
                for D in counts:
                    D['proportion'] = ''
            if show_total:
                total = {'count': total,
                         'query': self._total_url(base_url, extras, table, cols, constraint,
                                                  total, buckets, split_list),
                         'proportion':_format_percentage(total, self._overall, show_zero=True)}
                if avg is False: # Want to show avg even if 0
                    total['value'] = 'Total'
                else:
                    total['value'] = r'\(\mathrm{avg}\ %.2f\)' % avg
                counts.append(total)
            return self._suppress_unsearchable({'counts': counts})
        elif len(cols) == 2:
            if avg:
                raise ValueError("unsupported option")
            values, data = table._get_values_counts(cols, constraint, split_list=False, formatter=keyer, query_formatter=no_urls, base_url='', buckets=db_buckets)
            rows = self._make_headers(cols[0], values[0], buckets.get(cols[0]))
            columns = self._make_headers(cols[1], values[1], buckets.get(cols[1]))
            grid = [[{'count': row.count(data, column),
                      'query': cell_url(row, column),
                      'proportion': ''}
                     for column in columns] for row in rows]
            row_headers = [row.label for row in rows]
            col_headers = [column.label for column in columns]
            # _total_grid is used for recursive proportions; such proportioners
            # will set it for use in a totaler.  Otherwise, we set it to None
            # here to signal that unrecursive totaling should be used.
            self._total_grid = None
            if proportioner:
                proportioner(grid, row_headers, col_headers, self)
            if totaler:
                totaler(grid, row_headers, col_headers, self)
            return self._suppress_unsearchable({'grid': list(zip(row_headers, grid)),
                                                'col_headers': col_headers})
        elif not cols:
            return {}
        else:
            raise NotImplementedError

    def prep(self, attr):
        if isinstance(attr['cols'], str):
            attr['cols'] = [attr['cols']]
        cols = attr['cols']
        # default value for top_title from row_title/columns
        if 'top_title' not in attr:
            top_title = [(self._top_titles[col], self._knowls[col]) for col in cols]
        else:
            top_title = attr['top_title']
        if not isinstance(top_title, str):
            missing_knowl = any(knowl is None for text, knowl in top_title)
            joiner = attr.get('title_joiner', ' ' if missing_knowl else ' and ')
            attr['top_title'] = joiner.join((display_knowl(knowl, title=title) if knowl else title)
                                            for title, knowl in top_title)
        attr['hash'] = hsh = hex(abs(hash(attr['top_title'])))[2:]
        data = self.display_data(**attr)
        attr['intro'] = attr.get('intro',[])
        data['attribute'] = attr
        # issue when no constraints are included yet
        if len(cols) == 0:
            return data
        if 'row_title' not in attr:
            attr['row_title'] = self._short_display[cols[0]]
        if len(cols) == 1:
            max_rows = attr.get('max_rows',6)
            counts = data['counts']
            rows = [counts[i:i+10] for i in range(0, len(counts), 10)]
            if len(rows) > max_rows:
                short_rows = rows[:max_rows]
                data['divs'] = [(short_rows, "short_table_" + hsh, "short"),
                                (rows, "long_table_" + hsh + " nodisplay", "long")]
            else:
                data['divs'] = [(rows, "short_table", "none")]
        elif len(cols) == 2:
            if 'col_title' not in attr:
                attr['col_title'] = self._short_display[cols[1]]
        return data

    @lazy_attribute
    def distributions(self):
        return [self.prep(attr) for attr in self.stat_list]

    def setup(self, attributes=None, delete=False):
        """
        This function can be called manually at the Sage prompt to add
        the appropriate data to the stats table

        Warning: if delete is True and an entry in the stat_list includes the 'table' attribute,
        stats and counts from that table will also be deleted.
        """
        if attributes is None:
            attributes = self.stat_list
        if delete:
            self.table.stats._clear_stats_counts()
            for attr in attributes:
                if 'table' in attr:
                    attr['table'].stats._clear_stats_counts()
        for attr in attributes:
            cols = attr["cols"]
            if not cols:
                continue
            if isinstance(cols, str):
                cols = [cols]
            buckets = attr.get('buckets', {col: self._buckets[col] for col in cols if self._buckets[col]})
            if isinstance(buckets, list) and len(cols) == 1:
                buckets = {cols[0]: buckets}
            buckets = self._encode_buckets(buckets)
            constraint = attr.get("constraint")
            table = attr.get("table", self.table)
            split_list = all(self._split_lists[col] for col in cols)
            if buckets:
                if split_list:
                    raise ValueError("split_list not supported with buckets")
                table.stats.add_bucketed_counts(cols, buckets, constraint)
            else:
                table.stats.add_stats(cols, constraint, split_list=split_list)

    def _dyn_attribute_parse(self, info, attributes):
        """
        Sets the 'cols' and 'buckets' entries of an ``attributes`` dictionary
        based on the contents of the ``info`` dictionary.
        """
        cols = []
        buckets = {}
        totals = []
        for cname, bname, tname in [('col1', 'buckets1', 'totals1'), ('col2', 'buckets2', 'totals2')]:
            if cname in info and info[cname] != 'none':
                col = info[cname]
                if col in cols:
                    raise ValueError("Cannot repeat")
                cols.append(col)
                if bname in info:
                    cur_buckets = info[bname].replace(' ','')
                    if cur_buckets:
                        buckets[col] = cur_buckets.split(',')
                totals.append(info.get(tname, False))
        attributes['cols'] = cols
        attributes['buckets'] = buckets
        prop = info.get('proportions')
        if len(cols) == 1:
            if totals[0]:
                attributes['totaler'] = {'avg':False}
            if prop == 'recurse':
                attributes['proportioner'] = proportioners.recurse_1d(attributes)
        elif len(cols) == 2:
            attributes['totaler'] = totaler(row_counts=totals[0], col_counts=totals[1])
            if prop == 'recurse':
                attributes['proportioner'] = proportioners.per_grid_recurse(attributes)
            elif prop == 'rows':
                attributes['proportioner'] = proportioners.per_row_total
            elif prop == 'cols':
                attributes['proportioner'] = proportioners.per_col_total
        if prop == 'none':
            attributes['proportioner'] = False

    # Parameters of the dynamic statistics page itself, rather than of the search
    # that determines which records are counted.
    dynamic_params = ['col1', 'col2', 'buckets1', 'buckets2', 'totals1', 'totals2',
                      'proportions', 'search_type', 'search_array', 'count', 'start',
                      'hst', 'err', 'd', 'stats']

    def dynamic_link_constraint(self, info, cols):
        """
        The url fragments constraining the drill-down links on the dynamic
        statistics page to the records being counted.

        We echo back the search boxes that the user filled in, rather than the
        query that ``dynamic_parse`` produced from them, since the columns of that
        query are often not parameters that the search page accepts: a search box
        may be renamed, combined with a quantifier, or encoded before being
        compared with the database.  The search boxes reproduce the same search by
        construction, being the input that produced the query in the first place.
        """
        skip = set(self.dynamic_params)
        for col in cols:
            skip.update(self._url_params[col])
        return "&".join("%s=%s" % (key, quote(val, safe=URL_SAFE))
                        for key, val in info.items()
                        if key not in skip and isinstance(val, str) and val)

    def dynamic_setup(self, info):
        if not info:
            info["d"] = self.prep({'cols':[], 'buckets':{}})
        else:
            try:
                # parse the constraint
                constraint = {}
                self.dynamic_parse(info, constraint)
                attr = {'constraint': constraint}
                # add in the columns and proportioner+totaller strategies
                self._dyn_attribute_parse(info, attr)
                # the same constraint, in terms of the search page's parameters
                attr['link_constraint'] = self.dynamic_link_constraint(info, attr['cols'])
                info["d"] = self.prep(attr)
            except (ValueError, AttributeError, TypeError) as err:
                # These are the errors raised for invalid search input.  The search
                # parsers flash their own message, and set info['err'] when they have.
                if "err" not in info:
                    flash_error("%s", str(err))
                    info["err"] = ""
                # Show the search form and the error message, without any table
                info["d"] = self.prep({'cols':[], 'buckets':{}})
        info["stats"] = self
        info["get_bucket"] = (lambda i: info.get("buckets%s" % i, ""))
        info["get_col"] = (lambda i: info.get("col%s" % i, "none"))
        info["get_total"] = (lambda i: info.get("totals%s" % i, False))
        info["search_type"] = "DynStats"
