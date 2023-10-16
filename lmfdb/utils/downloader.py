import time
import datetime

from flask import abort, send_file, stream_with_context, Response

from werkzeug.datastructures import Headers
from ast import literal_eval
from io import BytesIO

class DownloadLanguage():
    # We choose the most common values
    comment_prefix = '#'
    assignment_defn = '='
    line_end = ''
    delim_start = '['
    delim_end = ']'
    start_and_end = ['[',']']
    make_data_comment = ''
    none = 'NULL'
    true = 'true'
    false = 'false'
    offset = 0 # 0-based by default
    return_keyword = 'return '

    def initialize(self, cols):
        return ''

    def to_lang(self, inp, level=1):
        if inp is None:
            return self.none
        elif inp is True:
            return self.true
        elif inp is False:
            return self.false
        if isinstance(inp, str):
            inp = inp.replace("\\", "\\\\")
            if len(inp) >= 2 and inp[0] == '"' and inp[-1] == '"':
                return inp
            return '"{0}"'.format(inp)
        if isinstance(inp, int):
            return str(inp)
        if level == 0:
            start, end = self.start_and_end
            sep = ',\n'
        else:
            start = self.delim_start
            end = self.delim_end
            sep = ', '
        try:
            if level == 0:
                start = start + '\n'
                end = '\n' + end
            return start + sep.join(self.to_lang(c, level=level + 1) for c in inp) + end
        except TypeError:
            # not an iterable object
            return str(inp)

    def assign(self, name, elt):
        return name + ' ' + self.assignment_defn + ' ' + elt + self.line_end + '\n'

    def func_start(self, fname, fargs):
        return self.function_start.format(func_name=fname, func_args=fargs)

class MagmaLanguage(DownloadLanguage):
    name = 'magma'
    comment_prefix = '//'
    assignment_defn = ':='
    line_end = ';'
    delim_start = '[*'
    delim_end = '*]'
    none = '[]'
    offset = 1
    make_data_comment = 'To create a list of {short_name}, type "{var_name}:= make_data();"'
    file_suffix = '.m'
    function_start = 'function {func_name}({func_args})\n'
    function_end = 'end function;\n'
    makedata = '    return [* make_row(row) : row in data *];\n'
    makedata_basic = '    return data;\n'

    def initialize(self, cols):
        from lmfdb.number_fields.number_field import PolynomialCol
        if any(isinstance(c, PolynomialCol) for c in cols):
            return '\nZZx<x> := PolynomialRing(Integers());\n\n'
        else:
            return '\n'

class SageLanguage(DownloadLanguage):
    name = 'sage'
    none = 'None'
    true = 'True'
    false = 'False'
    make_data_comment = 'To create a list of {short_name}, type "{var_name} = make_data()"'
    file_suffix = '.sage'
    function_start = 'def {func_name}({func_args}):\n'
    function_end = ''
    makedata = '    return [ make_row(row) for row in data ]\n'
    makedata_basic = '    return data\n'

    def initialize(self, cols):
        from lmfdb.number_fields.number_field import PolynomialCol
        if any(isinstance(c, PolynomialCol) for c in cols):
            return '\nZZx.<x> = ZZ[]\n\n'
        else:
            return '\n'

class GPLanguage(DownloadLanguage):
    name = 'gp'
    start_and_end = ['{[',']}']
    comment_prefix = '\\\\'
    assignment_defn = '='
    none = 'null'
    true = '1'
    false = '0'
    offset = 1
    return_keyword = ''
    make_data_comment = 'To create a list of {short_name}, type "{var_name} = make_data()"'
    file_suffix = '.gp'
    function_start = '{func_name}({func_args}) = \n{{\n' # Need double bracket since we're formatting these
    function_end = '}\n'
    makedata = '    [make_row(row)|row<-data]\n'
    makedata_basic = '    data\n'

class OscarLanguage(DownloadLanguage):
    name = 'oscar'

    def initialize(self, cols):
        from lmfdb.number_fields.number_field import PolynomialCol
        if any(isinstance(c, PolynomialCol) for c in cols):
            return '\nRx,x = PolynomialRing(QQ)\n\n'
        else:
            return '\n'

class TextLanguage(DownloadLanguage):
    name = 'text'
    delim_start = ' ['
    delim_end = ' ]'
    make_data_comment = ''
    file_suffix = '.txt'

class Downloader():
    """
    A class for downloading data in a uniform way.

    You should inherit from this class, providing

    - a ``table`` attribute, which is a PostgresTable
    - a ``title`` attribute (e.g. ``'Genus 2 curves'``), used at the beginning
      of the top comment.  Defaults to table name.
    - a ``short_name`` attribute (e.g. ``'curves'``), which is used in comments.
      Defaults to lower cased title.
    - a ``var_name`` attribute (e.g. ``'curves'``), used as a variable name in comments.
      Defaults to short_name, with spaces replaced by underscores.
    - a ``columns`` attribute, which is either a list of columns,
      a string (indicating a single column),
      or a dictionary with keys language names and values the appropriate columns.
      In all cases, exclude the label column, which is prepended automatically.
    - a ``column_wrappers`` attribute, which is a dictionary with column names
      as keys and unary functions f as values; data for the named columns
      be mapped through f when being added to the download data (column names
      that do not appear in columns will be ignored)
    - a ``data_format`` attribute, which is a list of strings
      (defaulting to the names of the columns), not including the label
    - a ``data_description`` attribute (optional), which is a list of strings
      describing the data format (or a string if there is only one line)
    - a ``function_body`` attribute, which is a dictionary
      with keys the download languages, and values
      lists of strings giving lines of a function to
      reconstruct appropriate objects in that system.
      For skipped languages, no function will be defined.

    You may also want to override the default behavior of the `to_lang` function,
    which is used to print the values of the columns.

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
        'text': TextLanguage(),
        'oscar': OscarLanguage(),
    }
    postprocess = None
    def get(self, name, default=None):
        if hasattr(self, name):
            return getattr(self, name)
        else:
            return default

    def _wrap(self, result, filebase, lang, title=None):
        """
        Adds the time downloaded as a comment, make into a flask response.
        """
        if title is None:
            title = self.get('title', self.table.search_table)
        filename = filebase + lang.file_suffix
        c = lang.comment_prefix
        mydate = time.strftime("%d %B %Y")
        s = '\n'
        s += c + ' %s downloaded from the LMFDB on %s.\n' % (title, mydate)
        s += result
        bIO = BytesIO()
        bIO.write(s.encode('utf-8'))
        bIO.seek(0)
        return send_file(bIO, download_name=filename, as_attachment=True)

    def _wrap_generator(self, generator, filebase, lang='text', title=None, add_ext=True):
        """
        As for _wrap, but uses a stream.  For use with large files.

        INPUT:

        - generator -- yields the contents of the file, usually one line at a time.
        """
        if title is None:
            title = self.get('title', self.table.search_table)
        filename = filebase
        if add_ext:
            filename += self.file_suffix[lang]
        c = self.comment_prefix[lang]
        mydate = time.strftime("%d %B %Y")

        @stream_with_context
        def _generator():
            yield '\n' + c + ' %s downloaded from the LMFDB on %s.\n' % (title, mydate)
            yield from generator

        headers = Headers()
        headers.add('Content-Disposition', 'attachment', filename=filename)
        resp = Response(_generator(), mimetype='text/plain', headers=headers)
        return resp

    def modify_query(self, query):
        """
        This is a hook for downloaders to modify a query before executing it.
        It is used in artin representations to only include non-hidden representations
        """
        pass

    def __call__(self, info):
        """
        Generate download file for a list of search results determined by the
        ``query`` field in ``info``.
        """
        lang = self.languages[info.get(self.lang_key, 'text')]
        filename = self.get('filename_base', self.table.search_table)
        ts = datetime.datetime.now().strftime("%m%d_%H%M")
        filename = f"lmfdb_{filename}_{ts}"
        title = self.get('title', self.table.search_table)
        short_name = self.get('short_name', title.split(' ')[-1].lower())
        var_name = self.get('var_name', short_name.replace('_',' '))
        make_data_comment = lang.make_data_comment
        if make_data_comment:
            make_data_comment = make_data_comment.format(short_name=short_name, var_name=var_name)
        columns = info["columns"]
        proj = columns.db_cols
        cols = [c for c in columns.columns_shown(info) if c.default(info)]
        data_format = self.get('data_format', [c.title for c in cols])
        if isinstance(data_format, dict):
            data_format = data_format[lang.name]
        # reissue query here
        try:
            query = literal_eval(info.get('query', '{}'))
            self.modify_query(query)
            data = list(self.table.search(query, projection=proj))
            if self.postprocess is not None:
                data = self.postprocess(data, info, query)
            #res_list = [[c.download_type.repr(lang, c.get(rec)) for c in cols] for rec in data]
            res_list = [[c.download(rec, lang) for c in cols] for rec in data]
        except Exception as err:
            return abort(404, "Unable to parse query: %s" % err)
        #print("RES LIST", res_list)
        c = lang.comment_prefix
        s = c + ' Query "%s" returned %d %s.\n\n' %(str(info.get('query')), len(data), short_name if len(data) == 1 else short_name)
        s += c + ' Each entry in the following data list has the form:\n'
        s += c + '    [' + ', '.join(data_format) + ']\n'
        data_desc = self.get('data_description')
        if isinstance(data_desc, dict):
            data_desc = data_desc[lang.name]
        if data_desc is not None:
            if isinstance(data_desc, str):
                data_desc = [data_desc]
            for line in data_desc:
                s += c + ' %s\n' % line
        if make_data_comment:
            s += c + '\n'
            s += c + ' ' + make_data_comment  + '\n'
        s += '\n\n'
        column_names = [(c.name if c.download_col is None else c.download_col) for c in cols]
        s += lang.assign("columns", lang.to_lang(column_names))
        s += lang.assign("data", lang.to_lang(res_list, level=0))
        s += lang.initialize(cols)
        if make_data_comment:
            for c in cols:
                if not c.inline:
                    func_body = "    " + c.cell_function_body(lang).replace("\n", "\n    ")
                    s += lang.func_start(c.cell_function_name, "x")
                    s += func_body + '\n'
                    s += lang.function_end
            if any(c.cell_function_name is not None for c in cols):
                rowline = "    " + lang.return_keyword + lang.delim_start
                for i, c in enumerate(cols):
                    if i:
                        rowline += ","
                    if c.cell_function_name is None:
                        rowline += f"row[{i + lang.offset}]"
                    else:
                        rowline += f"{c.cell_function_name}(row[{i + lang.offset}])"
                rowline += lang.delim_end + lang.line_end + "\n"
                s += '\n' + lang.func_start("make_row", "row") + rowline + lang.function_end
                s += "\n\n" + lang.func_start("make_data", "") + lang.makedata + lang.function_end
            else:
                s += "\n\n" + lang.func_start("make_row", "data") + lang.makedata_basic + lang.function_end
                s += "\n\n" + lang.func_start("make_data", "") + lang.makedata_basic + lang.function_end
        return self._wrap(s, filename, lang=lang)
