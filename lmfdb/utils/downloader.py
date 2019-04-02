import time
from flask import abort, send_file, stream_with_context, Response
from werkzeug.datastructures import Headers
from ast import literal_eval
import StringIO


class Downloader(object):
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
      as keys and unary functions f as values; data for for the named columns
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
    languages = ['magma', 'sage', 'gp', 'text']
    comment_prefix = {
            'magma':'//',
            'sage':'#',
            'gp':'\\\\',
            'text':'#'
            }
    assignment_defn = {
            'magma':':=',
            'sage':' = ',
            'gp':' = ',
            'text':'='
            }
    line_end = {'magma':';',
            'sage':'',
            'gp':'',
            'text':''
            }
    delim_start = {'magma':'[*',
            'sage':'[',
            'gp':'[',
            'text':' ['
            }
    delim_end = {'magma':'*]',
            'sage':']',
            'gp':']',
            'text':' ]'}
    start_and_end = {
            'magma':['[*','*]'],
            'sage':['[',']'],
            'gp':['{[',']}'],
            'text':['[',']']}
    file_suffix = {'magma':'.m','sage':'.sage','gp':'.gp','text':'.txt'}
    function_start = {'magma':['function make_data()'],
                      'sage':['def make_data():'],
                      'gp':['make_data() = ','{']}
    function_end = {'magma':['end function;'],
                    'gp':['}']}
    none = {'gp': 'null', 'sage' : 'None', 'text' : 'NULL', 'magma' : '[]'}
    make_data_comment = {
        'magma': 'To create a list of {short_name}, type "{var_name}:= make_data();"',
        'sage':'To create a list of {short_name}, type "{var_name} = make_data()"',
        'gp':'To create a list of {short_name}, type "{var_name} = make_data()"',
    }

    def to_lang(self, lang, inp, level = 0, prepend = ''):
        if inp is None:
            return self.none[lang]
        if isinstance(inp, str) or isinstance(inp, unicode):
            return '"{0}"'.format(str(inp))
        if isinstance(inp, int):
            return str(inp)
        if level == 0:
            start, end = self.start_and_end[lang]
            sep = ',\n' + prepend
        else:
            start = self.delim_start[lang]
            end = self.delim_end[lang]
            sep = ', '
        try:
            if level == 0:
                begin = start + '\\\n'
            else:
                begin = start
            return begin + sep.join(self.to_lang(lang, c, level = level + 1) for c in inp) + end
        except TypeError:
            # not an iterable object
            return str(inp)

    def assign(self, lang, name, elt, level = 0, prepend = ''):
        return name + ' ' + self.assignment_defn[lang] + ' ' + self.to_lang(lang, elt, level, prepend) + self.line_end[lang] + '\n'


    def get(self, name, default=None):
        if hasattr(self, name):
            return getattr(self, name)
        else:
            return default

    def _wrap(self, result, filebase, lang='text', title=None):
        """
        Adds the time downloaded as a comment, make into a flask response.
        """
        if title is None:
            title = self.get('title', self.table.search_table)
        filename = filebase + self.file_suffix[lang]
        c = self.comment_prefix[lang]
        mydate = time.strftime("%d %B %Y")
        s =  '\n'
        s += c + ' %s downloaded from the LMFDB on %s.\n' % (title, mydate)
        s += result
        strIO = StringIO.StringIO()
        strIO.write(str(s))
        strIO.seek(0)
        return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)

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
            for line in generator:
                yield line
        headers = Headers()
        headers.add('Content-Disposition', 'attachment', filename=filename)
        resp = Response(_generator(), mimetype='text/plain', headers=headers)
        return resp

    def __call__(self, info):
        """
        Generate download file for a list of search results determined by the
        ``query`` field in ``info``.
        """
        lang = info.get(self.lang_key,'text').strip()
        filename = self.get('filename_base', self.table.search_table)
        label_col = self.table._label_col
        title = self.get('title', self.table.search_table)
        short_name = self.get('short_name', title.split(' ')[-1].lower())
        var_name = self.get('var_name', short_name.replace('_',' '))
        make_data_comment = self.get('make_data_comment',{}).get(lang)
        if make_data_comment:
            make_data_comment = make_data_comment.format(short_name=short_name, var_name=var_name)
        func_start = self.get('function_start',{}).get(lang,[])
        func_body = self.get('function_body',{}).get(lang,[])
        func_end = self.get('function_end',{}).get(lang,[])
        if isinstance(self.columns, basestring):
            proj = [self.columns]
        elif isinstance(self.columns, list):
            proj = self.columns
        else:
            proj = self.columns[lang]
        onecol = (len(proj) == 1)
        wo_label = proj
        data_format = self.get('data_format', proj)
        if isinstance(data_format, dict):
            data_format = data_format[lang]
        assert len(data_format) == len(proj)
        if label_col:
            proj = [label_col] + proj
        # set up column wrappers
        cw = self.get('column_wrappers',{})
        id = lambda x: x
        for col in wo_label:
            if not col in cw:
                cw[col] = id
        # reissue query here
        try:
            query = literal_eval(info.get('query','{}'))
            data = list(self.table.search(query, projection=proj))
            if label_col:
                label_list = [res[label_col] for res in data]
            if onecol:
                res_list = [cw[wo_label[0]](res.get(wo_label[0])) for res in data]
            else:
                res_list = [[cw[col](res.get(col)) for col in wo_label]  for res in data]
        except Exception as err:
            return abort(404, "Unable to parse query: %s"%err)
        c = self.comment_prefix[lang]
        s = c + ' Query "%s" returned %d %s.\n\n' %(str(info.get('query')), len(data), short_name if len(data) == 1 else short_name)
        if label_col:
            s += c + ' Below are two lists, one called labels, and one called data (in matching order).\n'
            s += c + ' Each entry in the data list has the form:\n'
        else:
            s += c + ' Each entry in the following data list has the form:\n'
        if onecol:
            s += c + '    ' + data_format[0] + '\n'
        else:
            s += c + '    [' + ', '.join(data_format) + ']\n'
        data_desc = self.get('data_description')
        if isinstance(data_desc, dict):
            data_desc = data_desc[lang]
        if data_desc is not None:
            if isinstance(data_desc, basestring):
                data_desc = [data_desc]
            for line in data_desc:
                s += c + ' %s\n' % line
        if make_data_comment and func_body:
            s += c + '\n'
            s += c + ' ' + make_data_comment  + '\n'
        s += '\n'
        s += self.assign(lang, "labels", label_list)
        s += '\n\n'
        s += self.assign(lang, "data", res_list)
        if func_body:
            s += '\n\n'
            s += '\n'.join(func_start) + '\n'
            s += '    ' + '\n    '.join(func_body) + '\n'
            s += '\n'.join(func_end)
        return self._wrap(s, filename, lang=lang)
