# -*- coding: utf-8 -*-

class MFDataTable(object):
    def __init__(self, **kwds):
        r"""
        For 'one-dimensional' data sets the second skip parameter does not have a meaning but should be present anyway...

        """
        self._skip = kwds.get('skip', [])
        self._limit = kwds.get('limit', [])
        self._keys = kwds.get('keys', [])
        self._skip_rec = 0
        self._props = {}
        if self._limit and self._skip:
            self._nrows = self._limit[0]
            if len(self._limit) > 1:
                self._ncols = self._limit[1]
            else:
                self._ncols = 1
            if len(self._skip) == 2:
                self._skip_rows = self._skip[0]
                self._skip_cols = self._skip[1]
            else:
                self._skip_rec = self._skip[0]
        self._table = dict()
        self._is_set = False
        self._row_heads = []
        self._col_heads = []

    def ncols(self):
        return self._ncols

    def nrows(self):
        return self._nrows

    def get_element(self, i, j):
        return self._table[i][j]

    def set_table(self, **kwds):
        raise NotImplementedError("Method needs to be implemented in subclasses!")

    def table(self):
        if not self._is_set:
            self.set_table()
        return self._table

    def row_heads(self):
        return self._row_heads

    def col_heads(self):
        return self._col_heads

    def prop(self, name=''):
        if name in self._props.keys():
            return self._props[name]
        else:
            return ''
