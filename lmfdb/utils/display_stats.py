
from collections import defaultdict

from flask import url_for
from sage.all import UniqueRepresentation, lazy_attribute

from lmfdb.utils.utilities import format_percentage, display_knowl, KeyedDefaultDict, range_formatter

class formatters(object):
    @classmethod
    def boolean(cls, value):
        return 'True' if value else 'False'

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

class proportioners(object):
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
                total = stats.count(query(header))
                for D in row:
                    D['proportion'] = _format_percentage(D['count'], total)
        return inner

    @classmethod
    def per_col_total(cls, grid, row_headers, col_headers, stats):
        """
        Total is determined as the sum of the current column.
        """
        cls.per_row_total(zip(*grid), col_headers, row_headers, stats)

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
            cls.per_row_query(query)(zip(*grid), col_headers, row_headers, stats)
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
                    total = stats.count(query(row_head, col_head))
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

class totaler(object):
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
        """
        def _split(link):
            H, T = link.split('?')
            T = set(T.split('&'))
            return H, T
        head, tails = _split(link_list[0])
        for link in link_list[1:]:
            H, T = _split(link)
            if H != head:
                raise ValueError("Cannot vary main url")
            tails.intersection_update(T)
        return head + '?' + '&'.join(tails)

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
        if not grid:
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
                if recursive_prop:
                    overall = sum(D['count'] for D in stats._total_grid[i])
                    if corner_count:
                        # Make the sums available for the column proportions
                        stats._total_grid[i].append({'count':overall})
                proportion = _format_percentage(total, overall) if col_proportions else ''
                D = {'count':total, 'query':query, 'proportion':proportion}
                row.append(D)
        if col_counts:
            row_headers.append(col_total_label)
            if recursive_prop:
                total_grid_cols = zip(*stats._total_grid)
            row = []
            for i, col in enumerate(zip(*grid)):
                # We've already totaled rows, so have to skip if we don't want the corner
                if not corner_count and i == num_cols:
                    break
                total = sum(elt['count'] for elt in col)
                query = self.common_link([elt['query'] for elt in col]) if include_links else '?'
                if query[-1] == '?': # no common search queries
                    query = None
                if recursive_prop:
                    overall = sum(D['count'] for D in total_grid_cols[i])
                proportion = _format_percentage(total, overall) if (col_proportions and i != num_cols or corner_prop and i == num_cols) else ''
                D = {'count':total, 'query':query, 'proportion':proportion}
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
      - ``query_formatters`` -- callables as values.  Input a database value or output of formatter,
          output the text to insert into the url, such as 'level=2-10'.
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
    def _dynamic_cols(self):
        return [('none', 'None')] + [(col, self._short_display[col].capitalize()) for col in self.dynamic_cols]

    @property
    def _default_buckets(self):
        return [(col, ','.join(self._buckets.get(col, []))) for col, label in self._dynamic_cols]

    @property
    def _sort_keys(self):
        A = defaultdict(lambda: None)
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

    def display_data(self, cols, table=None, constraint=None, avg=None, buckets = None, totaler=None, proportioner=None, base_url=None, url_extras=None, **kwds):
        """
        Returns statistics data in a common format that is used by page templates.

        INPUT:

        - ``table`` -- a ``PostgresStatsTable``
        - ``cols`` -- a list of column names
        - ``constraint`` -- a dictionary giving constraints on other columns.
            Only rows satsifying those constraints are included in the counts.
        - ``avg`` -- whether to include the average value of cols[0]
            (cols must be of length 1 with no bucketing)
        - ``buckets`` -- a dictionary whose keys are columns, and whose values are lists of strings such as '5' or '2-7'.
        - ``totaler`` -- (1d-case) a query giving the denominator for the proportions.
                      -- (2d-case) a function taking inputs the grid, row headers, col headers
                         and this object, which adds some totals to the grid
        - ``proprotioner`` -- a function for adding proportions
            See examples at the top of display_stats.py.
        - ``base_url`` -- a base url, to which col=value tags are appended.
            Defaults to the url for ``self.baseurl_func``.
        - ``url_extras`` -- Text to add to the url after the '?'.
        - ``kwds`` -- used to discard unused extraneous arguments.

        OUTPUT:

        A dictionary.

        In the 1d case, it has one key, ``counts``, with value a list of dictionaries, each with four keys.
        - ``value`` -- a tuple of values taken on by the given columns.
        - ``count`` -- The number of rows with that tuple of values.
        - ``query`` -- a url resulting in a list of entries with the given tuple of values.
        - ``proportion`` -- the fraction of rows having this tuple of values,
            as a string formatted as a percentage.

        In the 2d case, it has two keys, ``grid`` and ``col_headers``.

        - ``grid`` is a list of pairs, the first being a row header and the second
            being a list of dictionaries as above.
        - ``col_headers`` is a list of column headers.
        """
        if isinstance(cols, basestring):
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
        formatter = self._formatters
        query_formatter = self._query_formatters
        sort_key = self._sort_keys
        reverse = self._reverses
        if base_url is None:
            base_url = url_for(self.baseurl_func) + '?'
        if url_extras:
            base_url += url_extras
        if constraint:
            base_url += "".join("%s&" % query_formatter[col](val) for col, val in constraint.items())
        if table is None:
            table = self.table
        self._tmp_table = table = table.stats

        if len(cols) == 1:
            avg = totaler.get('avg', False) if totaler else False
            show_total = bool(totaler)
            col = cols[0]
            split_list = self._split_lists[col]
            headers, counts = table._get_values_counts(cols, constraint, split_list=split_list, formatter=formatter, query_formatter=query_formatter, base_url=base_url, buckets=buckets)
            if not buckets:
                if show_total or proportioner is None:
                    total, avg = table._get_total_avg(cols, constraint, avg, split_list)
                headers = [formatter[col](val) for val in sorted(headers, key=sort_key[col], reverse=reverse[col])]
            elif cols == buckets.keys():
                if split_list or avg or sort_key[col]:
                    raise ValueError("Unsupported option")
                headers = [formatter[col](bucket) for bucket in buckets[col]]
                if show_total or proportioner is None:
                    total = sum(counts[bucket]['count'] for bucket in headers)
            else:
                raise ValueError("Bucket keys must be subset of columns")
            counts = [counts[val] for val in headers]
            for D, val in zip(counts, headers):
                D['value'] = val
            if proportioner is None or show_total:
                self._overall = total
            if proportioner is None or isinstance(proportioner, dict):
                proportioner = proportioners.ratio_1d(proportioner)
            if proportioner:
                proportioner(counts, headers, self)
            else:
                for D in counts:
                    D['proportion'] = ''
            if show_total:
                total = {'count': total,
                         'query':"{0}{1}".format(base_url, cols[0]),
                         'proportion':_format_percentage(total, self._overall, show_zero=True)}
                if avg is False: # Want to show avg even if 0
                    total['value'] = 'Total'
                else:
                    total['value'] = '\(\\mathrm{avg}\\ %.2f\)'%avg
                counts.append(total)
            return {'counts': counts}
        elif len(cols) == 2:
            if avg:
                raise ValueError("unsupported option")
            non_buckets = [col for col in cols if col not in buckets]
            if len(buckets) + len(non_buckets) != 2:
                raise ValueError("Bucket keys must be a subset of columns")
            headers, grid = table._get_values_counts(cols, constraint, split_list=False, formatter=formatter, query_formatter=query_formatter, base_url=base_url, buckets=buckets)
            for i, col in enumerate(cols):
                if col in buckets:
                    headers[i] = [formatter[col](bucket) for bucket in buckets[col]]
                else:
                    headers[i] = [formatter[col](val) for val in
                                  sorted(set(headers[i]), key=sort_key[col], reverse=reverse[col])]
            row_headers, col_headers = headers
            grid = [[grid[(rw,cl)] for cl in col_headers] for rw in row_headers]
            # _total_grid is used for recursive proportions; such proportioners
            # will set it for use in a totaler.  Otherwise, we set it to None
            # here to signal that unrecursive totaling should be used.
            self._total_grid = None
            if proportioner:
                proportioner(grid, row_headers, col_headers, self)
            if totaler:
                totaler(grid, row_headers, col_headers, self)
            return {'grid': zip(row_headers, grid), 'col_headers': col_headers}
        elif len(cols) == 0:
            return {}
        else:
            raise NotImplementedError

    def prep(self, attr):
        if isinstance(attr['cols'], basestring):
            attr['cols'] = [attr['cols']]
        cols = attr['cols']
        # default value for top_title from row_title/columns
        if 'top_title' not in attr:
            top_title = [(self._top_titles[col], self._knowls[col]) for col in cols]
        else:
            top_title = attr['top_title']
        if not isinstance(top_title, basestring):
            missing_knowl = any(knowl is None for text, knowl in top_title)
            joiner = attr.get('title_joiner', ' ' if missing_knowl else ' and ')
            attr['top_title'] = joiner.join((display_knowl(knowl, title=title) if knowl else title)
                                            for title, knowl in top_title)
        attr['hash'] = hsh = hex(abs(hash(attr['top_title'])))[2:]
        data = self.display_data(**attr)
        attr['intro'] = attr.get('intro',[])
        data['attribute'] = attr
        if len(cols) == 1:
            attr['row_title'] = self._short_display[cols[0]]
            max_rows = attr.get('max_rows',6)
            counts = data['counts']
            rows = [counts[i:i+10] for i in range(0,len(counts),10)]
            if len(rows) > max_rows:
                short_rows = rows[:max_rows]
                data['divs'] = [(short_rows, "short_table_" + hsh, "short"),
                                (rows, "long_table_" + hsh + " nodisplay", "long")]
            else:
                data['divs'] = [(rows, "short_table", "none")]
        elif len(cols) == 2:
            attr['row_title'] = self._short_display[cols[0]]
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
            if isinstance(cols, basestring):
                cols = [cols]
            buckets = attr.get('buckets', {col: self._buckets[col] for col in cols if self._buckets[col]})
            if isinstance(buckets, list) and len(cols) == 1:
                buckets = {cols[0]: buckets}
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

    def dynamic_setup(self, info):
        if not info:
            attr = {'cols':[], 'buckets':{}}
        else:
            constraint = {}
            try:
                # parse the constraint
                self.dynamic_parse(info, constraint)
                attr = {'constraint': constraint}
                # add in the columns and proportioner+totaller strategies
                self._dyn_attribute_parse(info, attr)
            except Exception:
                # Should provide nice error message
                raise
        info["d"] = self.prep(attr)
        info["stats"] = self
        info["get_bucket"] = (lambda i: info.get("buckets%s"%i, ""))
        info["get_col"] = (lambda i: info.get("col%s"%i, "none"))
        info["get_total"] = (lambda i: info.get("totals%s"%i, False))
        info["search_type"] = "DynStats"
