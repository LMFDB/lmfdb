from sage.all import UniqueRepresentation, lazy_attribute
from flask import url_for

def boolean_format(value):
    return 'True' if value else 'False'

def boolean_unknown_format(value):
    if value == 1:
        return 'True'
    elif value == -1:
        return 'False'
    else:
        return 'Unknown'

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
            kwds = {}
            for key in ['constraint', 'avg', 'formatter', 'buckets', 'split_list', 'include_upper', 'query_formatter', 'sort_key', 'reverse', 'url_extras', 'denominator']:
                if key in attr:
                    kwds[key] = attr[key]
            # default value for top_title from row_title
            if 'top_title' not in attr:
                attr['top_title'] = attr['row_title']
                if not attr['top_title'].endswith('s'):
                    attr['top_title'] += 's'
            attr['hash'] = hsh = hex(abs(hash(attr['top_title'])))[2:]
            table = attr.get('table',self.table)
            counts = table.stats.display_data(attr["cols"], url_for(self.baseurl_func), **kwds)
            max_rows = attr.get('max_rows',6)
            rows = [counts[i:i+10] for i in range(0,len(counts),10)]
            short_rows = rows[:max_rows]
            if len(rows) > max_rows:
                divs = [("short_table_" + hsh, short_rows, "short"),
                        ("long_table_" + hsh + " nodisplay", rows, "long")]
            else:
                divs = [("short_table", rows, "none")]
            dists.append({'attribute':attr,'divs':divs})
        return dists

    def setup(self):
        """
        This function should be called manually at the Sage prompt to add
        the appropriate data to the stats table.
        """
        for attr in self.stat_list:
            cols = attr["cols"]
            buckets = attr.get("buckets")
            constraint = attr.get("constraint")
            include_upper = attr.get("include_upper",True)
            if buckets:
                self.table.stats.add_bucketed_counts(cols, buckets, constraint, include_upper)
            else:
                self.table.stats.add_stats(cols, constraint)
