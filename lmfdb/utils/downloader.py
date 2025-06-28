"""
This file defines two kinds of classes used in constructing download files for the LMFDB:

* ``DownloadLanguage``, representing languages such as Sage and Magma
* ``Downloader``, provides utility functions for downloading both search results and a single object.
  Can subclassed to provide customization.  An instance of this class should be passed in as a
  download shortcut to the search_wrap constructor.

These interact with the column types defined in search_columns.py to support downloading different types of data.
In particular, the languages shown available for download are set by the `languages` attribute of a `SearchColumns` object.
"""


import time
import datetime
import re
import itertools
import csv
import io

from flask import abort, send_file, stream_with_context, Response, request, redirect, url_for
from urllib.parse import urlparse, urlunparse

from werkzeug.datastructures import Headers
from ast import literal_eval
from io import BytesIO
from sage.all import Integer, Rational, lazy_attribute

from lmfdb.utils import plural_form, pluralize, flash_error

class DownloadLanguage():
    # We choose the most common values; override these if needed in each subclass
    comment_prefix = '#'
    assignment_defn = '='
    line_end = '' # Semicolon also common

    delim_start = '[' # These are default delimiters used when wrapping a list in the default to_lang function
    delim_end = ']' # If the needed delimiter depends on context, a language can override the delim method instead
    start_and_end = ['[',']'] # These are the delimiters used in a multiline list
    iter_sep = ",\n" # These are used to separate rows
    make_data_comment = '' # A formattable comment describing how to call the make_data() function,
    #                        with placeholders `short_name` and `var_name`
    none = 'NULL'
    true = 'true'
    false = 'false'
    offset = 0 # the offset for the first entry in a list; 0-based by default
    return_keyword = 'return '
    return_finish = ''

    # Other required attributes in a subclass
    # name -- the name of the language, used when passing back and forth to strings
    # file_suffix -- the string appended to produce the full filename
    # function_start -- a formattable string giving the first line of a function definition
    #                   (with placeholders `func_name` and `func_args`)
    # function_end -- a string giving the line that ends a function definition

    # You may also want to update the inclusions dictionaries of Downloader objects,
    # as well as the createrecord_code and makedata_code methods.

    def initialize(self, cols, downloader):
        """
        This code block is inserted at a global level below the data list, to provide
        file-wide definitions for use in the create_record and make_data functions.

        INPUT:

        - ``cols`` -- the list of search columns being downloaded
        - ``downloader`` -- the Downloader object
        """
        return ""

    def delim(self, inp, level):
        """
        Returns the start and end delimiters appropriate for wrapping a list.
        A utility method used in ``to_lang``.

        INPUT:

        - ``inp`` -- a python iterable
        - ``level`` -- a nesting counter, starting at 1
        """
        # We allow the language to specify the delimiter based on the contents of inp
        # This allows magma to use sequences if the types are all the same
        return self.delim_start, self.delim_end

    def sep(self, level):
        """
        Returns the separator used for a list.  Defaults to comma, but can be overridden as a tab for example.
        A utility method used in ``to_lang``.

        INPUT::

        - ``level`` -- a nesting counter, starting at 1
        """
        return ", "

    def comment(self, inp):
        return "\n".join(self.comment_prefix + line if line else "" for line in inp.split("\n"))

    def string_to_lang(self, inp):
        """
        Override this function to remove quotes change backslash parsing.
        Used for languages like CSV where someone else has already dealt with escaping.
        """
        inp = inp.replace("\\", "\\\\").replace('"', '\\"')
        return '"{0}"'.format(inp)

    def to_lang(self, inp, level=1):
        """
        Converts a python object into a string for use in the given language.  At a minimum,
        should support None, True, False, strings, integers, floats, rationals, and (nested) lists of these objects
        """
        if inp is None:
            return self.none
        elif inp is True:
            return self.true
        elif inp is False:
            return self.false
        if isinstance(inp, str):
            return self.string_to_lang(inp)
        if isinstance(inp, (int, Integer, Rational)):
            return str(inp)
        try:
            it = iter(inp)
        except TypeError:
            # not an iterable object
            return str(inp)
        else:
            start, end = self.delim(inp, level)
            return start + self.sep(level).join(self.to_lang(c, level=level + 1) for c in it) + end

    def to_lang_iter(self, inp):
        """
        To support long lists of downloaded objects, this entry point creates a generator
        yielding strings making a a multiline list corresponding to the input.

        INPUT:

        - ``inp`` -- an iterable python object (currently called with the output of itertools.chain)
        """
        start, end = self.start_and_end
        sep = self.iter_sep
        it = iter(inp)
        yield start + "\n"
        try:
            yield self.to_lang(next(it))
        except StopIteration:
            pass
        for row in it:
            yield sep + self.to_lang(row)
        yield "\n" + end

    def assign(self, name, inp):
        """
        Creates an assignment clause in this language.

        INPUT:

        - ``name`` -- the variable name being assigned to.
        - ``inp`` -- a python object holding the desired contents of the variable
                     (or a string, already parsed into the language)
        """
        if not isinstance(inp, str):
            inp = self.to_lang(inp)
        return name + " " + self.assignment_defn + " " + inp + self.line_end + "\n"

    def assign_columns(self, columns, column_names):
        # We have a special function for assigning columns, to support adding hyperlinks to knowls in CSV files
        return self.assign("columns", column_names)

    def assign_iter(self, name, inp):
        """
        Creates an assignment clause from an iterable

        INPUT:

        - ``name`` -- the variable name being assigned to.
        - ``inp`` -- a python iterable holding the desired contents of the variable
        """
        yield name + " " + self.assignment_defn + " "
        yield from inp
        yield self.line_end + "\n"

    def record_assign(self, name, key, val):
        return f'{name}["{key}"] = {val}'

    def func_start(self, fname, fargs):
        """
        Creates the first line of a function definition.

        INPUT:

        - ``fname`` -- the name of the function
        - ``fargs`` -- a string, giving the function arguments, already parsed into the needed format
        """
        return self.function_start.format(func_name=fname, func_args=fargs)

class MagmaLanguage(DownloadLanguage):
    name = 'magma'
    file_suffix = '.m'
    comment_prefix = '//'
    assignment_defn = ':='
    line_end = ';'
    none = '[]'
    offset = 1
    make_data_comment = 'To create a list of {short_name}, type "{var_name}:= make_data();"'
    function_start = 'function {func_name}({func_args})\n'
    function_end = 'end function;\n'

    def delim(self, inp, level):
        # Magma has several types corresponding to Python lists
        # We use Sequences if possible, and Lists if not
        if not inp:
            return "[", "]"
        typ = set(type(x) for x in inp)
        if len(typ) > 1:
            return "[*", "*]"
        typ = typ.pop()
        while issubclass(typ, (list, tuple)):
            leveled = []
            for x in inp:
                leveled.extend(x)
            typ = set(type(x) for x in leveled)
            if len(typ) > 1:
                return "[*", "*]"
            typ = typ.pop()
            inp = leveled
        return "[", "]"

    def initialize(self, cols, downloader):
        from lmfdb.number_fields.number_field import PolynomialCol
        column_names = [(col.name if col.download_col is None else col.download_col) for col in cols]
        for var, (require, bylang) in downloader.inclusions.items():
            if "magma" in bylang and all(col in column_names for col in require):
                column_names.append(var)
        s = f"RecFormat := recformat<{','.join(column_names)}>;\n"
        if any(isinstance(col, PolynomialCol) for col in cols):
            s += 'ZZx<x> := PolynomialRing(Integers());\n'
        return s + '\n'

    def record_assign(self, name, key, val):
        return f'{name}`{key} := {val};'

class SageLanguage(DownloadLanguage):
    name = 'sage'
    file_suffix = '.sage'
    none = 'None'
    true = 'True'
    false = 'False'
    make_data_comment = 'To create a list of {short_name}, type "{var_name} = make_data()"'
    function_start = 'def {func_name}({func_args}):\n'
    function_end = ''

    def initialize(self, cols, downloader):
        from lmfdb.number_fields.number_field import PolynomialCol
        if any(isinstance(c, PolynomialCol) for c in cols):
            return '\nZZx.<x> = ZZ[]\n\n'
        else:
            return '\n'

class GPLanguage(DownloadLanguage):
    name = 'gp'
    file_suffix = '.gp'
    start_and_end = ['{[',']}']
    comment_prefix = '\\\\'
    line_end = ';'
    none = 'null'
    true = '1'
    false = '0'
    offset = 1
    make_data_comment = 'To create a list of {short_name}, type "{var_name} = make_data()"'
    function_start = '{func_name}({func_args}) =\n{{\n' # Need double bracket since we're formatting these
    function_end = '}\n'
    return_keyword = 'return('
    return_finish = ')'

    def record_assign(self, name, key, val):
        return f'mapput(~{name}, "{key}", {val});'

class GAPLanguage(DownloadLanguage):
    name = 'gap'
    file_suffix = '.g'
    assignment_defn = ':='
    line_end = ';'
    none = '[]'
    true = 'true'
    false = 'false'
    offset = 1
    make_data_comment = 'To create a list of {short_name}, type "{var_name} := make_data();"'
    function_start = '{func_name} := function({func_args})\n'
    function_end = 'end;\n'

    def record_assign(self, name, key, val):
        return f'{name}.{key} := {val};'

class OscarLanguage(DownloadLanguage):
    name = 'oscar'
    file_suffix = '.jl'
    offset = 1
    none = 'nothing'
    make_data_comment = 'To create a list of {short_name}, type "{var_name} = make_data()"'
    function_start = 'function {func_name}({func_args})\n'
    function_end = 'end\n'

    def initialize(self, cols, downloader):
        from lmfdb.number_fields.number_field import PolynomialCol
        if any(isinstance(c, PolynomialCol) for c in cols):
            return '\nRx,x = PolynomialRing(QQ)\n\n'
        else:
            return '\n'

class TextLanguage(DownloadLanguage):
    name = 'text'
    file_suffix = '.txt'
    start_and_end = ["", "\n\n"]
    iter_sep = "\n"

    def assign(self, name, inp):
        # We don't want to include the column definition here, since it's already in comments
        return ""

    def assign_iter(self, name, inp):
        # For text downloads, we just give the data
        yield from inp

    def delim(self, inp, level):
        if level == 1:
            return "", ""
        else:
            return "[", "]"

    def sep(self, level):
        if level == 1:
            return "\t"
        else:
            return ", "

class CSVLanguage(DownloadLanguage):
    name = "csv"
    file_suffix = ".csv"
    start_and_end = ["", ""]
    iter_sep = "\n"
    buff = io.StringIO()

    def comment(self, inp):
        # CSV does not support comments
        return ""

    def string_to_lang(self, inp):
        # The csv module deals with escaping backslashes, and we don't want extra quotes
        return inp

    @lazy_attribute
    def writer(self):
        return csv.writer(self.buff)

    def write(self, inp):
        t = self.buff.tell()
        self.writer.writerow(inp)
        self.buff.seek(t)
        return self.buff.readline()

    def assign(self, name, inp):
        # Column assignments are handled separately below
        return ""

    def assign_columns(self, columns, column_names):
        urlparts = urlparse(request.url)
        urls = [urlunparse(urlparts._replace(
            path=url_for("knowledge.show", ID=col.knowl),
            params="",
            query="",
            fragment="")) for col in columns]
        return self.write([f'=HYPERLINK("{url}", "{name}")'
                           for url, name in zip(urls, column_names)])

    def assign_iter(self, name, inp):
        # For CSV downloads, we only output data rows since CSV does not support comments
        yield from inp

    def to_lang_iter(self, inp):
        """
        We use the csv module to generate the output
        """
        for row in inp:
            yield self.write(row)


class Downloader():
    """
    A class for downloading data in a uniform way.

    You should inherit from this class, providing

    - a ``table`` attribute, which is a PostgresTable
    - a ``title`` attribute (e.g. ``'Genus 2 curves'``), used at the beginning
      of the top comment.  Defaults to table name.
    - a ``short_name`` attribute (e.g. ``'curves'``), which is used in comments.
      Defaults to last word of lower cased title.
    - a ``var_name`` attribute (e.g. ``'curves'``), used as a variable name in comments.
      Defaults to short_name, with spaces replaced by underscores.

    An instance of the resulting class is usually then
    passed into the `shortcuts` argument of the `search_wrap`
    decorator on your search function.
    """
    # defaults, edit as desired in inherited class
    lang_key = 'Submit' # name of the HTML button/link starting the download
    languages = {
        'magma': MagmaLanguage(),
        'sage': SageLanguage(),
        'gp': GPLanguage(),
        'gap': GAPLanguage(),
        'text': TextLanguage(),
        'oscar': OscarLanguage(),
        'csv': CSVLanguage(),
    }

    # To automatically add data to the create_record function, you can modify the following dictionary,
    # which should have keys to be inserted in the resulting record, with values a pair (cols, bylang),
    # where cols is a list of column names required to be present in order to insert this code,
    # and bylang is a dictionary giving code snippets to be added defining the key.
    # See NFDownloader in lmfdb/number_fields/number_field.py for an example.
    inclusions = {}

    def __init__(self, table=None, title=None, filebase=None, short_name=None, var_name=None, lang_key='Submit'):
        if table is None:
            if hasattr(self.__class__, "table"):
                table = self.__class__.table
        self.table = table

        if title is None:
            if hasattr(self.__class__, "title"):
                title = self.__class__.title
            elif table is not None:
                title = table.search_table
        self.title = title

        if short_name is None:
            if hasattr(self.__class__, "short_name"):
                short_name = self.__class__.short_name
            elif title is not None:
                short_name = title.split(" ")[-1].lower()
        self.short_name = short_name

        if var_name is None:
            if hasattr(self.__class__, "var_name"):
                var_name = self.__class__.var_name
            elif short_name is not None:
                var_name = plural_form(short_name.replace(" ", "_"))
        self.var_name = var_name

        if filebase is None:
            if hasattr(self.__class__, "filebase"):
                filebase = self.__class__.filebase
            elif table is not None:
                filebase = table.search_table
        self.filebase = filebase

        self.lang_key = lang_key

    def postprocess(self, row, info, query):
        """
        This function is called on each result from the database.

        This hooks makes it possible to construct a python object wrapping the record that provides
        additional methods for supporting search columns.  See abelian varieties and artin representations
        for examples.
        """
        return row

    def get(self, name, default=None):
        """
        We emulate dictionary-style access to attributes, with a default value.

        INPUT:

        - ``name`` -- a string, the name of an attribute
        - ``default`` -- the value to be returned if the attribute does not exist
        """
        if hasattr(self, name):
            return getattr(self, name)
        else:
            return default

    def _wrap(self, result, filebase, lang, title=None, add_ext=True):
        """
        Adds the time downloaded as a comment, make into a flask response.

        INPUT:

        - ``result`` -- a string, the contents of the file to be downloaded
        - ``filebase`` -- the base part of the filename, without a suffix
        - ``lang`` -- a download language, or string giving a key into ``self.languages``
        - ``title`` -- the title, included in a comment at the top of the file
        - ``add_ext`` -- whether to add the extension to the filename (determined by the language)

        OUTPUT:

        An http response, as generated by Flask's `send_file` function.
        """
        if title is None:
            title = self.title
        if isinstance(lang, str):
            lang = self.languages.get(lang, TextLanguage())
        filename = filebase + lang.file_suffix
        mydate = time.strftime("%d %B %Y")
        s = '\n'
        s += lang.comment(' %s downloaded from the LMFDB on %s.\n' % (title, mydate))
        s += result
        bIO = BytesIO()
        bIO.write(s.encode('utf-8'))
        bIO.seek(0)
        return send_file(bIO, download_name=filename, as_attachment=True)

    def _wrap_generator(self, generator, filebase, lang='text', title=None, add_ext=True):
        """
        As for _wrap, but uses a stream.  For use with (potentially) large files.

        INPUT:

        - ``generator`` -- yields the contents of the file, usually one line at a time
        - ``filebase`` -- the base part of the filename, without a suffix
        - ``lang`` -- a download language, or string giving a key into ``self.languages``
        - ``title`` -- the title, included in a comment at the top of the file
        - ``add_ext`` -- whether to add the extension to the filename (determined by the language)

        OUTPUT:

        An http response giving the file as an attachment
        """
        if title is None:
            title = self.title
        if isinstance(lang, str):
            lang = self.languages.get(lang, TextLanguage())
        filename = filebase
        if add_ext:
            filename += lang.file_suffix
        mydate = time.strftime("%d %B %Y")

        @stream_with_context
        def _generator():
            yield lang.comment('\n %s downloaded from the LMFDB on %s.\n' % (title, mydate))
            # Rather than just doing `yield from generator`, we need to buffer
            # since otherwise the response is inefficiently broken up into tiny chunks
            # causing the download to slow.

            # When running asynchronously (which we couldn't get to work), a sleep here
            # was also necessary to prevent gunicorn from timing out the worker.
            # Unfortunately, making asynchronous mode work reliably required further
            # changes to the underlying database interactions, so is not currently
            # implemented.
            buff = ""
            threshold = 10240 # 10KB
            for i, line in enumerate(generator, 1):
                if len(buff) > threshold:
                    yield buff
                    buff = ""
                    #time.sleep(0.001)
                buff += line
                #yield line
            if buff:
                yield buff

        headers = Headers()
        headers.add('Content-Disposition', 'attachment', filename=filename)
        resp = Response(_generator(), mimetype='text/event-stream', headers=headers)
        return resp

    def get_table(self, info):
        """
        This is a hook for downloaders to modify the search table based on info, which happens for hgm for example.
        """
        return self.table

    def modify_query(self, info, query):
        """
        This is a hook for downloaders to modify the info dictionary or a query before executing it.
        It is used in artin representations to only include non-hidden representations
        """
        pass

    def get_sort(self, info, query):
        """
        This determines the sort order requested from the database.

        OUTPUT:

        - a list or other object appropriate for passing as the ``sort`` argument
          to the ``search`` method of the search table.
        - a string describing the search order
        """
        SA = self.search_array
        if SA is not None and SA.sorts is not None:
            sorts = SA.sorts.get(SA._st(info), []) if isinstance(SA.sorts, dict) else SA.sorts
            sord = info.get("sort_order", "")
            sop = info.get("sort_dir", "")
            for name, display, S in sorts:
                if name == sord:
                    if sop == "op":
                        return [(col, -1) if isinstance(col, str) else (col[0], -col[1]) for col in S], f"{display} (reversed)"
                    return S, display
        return None, None

    def createrecord_code(self, lang, column_names):
        """
        The contents of a function that creates a record from an entry of the data list.

        By default, this just creates a record/dictionary using the column names as keys
        and the contents as values, but it can be overridden in a subclass.
        """
        if lang.name == "sage":
            lines = ["out = {col: val for col, val in zip(columns, row)}"]
        elif lang.name == "magma":
            pairs = [f"{col}:=row[{i+1}]" for i, col in enumerate(column_names)]
            lines = [f"out := rec<RecFormat|{','.join(pairs)}>;"]
        elif lang.name == "gap":
            local_vars = ["out"] + [var for var, (require, bylang) in self.inclusions.items() if "gap" in bylang]
            pairs = [f"{col}:=row[{i+1}]" for i, col in enumerate(column_names)]
            lines = [f"local {', '.join(local_vars)};", f"out := rec({','.join(pairs)});"]
        elif lang.name == "gp":
            pairs = [f'"{col}",row[{i+1}]' for i, col in enumerate(column_names)]
            lines = [f"out = Map([{';'.join(pairs)}]);"]
        elif lang.name == "oscar":
            lines = ["out = Dict(zip(columns, row))"]
        else:
            return ""
        for var, (require, bylang) in self.inclusions.items():
            if all(col in column_names for col in require) and lang.name in bylang:
                lines.append(bylang[lang.name])
                lines.append(lang.record_assign("out", var, var))
        lines.append(lang.return_keyword + "out" + lang.return_finish + lang.line_end)
        return "".join("    " + line + "\n" for line in lines)

    def makedata_code(self, lang):
        """
        The contents of a function that processes the input data list to produce
        a more user friendly version.  By default, this turns the entries into
        records/dictionaries, but can be overridden in a subclass.
        """
        if lang.name == "sage":
            line = "return [create_record(row) for row in data]"
        elif lang.name == "magma":
            line = "return [create_record(row) : row in data];"
        elif lang.name == "gap":
            line = "return List(data, create_record);"
        elif lang.name == "gp":
            line = "return(apply(create_record, data));"
        elif lang.name == "oscar":
            line = "return [create_record(row) for row in data]"
        else:
            return ""
        return "    " + line + "\n"

    def __call__(self, info):
        """
        Generate download file for a list of search results determined by the
        ``query`` field in ``info``.

        This is the main entry point for generating a download file from search results.
        """
        lang = self.languages[info.get(self.lang_key, 'text')]
        table = self.get_table(info)
        self.search_array = info.get("search_array")
        filename = self.filebase
        ts = datetime.datetime.now().strftime("%m%d_%H%M")
        filename = f"lmfdb_{filename}_{ts}"
        urlparts = urlparse(request.url)
        pieces = urlparts.query.split("&")
        # We omit the download-specific parts that were added in lmfdb/templates/download_search_results.html
        omit = ["Submit=", "download=", "query=", "download_row_count="]
        pieces = [piece for piece in pieces if not any(piece.startswith(bad) for bad in omit)]
        urlparts = urlparts._replace(query="&".join(pieces))
        url = urlunparse(urlparts)

        # This comment is near the top of the file and describes how to call the make_data function defined below.
        make_data_comment = lang.make_data_comment
        if make_data_comment:
            make_data_comment = make_data_comment.format(short_name=plural_form(self.short_name), var_name=self.var_name)

        # Determine which columns will be fetched from the database
        columns = info["columns"]
        # It's fairly common to add virtual columns in postprocessing that are then used in MultiProcessedCols.
        # These virtual columns are often only used in display code and won't be present in the database, so we just strip them out
        if isinstance(columns.db_cols, list):
            proj = [col for col in columns.db_cols if col in table.search_cols]
        else:
            proj = columns.db_cols # some tables use 1 for project-to-all

        # Extract the query and modify it
        try:
            query = literal_eval(info.get('query', '{}'))
            self.modify_query(info, query)
        except Exception as err:
            return abort(404, "Unable to parse query: %s" % err)

        one_per = query.pop("__one_per__", None)
        if isinstance(one_per, str):
            one_per = [one_per]

        # Determine the sort order
        sort, sort_desc = self.get_sort(info, query)

        # The user can limit the number of results
        if "download_row_count" in info:
            limit = info["download_row_count"]
            match = re.match(r"\s*(\d+)\s*-\s*(\d+)\s*", limit)
            if match:
                offset = int(match.group(1)) - 1
                limit = int(match.group(2)) - offset
                limit = max(limit, 0)
            else:
                match = re.match(r"\s*(\d+)\s*", limit)
                if match:
                    offset = 0
                    limit = int(match.group(1))
                else:
                    flash_error('Row constraint (%s) must be "all", an integer, or a range of integers', limit)
                    return redirect(url)
        else:
            offset = 0
            limit = None

        # The number of results is needed in advance since we want to show it at the top
        # while the iterator won't be done
        num_results = table.count(query)

        # Actually issue the query, and store the result in an iterator
        data = iter(table.search(query, projection=proj, sort=sort, one_per=one_per, limit=limit, offset=offset))

        # We get the first 50 results, in order to accommodate sections (like modular forms) where default and contingent columns rely on having access to info["results"]
        # We don't get all the results, since we want to support downloading millions of records, where this would time out.
        info["results"] = first50 = [self.postprocess(row, info, query) for row in itertools.islice(data, 50)]
        cols = [col for col in columns.columns_shown(info, rank=-1) if col.default(info)]
        column_names = [(col.name if col.download_col is None else col.download_col) for col in cols]
        if len(column_names) != len(set(column_names)):
            # There are some cases where multiple displayed columns correspond to the same underlying data
            # (Weirstrass coefficients and Weierstrass equation for elliptic curves for example).
            # In such cases, we use the *name* to remove duplicates, and assume that we can choose either column
            seen = set()
            include = []
            for i, name in enumerate(column_names):
                if name not in seen:
                    include.append(i)
                    seen.add(name)
            cols = [cols[i] for i in include]
            column_names = [column_names[i] for i in include]
        data_format = [(col.title if isinstance(col.title, str) else col.title(info)) for col in cols]
        first50 = [[col.download(rec) for col in cols] for rec in first50]
        if num_results > 10000:
            # Estimate the size of the download file.  This won't necessarily be a great estimate
            # since later rows are often larger, but it's something
            size_estimate = sum([len(lang.to_lang(rec)) for rec in first50]) * num_results / 50
            if size_estimate > 100 * 1024**2: # 100MB
                # We need to delete the data iterator, otherwise it will try to go through all of the records when another connection to the database is opened.
                del data
                raise ValueError("Download file too large.  You can try either using the API or directly connecting to the LMFDB's PostgreSQL database")
        #print("FIRST FIFTY", first50)

        # Create a generator that produces the lines of the download file
        def make_download():
            # We start with a string describing the query, the number of results and the sort order
            yield lang.comment(' Search link: %s\n' % url)
            if limit is None:
                num_res_disp = pluralize(num_results, self.short_name)
            else:
                num_res_disp = pluralize(limit, self.short_name, denom=num_results, offset=offset)
            yield lang.comment(' Query "%s" %s %s%s.\n\n' % (
                str(info.get('query')),
                "returned" if limit is None else "was limited to",
                num_res_disp,
                "" if sort_desc is None else f", sorted by {sort_desc}"))

            # We then describe the columns included, both in a comment and as a variable
            yield lang.comment(' Each entry in the following data list has the form:\n')
            yield lang.comment('    [' + ', '.join(data_format) + ']\n')
            yield lang.comment(' For more details, see the definitions at the bottom of the file.\n')
            if make_data_comment:
                yield lang.comment(f'\n {make_data_comment}\n')
            yield lang.comment('\n\n')
            yield lang.assign_columns(cols, column_names)

            # This is where the actual contents are included, applying postprocess and col.download to each
            yield from lang.assign_iter("data", lang.to_lang_iter(
                itertools.chain(
                    first50,
                    map(
                        lambda rec: [col.download(rec) for col in cols],
                        map(
                            lambda rec: self.postprocess(rec, info, query),
                            data)))))

            # Here we allow language specific global initialization code, like defining polynomial rings
            yield lang.initialize(cols, self)

            # Now the two function definitions, create_record and make_data, that aim to make the data list more user friendly
            if make_data_comment:
                yield "\n" + lang.func_start("create_record", "row") + self.createrecord_code(lang, column_names) + lang.function_end
                yield "\n" + lang.func_start("make_data", "") + self.makedata_code(lang) + lang.function_end + "\n\n"
            # We need to be able to look up knowls within knowls, so to reduce the number of database calls we just get them all.

            # We do some global preprocessing to get access to knowls that define the columns
            if any(col.download_desc is None for col in cols):
                from lmfdb.knowledge.knowl import knowldb
                all_knowls = {rec["id"]: (rec["title"], rec["content"]) for rec in knowldb.get_all_knowls(fields=["id", "title", "content"])}
                knowl_re = re.compile(r"""\{\{\s*KNOWL\(\s*["'](?:[^"']+)["'],\s*(?:title\s*=\s*)?['"]([^"']+)['"]\s*\)\s*\}\}""")

                def knowl_subber(match):
                    return match.group(1)

            # If we haven't specified a more specific download_desc, we use the column knowl to get a string to add to the bottom of the file for each column
            for col, name in zip(cols, column_names):
                if col.download_desc is None:
                    knowldata = all_knowls.get(col.knowl)
                    if knowldata is None:
                        continue
                    # We want to remove KNOWL macros
                    _, content = knowldata
                    knowl = knowl_re.sub(knowl_subber, content)
                else:
                    knowl = col.download_desc
                if knowl:
                    if isinstance(col.title, str):
                        title = col.title
                    else:
                        title = col.title(info)
                    if name.lower() == title.lower():
                        yield lang.comment(f" {title} --\n")
                    else:
                        yield lang.comment(f"{title} ({name}) --\n")
                    for line in knowl.split("\n"):
                        if line.strip():
                            yield lang.comment("    " + line.rstrip() + "\n")
                        else:
                            yield lang.comment("\n")
                    yield lang.comment("\n\n")

        return self._wrap_generator(make_download(), filename, lang=lang)
