from sage.all import UniqueRepresentation, lazy_attribute
from flask import url_for
from lmfdb.utils import format_percentage, display_knowl
from itertools import izip_longest

def boolean_format(value):
    return 'True' if value else 'False'

def boolean_unknown_format(value):
    if value == 1:
        return 'True'
    elif value == -1:
        return 'False'
    else:
        return 'Unknown'

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
#   * a PostgresStatsTable                                       #
# and modifies the grid to include proportions                   #
##################################################################

def _format_percentage(cnt, total):
    """
    Variant of format_percentage that returns blanks for 0.
    """
    if cnt == 0:
        return ""
    else:
        return format_percentage(cnt, total)

def per_row_total(grid, row_headers, col_headers, stats):
    """
    Total is determined as the sum of the current row.
    """
    for row in grid:
        total = sum(D['count'] for D in row)
        for D in row:
            D['proportion'] = _format_percentage(D['count'], total)

def per_row_query(query):
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

def per_col_total(grid, row_headers, col_headers, stats):
    """
    Total is determined as the sum of the current column.
    """
    per_row_total(zip(*grid), col_headers, row_headers, stats)

def per_col_query(query):
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
        per_row_query(query)(zip(*grid), col_headers, row_headers, stats)
    return inner

def per_grid_query(query):
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

def per_grid_recurse(attr):
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
    attr['constraint'] = None
    attr['proportioner'] = None
    def inner(grid, row_headers, col_headers, stats):
        _, total_grid = stats.display_data(**attr)
        for row, trow in zip(grid, total_grid):
            for D, tD in zip(row, trow):
                D['proportion'] = _format_percentage(D['count'], tD['count'])
    return inner

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
#   * a PostgresStatsTable                                       #
# and modifies the grid to include proportions                   #
##################################################################

def common_link(link_list):
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
    return head +'?' + '&'.join(tails)

def sum_totaler(row_counts=True, row_proportions=True, col_counts=True, col_proportions=True, corner_count=True, corner_proportion=False, include_links=True, row_total_label='Total', col_total_label='Total'):
    def inner(grid, row_headers, col_headers, stats):
        num_cols = len(grid[0])
        if row_proportions or col_proportions or corner_count:
            overall = sum(D['count'] for row in grid for D in row)
        if row_counts:
            col_headers.append(row_total_label)
            for row in grid:
                total = sum(D['count'] for D in row)
                query = common_link([D['query'] for D in row]) if include_links else None
                proportion = _format_percentage(total, overall) if col_proportions else ''
                D = {'count':total, 'query':query, 'proportion':proportion}
                row.append(D)
        if col_counts:
            row_headers.append(col_total_label)
            row = []
            for i, col in enumerate(zip(*grid)):
                # We've already totaled rows, so have to skip if we don't want the corner
                if not corner_count and i == num_cols:
                    break
                total = sum(D['count'] for D in col)
                query = common_link([D['query'] for D in col]) if include_links else '?'
                if query[-1] == '?': # no common search queries
                    query = None
                proportion = _format_percentage(total, overall) if (col_proportions and i != num_cols or corner_proportion and i == num_cols) else ''
                D = {'count':total, 'query':query, 'proportion':proportion}
                row.append(D)
            grid.append(row)
        if corner_count and row_counts and not col_counts:
            # Have to add the corner specially
            row = [{'count':'', 'query':None, 'proportion':''} for _ in range(num_cols)]
            query = common_link(row[-1]['query'] for row in grid) if include_links else '?'
            if query[-1] == '?':
                query = None
            proportion = _format_percentage(1,1) if corner_proportion else ''
            D = {'count':overall, 'query':query, 'proportion':proportion}
            row.append(D)
            grid.append(row)
    return inner

class StatsDisplay(UniqueRepresentation):
    """
    A class for displaying statistics in a uniform way.

    It is used in conjunction with the display_stats.html template.
    You should inherit from this class, providing

    - a ``summary`` attribute, which is displayed at the top of the page
    - a ``table`` attribute, which is a PostgresTable
    - a ``stat_list`` attribute, which is a list of
      dictionaries with the following keys:

      - ``cols`` -- a list of columns to analyze.
      - ``buckets`` -- (optional) a dictionary giving buckets.  See db_backend for more details.
      - ``top_title`` -- text to be displayed before the rows associated to these columns
      - ``row_title`` -- text to be displayed as a row label
      - ``knowl`` -- a knowl describing the attribute being analyzed
      - ``format`` -- (optional) a function to format the values from the database
      - ``avg`` -- (optional boolean, default False) whether to display the average

    This object is then passed into the display_stats.html template as ``info``.
    """
    @lazy_attribute
    def distributions(self):
        dists = []
        for attr in self.stat_list:
            if isinstance(attr['cols'], basestring):
                attr['cols'] = [attr['cols']]
            cols = attr['cols']
            # default value for top_title from row_title
            if 'top_title' not in attr:
                if len(cols) == 1:
                    top_title = attr['row_title']
                    if not top_title.endswith('s'):
                        top_title += 's'
                    top_title = [top_title]
                else:
                    top_title = [col.replace('_',' ') for col in cols]
            elif isinstance(attr['top_title'], basestring):
                top_title = [attr['top_title']]
            else:
                top_title = attr['top_title']
            if isinstance(attr['knowl'], basestring):
                knowls = [attr['knowl']]
            else:
                knowls = attr['knowl']
            joiner = attr.get('title_joiner', ' ' if None in knowls or len(knowls) < len(top_title) else ' and ')
            attr['top_title'] = joiner.join((display_knowl(knowl, title=title) if knowl else title)
                                            for knowl, title in izip_longest(knowls, top_title))
            attr['hash'] = hsh = hex(abs(hash(attr['top_title'])))[2:]
            attr['base_url'] = url_for(self.baseurl_func)
            table = attr.get('table',self.table)
            data = table.stats.display_data(**attr)
            attr['intro'] = attr.get('intro',[])
            if len(cols) == 1:
                max_rows = attr.get('max_rows',6)
                counts = data['counts']
                rows = [counts[i:i+10] for i in range(0,len(counts),10)]
                if len(rows) > max_rows:
                    short_rows = rows[:max_rows]
                    divs = [(short_rows, "short_table_" + hsh, "short"),
                            (rows, "long_table_" + hsh + " nodisplay", "long")]
                else:
                    divs = [(rows, "short_table", "none")]
                dists.append({'attribute':attr, 'divs':divs})
            elif len(cols) == 2:
                attr['corner_label'] = attr.get('corner_label',r'\({0} \backslash {1}\)'.format(*cols))
                data['attribute'] = attr
                dists.append(data)
        return dists

    def setup(self, delete=False):
        """
        This function should be called manually at the Sage prompt to add
        the appropriate data to the stats table.

        Warning: if delete is True and an entry in the stat_list includes the 'table' attribute,
        stats and counts from that table will also be deleted.
        """
        if delete:
            self.table.stats._clear_stats_counts(extra=False)
            for attr in self.stat_list:
                if 'table' in attr:
                    attr['table'].stats._clear_stats_counts(extra=False)
        for attr in self.stat_list:
            cols = attr["cols"]
            buckets = attr.get("buckets")
            # Deal with the length 1 shortcuts
            if isinstance(cols, basestring):
                cols = [cols]
            if isinstance(buckets, list) and len(cols) == 1:
                buckets = {cols[0]: buckets}
            constraint = attr.get("constraint")
            include_upper = attr.get("include_upper", True)
            table = attr.get("table", self.table)
            split_list = attr.get("split_list", False)
            if buckets:
                if split_list:
                    raise ValueError("split_list not supported with buckets")
                table.stats.add_bucketed_counts(cols, buckets, constraint, include_upper)
            else:
                table.stats.add_stats(cols, constraint, split_list=split_list)
