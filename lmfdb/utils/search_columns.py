"""
This file includes classes defining how the columns on search result pages display,
as well as how they create content in a downloaded file.  There are two kinds of classes:

* Instances of ``SearchCol`` (and its subclasses), correspond to a single column, defining
  how it is displayed and downloaded
* All of the search columns are collected into a ``SearchColumns`` instance, providing an
  interface for interacting with the set of columns as a whole.

The three main entry points to ``SearchCol`` are

* its ``display`` method, which returns a string to be displayed in the html corresponding to
  the column within a row corresponding to a provided dictionary,
* its ``download`` method, which returns a Python object that is then encoded using a download
  language (in ``lmfdb/utils/downloader.py``) when creating a download file,
* its ``show`` method, which is used to iterate over columns, and usually just yields the
  column, but can yield nothing (if the column shouldn't be displayed) or multiple subcolumns
  (in the case of column groups).
"""

import re
from .web_display import display_knowl
from lmfdb.utils import coeff_to_poly
from sage.all import Rational, latex

def get_default_func(default, name):
    """
    This utility function takes the default value provided when creating
    a search column and returns a function that determines whether the
    column should be shown by default, based on the info dictionary
    created from the url parameters.

    In particular, it ensures that if the user explicitly hides/shows
    the column in the column dropdown, or if the column is the main
    component of a sort order, that overrides the input value.
    """
    def f(info):
        if "hidecol" in info and name in info["hidecol"].split("."):
            return False
        if "showcol" in info and name in info["showcol"].split("."):
            return True
        sort_order = info.get('sort_order', '')
        if (sort_order and sort_order == name
                and "search_array" in info
                and info["search_array"].sorts is not None):
            return True
        if isinstance(default, bool):
            return default
        return default(info)
    return f


class SearchCol:
    """
    INPUT:

    - ``name`` -- a string describing this column, the name of the html element, used in the url
      to specify that the column be shown or hidden, the name for the column in download files,
      and the default key used when extracting data from a database record.
    - ``knowl`` -- a knowl identifier, for displaying the column header as a knowl
    - ``title`` -- the string shown for the column header, also included when describing the column
      in a download file.  Alternatively, you can provide a function of info that produces such a string.
    - ``default`` -- either a boolean or a function taking an info dictionary as input and returning
      a boolean.  In either case, this determines whether the column is displayed initially.  See
      the ``get_default_func`` above.
    - ``align`` -- horizontal alignment for this column; left by default, though some subclasses
      override this choice.
    - ``contingent`` -- either None or a function taking an info dictionary as input and returning
      a boolean.  In the second case, if the function returns false then the column is not even
      included in the list of drop-down options.
    - ``short_title`` -- the string used to describe this column in the dropdown (defaults to the same
      as the title).
    - ``mathmode`` -- whether the contents should be displayed in math mode
    - ``orig`` -- a list of columns from the underlying search table, used to construct this column.
      A string means the corresponding length 1 list, and None defaults to using the column name.
      This list is used to determine a projection when constructing the underlying search.
    - ``download_desc`` -- a string included at the bottom of the download file describing this column.
      Defaults to the contents of the knowl.
    - ``download_col`` -- a column of the underlying search table, used to clarify what data
      should be included.  Defaults to the column's name.
    - ``th_class``, ``th_style``, ``th_content``, ``td_class``, ``td_style``, ``td_content`` -- used
      to add CSS to the HTML elements corresponding to this column.

    Name, knowl and title can be passed either positionally or as a keyword argument; other values should be
    provided as keywords so that subclasses don't need to worry about passing positional arguments appropriately.
    """
    def __init__(self, name, knowl, title, default=True, align="left",
                 mathmode=False, contingent=None, short_title=None, orig=None,
                 download_desc=None, download_col=None, **kwds):
        # Both contingent and default can be functions that take info
        # as an input (if default is a boolean it's translated to the
        # constant function with that value)
        # If contingent is false, then that column doesn't even show
        # up on the list of possible columns
        # If default is false, then that column is included in the
        # selector but not displayed by default
        assert "," not in name
        self.name = name
        self.knowl = knowl
        self.title = title
        if short_title is None:
            if title is None:
                short_title = None
            elif isinstance(title, str):
                short_title = title.lower()
            else:
                def short_title(info): return title(info).lower()
        self.short_title = short_title
        self.default = get_default_func(default, name)
        self.mathmode = mathmode
        if orig is None:
            orig = [name]
        elif isinstance(orig, str):
            orig = [orig]
        self.orig = orig
        self.height = 1
        self.contingent = contingent
        self.th_class = self.td_class = f"col-{name}"
        if align == "left":
            self.th_style = self.td_style = ""
        else:
            self.th_style = self.td_style = f"text-align:{align};"
        self.th_content = self.td_content = ""
        self.download_desc = download_desc
        self.download_col = download_col

        for key, val in kwds.items():
            assert hasattr(self, key) and key.startswith("th_") or key.startswith("td_")
            setattr(self, key, getattr(self, key) + val)

    def _get(self, rec, name=None, downloading=False):
        """
        INPUT:

        - ``rec`` -- either a dictionary, or a class with attributes (such as AbvarFq_isoclass,
          constructed through a postprocess step).  This corresponds to a row (of the search results,
          or of the underlying table in the database).
        - ``name`` -- defaults to the name of the column, but can be overridden when downloading
        - ``downloading`` -- boolean, whether we are extracting a value for downloading.  Determines
          whether missing values are returned as empty strings or as None.

        OUTPUT:

        A python object, the value for this column extracted from the database
        """
        if name is None:
            name = self.name
            orig = self.orig[0]
        else:
            orig = name
        if isinstance(rec, dict):
            ans = rec.get(orig)
            if not downloading and ans is None:
                return ""
            return ans
        val = getattr(rec, name)
        return val() if callable(val) else val

    def get(self, rec):
        """
        INPUT:

        - ``rec`` -- either a dictionary, or a class with attributes (such as AbvarFq_isoclass,
          constructed through a postprocess step).  This corresponds to a row (of the search results,
          or of the underlying table in the database).

        OUTPUT:

        A python object, the value for this column extracted from the database
        """
        # This function is used by the front-end display code, while the underlying _get method
        # is used for downloading.  The difference shows up for Floats, where we want the full
        # precision in the downloaded file
        return self._get(rec)

    def display(self, rec):
        """
        A string, to be displayed on the webpage, corresponding to this column within the row specified by
        the input ``rec``.
        """
        # default behavior is to just use the string representation of rec
        s = str(self.get(rec))
        if s and self.mathmode:
            s = f"${s}$"
        return s

    def display_knowl(self, info):
        """
        Displays the column header contents.
        """
        if isinstance(self.title, str):
            title = self.title
        else:
            title = self.title(info)
        if self.knowl:
            return display_knowl(self.knowl, title)
        return title

    def show(self, info, rank=None):
        """
        This function is used when iterating through columns.

        INPUT:

        - ``info`` -- a dictionary, constructed from the url passed with the request
        - ``rank`` -- either None (indicating a data row), -1 (indicating a download), 0 (indicating the main header row), or a positive integer (indicating a later header row, where most columns are not shown).

        OUTPUT:

        A generator, containing columns to be shown.  Usually contains one column (this one).
        """
        # rank = 0 indicates the header row, rank = -1 indicates downloading
        if (self.contingent is None or self.contingent(info)) and (rank is None or rank <= 0):
            yield self

    def download(self, rec):
        """
        A string, to be included in a download file, corresponding to this column.

        INPUT:

        - ``rec`` -- either a dictionary, or a class with attributes (such as AbvarFq_isoclass,
          constructed through a postprocess step).  This corresponds to a row (of the search results,
          or of the underlying table in the database).
        """
        name = None
        if self.download_col is not None:
            name = self.download_col
        return self._get(rec, name=name, downloading=True)


class SpacerCol(SearchCol):
    """
    Spacer columns have empty content, but can have CSS added through ``td_*`` and ``th_*`` keywords.
    """
    def __init__(self, name, **kwds):
        super().__init__(name, None, None, orig=[], **kwds)

    def display(self, rec):
        return ""

    def display_knowl(self, info):
        return ""

    def show(self, info, rank=None):
        if rank == -1:
            return []
        return super().show(info, rank)


class MathCol(SearchCol):
    """
    Math columns display their contents in math mode and use center alignment by default.
    """
    def __init__(self, name, knowl, title, align="center", **kwds):
        kwds["mathmode"] = True
        super().__init__(name, knowl, title, align=align, **kwds)


class FloatCol(MathCol):
    """
    Float columns allow specifying a precision (defaulting to 3)
    """
    def __init__(self, name, knowl, title, prec=3, **kwds):
        super().__init__(name, knowl, title, **kwds)
        self.prec = prec

    def get(self, rec):
        val = self._get(rec)
        if val == "":
            # null value
            return ""
        # We mix string processing directives so that we can use variable precision
        return f"%.{self.prec}f" % val


class CheckCol(SearchCol):
    """
    Check columns are for boolean columns from the database.  They use a unicode check mark
    to represent a True value, and question mark for unknown, and blank for False.
    They are also centered by default.
    """
    def __init__(self, name, knowl, title, align="center", unknown="?", no="", **kwds):
        super().__init__(name, knowl, title, align=align, **kwds)
        self.unknown = unknown
        self.no = no

    def display(self, rec):
        val = self._get(rec, downloading=True) # We emulate downloading so that we can determine if the value is None
        if val:
            return "&#x2713;"
        elif val is None:
            return self.unknown
        else:
            return self.no


class CheckMaybeCol(SearchCol):
    """
    CheckMaybe columns are for integer columns that use 1 to represent true, -1 for false and 0 for unknown.
    They explicitly show "not computed" rather than "?" for unknown values.
    They are also centered by default.
    """
    def __init__(self, name, knowl, title, align="center", unknown="?", no="", **kwds):
        super().__init__(name, knowl, title, align=align, **kwds)
        self.unknown = unknown
        self.no = no

    def display(self, rec):
        ans = self.get(rec)
        if ans > 0:
            return "&#x2713;"
        elif ans < 0:
            return self.no
        else:
            return self.unknown

    def download(self, rec, name=None):
        ans = self._get(rec)
        if ans == 0:
            return None
        else:
            return (ans > 0)


class LinkCol(SearchCol):
    """
    These columns are used for links.  They have an additional input, `url_for`,
    a function which takes the contents to be displayed
    (usually the label of an LMFDB object) and produces a url.
    """
    def __init__(self, name, knowl, title, url_for, **kwds):
        super().__init__(name, knowl, title, **kwds)
        self.url_for = url_for

    def display(self, rec):
        link = self.get(rec)
        if not link:
            return ""
        return f'<a href="{self.url_for(link)}">{link}</a>'


class ProcessedCol(SearchCol):
    """
    These columns allow for an arbitrary function to be applied to the contents retrieved from the database.

    They take two additional inputs:

    - ``func`` -- a function, applied to the contents from the database, whose output is to be displayed.
      Defaults to the identity.
    - ``apply_download`` -- either a boolean (determining whether the function should be applied when
      downloading), or a function that is applied instead while downloading.
    """
    def __init__(self, name, knowl, title, func=None, apply_download=False, **kwds):
        super().__init__(name, knowl, title, **kwds)
        if func is None:
            # Some other column types like RationalCol inherit from ProcessedCol
            def func(x): return x
        self.func = func
        self.apply_download = apply_download

    def display(self, rec):
        s = str(self.func(self.get(rec)))
        if s and self.mathmode:
            s = f"${s}$"
        return s

    def download(self, rec, name=None):
        if self.download_col is not None:
            name = self.download_col
        s = self._get(rec, name=name, downloading=True)
        if callable(self.apply_download):
            s = self.apply_download(s)
        elif self.apply_download:
            s = self.func(s)
        return s

class ProcessedLinkCol(ProcessedCol):
    """
    These columns allow for functions to be applied to the contents retrieved from the database before generating
    a link.  They take three additional inputs:

    - ``url_func`` -- a function producing the url from the contents
    - ``disp_func`` -- a function producing the string to be displayed from the contents
    - ``apply_download`` -- either a boolean (determining whether the display function should be applied when
      downloading), or a function that is applied instead while downloading.
    """
    def __init__(self, name, knowl, title, url_func, disp_func, **kwds):
        super().__init__(name, knowl, title, disp_func, **kwds)
        self.url_func = url_func

    def display(self, rec):
        disp = super().display(rec)
        url = self.url_func(self.get(rec))
        return f'<a href="{url}">{disp}</a>'


class MultiProcessedCol(SearchCol):
    """
    These columns allow for functions that combine multiple columns from the database into a single output column.
    They take three additional inputs:

    - ``inputs`` -- a list of column names from the search table (or that have been created in a postprocessing step)
    - ``func`` -- a function taking as input the inputs from a given row and producing a value to be displayed
    - ``apply_download`` -- either a boolean (determining whether the function should be applied when
      downloading), or a function that is applied instead when downloading.

    Note that ``download_col`` is still available, and provides an alternative to the use of ``apply_download``.

    Unlike SearchCols, these columns only support dictionaries rather than custom postprocess classes,
    since a custom class can just define a method for use instead.
    """
    def __init__(self, name, knowl, title, inputs, func, apply_download=True, **kwds):
        super().__init__(name, knowl, title, orig=inputs, **kwds)
        self.func = func
        self.apply_download = apply_download

    def display(self, rec):
        s = self.func(*[rec.get(col) for col in self.orig])
        if s and self.mathmode:
            s = f"${s}$"
        return s

    def download(self, rec, name=None):
        if self.download_col is None:
            data = [rec.get(col) for col in self.orig]
            if callable(self.apply_download):
                data = self.apply_download(*data)
            elif self.apply_download:
                data = self.func(*data)
        else:
            data = self._get(rec, name=self.download_col, downloading=True)
        return data

class ColGroup(SearchCol):
    """
    A group of columns that are visually joined.

    See classical modular forms and subgroups of abstract groups for examples.
    In the first case, a few columns (the first few traces and Atkin-Lehner signs)
    have subcolumns.  In the second, almost every column is grouped into one of three
    categories (subgroup, ambient or quotient).

    The main mechanism to support column groups is the show function.  Unlike most columns,
    the set of columns produced depends on the input rank.  When rank is -1 or 0 (downloading
    or top header), this column is yielded.  Otherwise (the subheaders or when displaying contents)
    the subcolumns are yielded.

    There is also a subtle difference in behavior depending on whether the name of the column group
    is the same as the name of each sub column.  In this case, the columns are all shown and hidden
    together in the column dropdown; otherwise, they are controlled independently.  See the
    ``ColumnController`` class in ``lmfdb/utils/search_boxes.py`` for more details.

    There is one additional input:

    - ``subcols`` -- a list of ``SearchColumn`` instances, or a callable taking ``info`` as input:
      the columns to be grouped together.

    In addition, the top column header is center aligned by default, ``orig`` is constructed from
    the ``orig`` attributes of the subcolumns

    Note that ``download_col`` is still available.  If not specified, a list is constructed from the
    download methods of the subcolumns.
    """
    # See classical modular forms for an example

    def __init__(self, name, knowl, title, subcols,
                 contingent=lambda info: True, orig=None,
                 align="center", download_together=False, **kwds):
        if orig is None:
            orig = sum([sub.orig for sub in subcols], [])
        super().__init__(name, knowl, title, align=align, orig=orig, contingent=contingent, **kwds)
        self.subcols = subcols
        self.download_together = download_together
        # A more complicated grouping could add more header rows, but the examples we have only need 2
        self.height = 2

    def show(self, info, rank=None):
        if self.contingent(info):
            if self.download_together and rank == -1:
                yield self
            else:
                if callable(self.subcols):
                    subcols = self.subcols(info)
                else:
                    subcols = self.subcols
                n = 0
                for sub in subcols:
                    if sub.name != self.name and "colgroup" not in sub.th_class:
                        sub.th_class += f" colgroup-{self.name}"
                    if sub.default(info):
                        n += 1
                self.th_content = f" colspan={n}"
                if rank is None or rank > 0:
                    yield from subcols
                else:
                    yield self

    def download(self, rec):
        if self.download_col is not None:
            return self._get(rec, name=self.download_col, downloading=True)
        return [sub.download(rec) for sub in self.subcols]


class SearchColumns:
    """
    This class packages together a list of search columns, providing the ``columns_shown`` method
    as an iterator over the columns to be displayed.

    INPUT:

    - ``columns`` -- a list of SearchCol objects
    - ``db_cols`` -- the column names to be retrieved from the underlying search table.
      By default this is constructed from the ``orig`` attributes of the underlying search columns,
      but it sometimes needs to be overridden, mainly for cases like abelian varieties and artin
      representations that use a class for postprocessing.
    - ``tr_class`` -- a list of CSS classes to be added to the corresponding rows in the header (see classical modular forms for an example)
    """
    above_results = ""  # Can add text above the Results (1-50 of ...) if desired
    above_table = ""  # Can add text above the results table if desired
    dummy_download = False  # change this to include dummy_download_search_results.html instead of download_search_results.html
    below_download = ""  # Can add text above the bottom download links

    def __init__(self, columns, db_cols=None, tr_class=None):
        self.maxheight = maxheight = max(C.height for C in columns)
        if maxheight > 1:
            for C in columns:
                if C.height == 1:
                    # columns that have height > 1 are responsible for
                    # setting th_content on their own
                    C.th_content += fr" rowspan={maxheight}"
        self.columns = columns
        if db_cols is None:
            db_cols = sorted(set(sum([C.orig for C in columns], [])))
        self.db_cols = db_cols
        if tr_class is None:
            tr_class = ["" for _ in range(maxheight)]
        self.tr_class = tr_class

    def columns_shown(self, info, rank=None):
        """
        Iterate over columns.

        INPUT:

        - ``info`` -- the dictionary created from the url
        - ``rank`` -- either None (indicating the body of the table), -1 (indicating downloading),
          0 (indicating the top row of the header) or a positive integer (indicating a lower row in the header).
        """
        # By default, this doesn't depend on info
        # rank is None in the body of the table, 0..(maxrank-1) in the header, and -1 when downloading
        for C in self.columns:
            yield from C.show(info, rank)


# The following column types are used to control download behavior

class PolynomialCol(SearchCol):
    """
    These columns display their contents as polynomials in x.
    """
    def display(self, rec):
        return f"${latex(coeff_to_poly(self.get(rec)))}$"

def eval_rational_list(s):
    """
    Some columns in the LMFDB store lists as strings rather than arrays.  This function
    unpacks several of the most common storage types for use in downloading.

    More precisely, it handles lists of integers or rationals stored in the following formats

    - unnested lists like "[1,2,3]" or "1,2,3"
    - once-nested lists like "[[1,2],[3,4]]" or "1,2;3,4"
    - single quotes wrapping the integers/rationals, like "['1','2','3']"
    """
    def split(x):
        if not x:
            return []
        return x.split(",")
    s = s.replace(" ", "").replace("'", "")
    s = s.lstrip("[").rstrip("]")
    if not s:
        return []
    for obreak in [";", "],["]:
        if obreak in s:
            return [[Rational(y) for y in split(x)] for x in s.split(obreak)]
    return [Rational(x) for x in split(s)]

class ListCol(ProcessedCol):
    """
    Used for lists that may be empty.

    The list may be stored in a postgres array or a postgres string
    """
    def __init__(self, *args, **kwds):
        if "delim" in kwds:
            self.delim = kwds.pop("delim")
            assert len(self.delim) == 2
        else:
            self.delim = None
        super().__init__(*args, **kwds)

    def display(self, rec):
        s = str(self.func(self.get(rec)))
        if s == "[]":
            s = "[&nbsp;]"
        if self.delim:
            s = s.replace("[", self.delim[0]).replace("]", self.delim[1])
        if s and self.mathmode:
            s = f"${s}$"
        return s

class RationalListCol(ListCol):
    """
    For lists of rational numbers.

    Uses the ``eval_rational_list`` function to process the column for downloading.
    """
    def __init__(self, name, knowl, title, func=None, apply_download=False, mathmode=True, use_frac=True, **kwds):
        self.use_frac = use_frac
        super().__init__(name, knowl, title, func=func, apply_download=apply_download, mathmode=mathmode, **kwds)

    def display(self, rec):
        s = super().display(rec)
        if self.use_frac:
            s = re.sub(r"(\d+)/(\d+)", r"\\frac{\1}{\2}", s)
        return s.replace("'", "").replace('"', '')

    def download(self, rec):
        s = super().download(rec)
        return eval_rational_list(s)

class RationalCol(ProcessedCol):
    """
    For rational numbers stored as strings; parses them appropriately for downloading.
    """
    def download(self, rec):
        s = super().download(rec)
        return Rational(s)
