from .web_display import display_knowl
from sage.structure.unique_representation import UniqueRepresentation


class TdElt():
    _wrap_type = 'td'
    def _add_class(self, D, clsname):
        if 'class' in D:
            D['class'] = D['class'] + ' ' + clsname
        else:
            D['class'] = clsname

    def _wrap(self, typ, **kwds):
        keys = []
        kwds = dict(kwds)
        if hasattr(self, "wrap_mixins"):
            kwds.update(self.wrap_mixins)
        if self.advanced:
            self._add_class(kwds, 'advanced')
        kwds['valign'] = 'top'
        for key, val in kwds.items():
            keys.append(' %s="%s"' % (key, val))
        return "<%s%s>" % (typ, "".join(keys))

    def td(self, colspan=None, nowrap=False, **kwds):
        if colspan is not None:
            kwds['colspan'] = colspan
        if nowrap:
            self._add_class(kwds, 'nowrap')
        return self._wrap("td", **kwds)

class Spacer(TdElt):
    def __init__(self, colspan=None, advanced=False):
        self.colspan = colspan
        self.advanced = advanced

    def input_html(self, info=None):
        return self.td(self.colspan) + "</td>"

    def label_html(self, info=None):
        return self.td(self.colspan) + "</td>"

    def example_html(self, info=None):
        return self.td() + "</td>"

    def has_label(self, info=None):
        return False

class RowSpacer(Spacer):
    def __init__(self, rowheight, advanced=False):
        self.rowheight = rowheight
        self.advanced = advanced

    def tr(self, rowspan=0, **kwds): # used for row spacers
        if rowspan is not None:
            kwds['style'] = "height:%spx" % rowspan
        return self._wrap("tr", **kwds)

    def html(self, info=None):
        return self.tr(self.rowheight) + "</tr>"


class BasicSpacer(Spacer):
    def __init__(self, msg, colspan=1, advanced=False):
        Spacer.__init__(self, colspan=colspan, advanced=advanced)
        self.msg = msg

    def input_html(self, info=None):
        return self.td(self.colspan) + self.msg + "</td>"


class CheckboxSpacer(Spacer):
    def __init__(self, checkbox, colspan=1, advanced=False):
        Spacer.__init__(self, colspan=colspan, advanced=advanced)
        self.checkbox = checkbox

    def html(self, info=None):
        return (
            self.td(self.colspan)
            + self.checkbox._label(info)
            + " "
            + self.checkbox._input(info)
            + "</td>"
        )


class SearchBox(TdElt):
    """
    Class abstracting the input boxes used for LMFDB searches.
    """
    _default_width = 160

    def __init__(
        self,
        name=None,
        label=None,
        knowl=None,
        example=None,
        example_span=None,
        example_span_colspan=1,
        colspan=(1, 1, 1),
        rowspan=(1, 1),
        width=None,
        short_width=None,
        short_label=None,
        advanced=False,
        example_col=False,
        id=None,
        qfield=None,
    ):
        self.name = name
        self.id = id
        self.label = label
        self.knowl = knowl
        self.example = example
        self.example_span = example if example_span is None else example_span
        self.example_span_colspan = example_span_colspan
        if example_col is None:
            example_col = bool(self.example_span)
        self.example_col = example_col
        self.label_colspan, self.input_colspan, self.short_colspan = colspan
        self.label_rowspan, self.input_rowspan = rowspan
        if short_label is None:
            short_label = label
        self.short_label = short_label
        self.advanced = advanced
        self.qfield = name if qfield is None else qfield
        if width is None:
            width = self._default_width
        self.width = width
        self.short_width = self.width if short_width is None else short_width

    def _label(self, info):
        label = self.label if info is None else self.short_label
        if self.knowl is not None:
            knowl = display_knowl(self.knowl, label)
            if knowl is not None:
                return knowl
        return label

    def has_label(self, info):
        label = self.label if info is None else self.short_label
        return bool(label)

    def label_html(self, info=None):
        colspan = self.label_colspan if info is None else self.short_colspan
        return self.td(colspan, rowspan=self.label_rowspan, nowrap=True) + self._label(info) + "</td>"

    def input_html(self, info=None):
        colspan = self.input_colspan if info is None else self.short_colspan
        return self.td(colspan, rowspan=self.input_rowspan) + self._input(info) + "</td>"

    def example_html(self, info=None):
        if self.example_span:
            return (
                self.td(self.example_span_colspan)
                + '<span class="formexample">e.g. %s</span></td>' % self.example_span
            )
        elif self.example_col:
            return "<td></td>"


class TextBox(SearchBox):
    """
    A text box for user input.

    INPUT:

    - ``name`` -- the name of the input (will show up in URL)
    - ``label`` -- the label for the input, shown on browse page
    - ``knowl`` -- a knowl id to apply to the label (you can set as None include a display_knowl directly in the label/short_label if the whole text shouldn't be a knowl link)
    - ``example`` -- the example in the input box
    - ``example_span`` -- the formexample span (defaults to example)
    - ``width`` -- the width of the input element on the browse page
    - ``short_width`` -- the width of the input element on the refine-search page (defaults to width)
    - ``short_label`` -- the label on the refine-search page, if different
    - ``qfield`` -- the corresponding database column (defaults to name).  Not currently used.
    """

    def __init__(
        self,
        name=None,
        label=None,
        knowl=None,
        example=None,
        example_span=None,
        example_span_colspan=1,
        example_value=False,
        colspan=(1, 1, 1),
        rowspan=(1, 1),
        width=160,
        short_width=None,
        short_label=None,
        advanced=False,
        example_col=None,
        id=None,
        qfield=None,
        extra=[],
    ):
        SearchBox.__init__(
            self,
            name,
            label,
            knowl=knowl,
            example=example,
            example_span=example_span,
            example_span_colspan=example_span_colspan,
            colspan=colspan,
            rowspan=rowspan,
            width=width,
            short_width=short_width,
            short_label=short_label,
            advanced=advanced,
            example_col=example_col,
            id=id,
            qfield=qfield,
        )
        self.extra = extra
        self.example_value = example_value

    def _input(self, info):
        keys = self.extra + ['type="text"', 'name="%s"' % self.name]
        if self.id is not None:
            keys.append('id="%s"' % self.id)
        if self.advanced:
            keys.append('class="advanced"')
        if self.example is not None:
            if self.example_value and info is None:
                keys.append('value="%s"' % self.example)
            else:
                keys.append('placeholder="%s"' % self.example)
        if info is None:
            if self.width is not None:
                keys.append('style="width: %spx"' % self.width)
        else:
            if self.short_width is not None:
                keys.append('style="width: %spx"' % self.short_width)
            if self.name in info:
                keys.append('value="%s"' % info[self.name])
        return '<input type="text" ' + " ".join(keys) + "/>"

class SelectBox(SearchBox):
    """
    A select box for user input.

    INPUT:

    - ``name`` -- the name of the input (will show up in URL)
    - ``label`` -- the label for the input, shown on browse page
    - ``options`` -- list of tuples (value, option) for the select options
    - ``knowl`` -- a knowl id to apply to the label (you can set as None include a display_knowl directly in the label/short_label if the whole text shouldn't be a knowl link)
    - ``width`` -- the width of the input element on the browse page
    - ``short_width`` -- the width of the input element on the refine-search page (defaults to width)
    - ``short_label`` -- the label on the refine-search page, if different
    - ``qfield`` -- the corresponding database column (defaults to name).  Not currently used.
    """
    _options = []
    _default_width = 170
    _default_min_width = 85

    def __init__(
        self,
        name=None,
        label=None,
        options=None,
        knowl=None,
        example=None,
        example_span=None,
        example_span_colspan=1,
        colspan=(1, 1, 1),
        rowspan=(1, 1),
        width=None,
        min_width=None,
        short_width=None,
        short_label=None,
        advanced=False,
        example_col=False,
        id=None,
        qfield=None,
        extra=[],
    ):
        SearchBox.__init__(
            self,
            name,
            label,
            knowl=knowl,
            example=example,
            example_span=example_span,
            example_span_colspan=example_span_colspan,
            colspan=colspan,
            rowspan=rowspan,
            width=width,
            short_width=short_width,
            short_label=short_label,
            advanced=advanced,
            example_col=example_col,
            id=id,
            qfield=qfield,
        )
        if options is None:
            options = self._options
        self.options = options
        self.extra = extra
        if min_width is None:
            min_width = self._default_min_width
        self.min_width = min_width

    def _input(self, info):
        keys = self.extra + ['name="%s"' % self.name]
        if self.id is not None:
            keys.append('id="%s"' % self.id)
        if self.advanced:
            keys.append('class="advanced"')
        if info is None:
            if self.width is not None:
                keys.append('style="width: %spx"' % self.width)
        else:
            if self.short_width is not None:
                keys.append('style="width: %spx"' % self.short_width)
        opts = []
        for value, display in self.options:
            if (
                info is None
                and value == ""
                or info is not None
                and info.get(self.name, "") == value
            ):
                selected = " selected"
            else:
                selected = ""
            if value is None:
                value = ""
            else:
                value = 'value="%s"' % value
            opts.append("<option %s%s>%s</option>" % (value, selected, display))
        return "        <select %s>\n%s\n        </select>" % (
            " ".join(keys),
            "".join("\n" + " " * 10 + opt for opt in opts),
        )

class NoEg(SearchBox):
    def example_html(self, info=None):
        return (
            self.td(self.example_span_colspan)
            + '<span class="formexample">%s</span></td>' % self.example_span
        )

class TextBoxNoEg(NoEg, TextBox):
    pass

class SelectBoxNoEg(NoEg, SelectBox):
    pass

class HiddenBox(SearchBox):
    def _input(self, info=None):
        keys = ['name="%s"' % self.name]
        if self.advanced:
            keys.append('class="advanced"')
        if info is not None and info.get(self.name):
            keys.append('value="%s"' % info.get(self.name))
        return '<input type="hidden" %s>' % (" ".join(keys),)

class CheckBox(SearchBox):
    def _input(self, info=None):
        keys = ['name="%s"' % self.name, 'value="yes"']
        if self.advanced:
            keys.append('class="advanced"')
        if info is not None and info.get(self.name, False):
            keys.append("checked")
        return '<input type="checkbox" %s>' % (" ".join(keys),)

class SneakyBox(SearchBox):
    """
    Only displayed in result refinement if the corresponding input is present.
    Intended for use in displaying statistics and jump boxes
    """

class SneakyTextBox(TextBox, SneakyBox):
    pass

class SkipBox(TextBox):
    def _input(self, info=None):
        return ""

    def _label(self, info=None):
        return ""


class TextBoxWithSelect(TextBox):
    def __init__(self, name, label, select_box, **kwds):
        self.select_box = select_box
        self.select_box.width = self.select_box.min_width
        self.select_box.short_width = self.select_box.min_width
        TextBox.__init__(self, name, label, **kwds)

    def label_html(self, info=None):
        colspan = self.label_colspan if info is None else self.short_colspan
        return (
                self.td(colspan, nowrap=True, style="text-align-last: justify;")
            + self._label(info)
            + '<span style="margin-left: 10px;"></span>'
            + self.select_box._input(info)
            + "</td>"
        )


class DoubleSelectBox(SearchBox):
    def __init__(self, label, select_box1, select_box2, **kwds):
        self.select_box1 = select_box1
        self.select_box2 = select_box2
        if 'name' not in kwds:
            kwds['name'] = label
        SearchBox.__init__(self, label=label, **kwds)

    def _input(self, info):
        return (
            '<div style="display: flex; justify-content: space-between;">'
            + self.select_box1._input(info)
            + self.select_box2._input(info)
            + "</div>"
        )

class ExcludeOnlyBox(SelectBox):
    _options = [("", ""),
                ("exclude", "exclude"),
                ("only", "only")]

class YesNoBox(SelectBox):
    _options = [("", ""),
                ("yes", "yes"),
                ("no", "no")]

class YesNoMaybeBox(SelectBox):
    _default_min_width = 130
    _options = [("", ""),
                ("yes", "yes"),
                ("not_no", "yes or unknown"),
                ("not_yes", "no or unknown"),
                ("no", "no"),
                ("unknown", "unknown")]

class ParityBox(SelectBox):
    _options = [('', ''),
                ('even', 'even'),
                ('odd', 'odd')]

class ParityMod(SelectBox):
    _default_min_width = 95
    _options = [('', 'any parity'),
                ('even', 'even only'),
                ('odd', 'odd only')]


class SubsetBox(SelectBox):
    _options = [('', 'include'),
                ('exclude', 'exclude'),
                ('exactly', 'exactly'),
                ('subset', 'subset')]

class SubsetNoExcludeBox(SelectBox):
    _options = [('', 'include'),
                ('exactly', 'exactly'),
                ('subset', 'subset')]

class CountBox(TextBox):
    def __init__(self):
        TextBox.__init__(
            self,
            name="count",
            label="Results to display",
            example=50,
            example_col=True,
            example_value=True,
            example_span="")

class ColumnController(SelectBox):
    def __init__(self):
        super().__init__(
            name="column_control",
            knowl="doc.select_search_columns",
            label="Select",
            width=170)

    def _label(self, info):
        if info is None:
            return ""
        C = info.get("columns")
        if C is None:
            return ""
        R = info.get("results")
        if R is None:
            return ""
        return super()._label(info)

    def _input(self, info):
        if info is None:
            print("WARNING: Column controller should not be included on browse page")
            return ""
        C = info.get("columns")
        if C is None:
            print("WARNING: Column controller included but no columns specified in @search_wrap")
            return ""
        R = info.get("results")
        if R is None:
            # can happen if search input error for example
            return ""
        keys = [
            '''onmousedown="this.size=this.length; this.value='';"''',
            '''onmousemove="return false;"''',
            '''onmouseup="this.focus();"''',
            '''onblur="this.size=0; this.value='none';"''',
            '''oninput="control_columns(this);"''',
            '''id="column-selector"''',
        ]
        style="position: absolute; z-index: 9999;"
        if self.short_width is not None:
            style += f'width: {self.short_width}px;'
        keys.append(f'style="{style}"')
        options = [("none", " selected", "columns to display")]
        use_rank = 0 # which rank to iterate over in determining the columns listed in the select
        for col in C.columns_shown(info, 0):
            if col.height > 1 and any(sub.name != col.name for sub in col.show(info, 1)):
                # A ColGroup with columns that should be shown/hidden individually
                use_rank = 1
                break
        for col in C.columns_shown(info, use_rank):
            if col.short_title is None: # probably a spacer column:
                continue
            title = col.short_title.replace("$", "").replace(r"\(", "").replace(r"\)", "").replace("\\", "")
            if col.default(info):
                disp = "✓ " + title # The space is a unicode space the size of an emdash
            else:
                disp = "  " + title # The spaces are unicode, the sizes of an endash and a thinspace
            options.append((col.name, "", disp))
        # options.append(("done", "", "&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;done"))
        options = [f'<option value="{name}"{selected}>{disp}</option>' for name,selected,disp in options]
        return "        <select %s>\n%s\n        </select>" % (
            " ".join(keys),
            "".join("\n" + " " * 10 + opt for opt in options),
        )

class SortController(SelectBox):
    wrap_mixins = {'width': '170px'}
    def __init__(self, options, knowl):
        extra = [
            '''onmousedown="this.size=this.length; this.selectedIndex = -1;"''',
            '''onmousemove="return false;"''',
            '''onmouseup="this.focus();"''',
            '''onblur="blur_sort(this);"''',
            '''oninput="control_sort(this);"''',
            '''id="sort-selecter"''',
            '''style="width: 170px; position: absolute; z-index: 9999;"''',
        ]
        super().__init__(
            name="sort_order",
            label="Sort order",
            options=options,
            knowl=knowl,
            width=None,
            extra=extra,
        )

    #sort_box = SelectBox(
    #    name='sort_order',
    #    options=list(sort),
    #    width=130)
    #sort_dir = SelectBox(
    #    name='sort_dir',
    #    options=[('', '&#9650;'), ('op', '&#9660;')],
    #    width=None,
    #    extra=['style="min-width: 40px; max-width: 40px; padding: 0px;"'],
    #)
    #sort_ord = DoubleSelectBox(
    #    name='sort_combo',
    #    label='Sort order',
    #    knowl=self.sort_knowl,
    #    select_box1=sort_box,
    #    select_box2=sort_dir)

class SearchButton(SearchBox):
    _default_width = 170
    def __init__(self, value, description, **kwds):
        kwds['label'] = kwds.get('label', '')
        SearchBox.__init__(self, **kwds)
        self.value = value
        self.description = description

    def td(self, colspan=None, **kwds):
        kwds = dict(kwds)
        #self._add_class(kwds, 'button')
        return SearchBox.td(self, colspan, **kwds)

    def _input(self, info):
        if info is None:
            onclick = ""
        else:
            onclick = " onclick='resetStart()'"
        btext = "<button type='submit' name='search_type' value='{val}' style='width: {width}px;'{onclick}>{desc}</button>"
        return btext.format(
            width=self.width,
            val=self.value,
            desc=self.description,
            onclick=onclick)

class SearchButtonWithSelect(SearchButton):
    def __init__(self, value, description, select_box, **kwds):
        self.select_box = select_box
        self.select_box.width = self.select_box.min_width
        SearchButton.__init__(self, value, description, **kwds)

    def label_html(self, info=None):
        colspan = self.label_colspan if info is None else self.short_colspan
        return (self.td(colspan)
                + '<div style="display: flex; justify-content: space-between;">'
                + self._label(info)
                + '<span style="margin-left: 5px;"></span>'
                + self.select_box._input(info)
                + "</div>"
                + "</td>")

class SearchArray(UniqueRepresentation):
    """
    This class is used to represent the grid of inputs in a browse or search array.
    The goal is to be able to use create one object for each input which can then
    be reused in multiple locations.

    You should set the following attributes/functions to make this work.

    - ``browse_array`` and ``refine_array`` -- each a list of lists of ``SearchBox`` objects.
        You can also override ``main_array()`` for more flexibility.
        Will be passed ``info=None`` for the browse page, or the info dictionary for refining search
    - ``sort_order`` -- a function of ``info`` returning a list of pairs, the url value
        and display value for the sort options.  You may also want to set the ``sort_knowl`` attribute
    - ``search_types`` -- returns a list of pairs giving the url value and display value
        for the search buttons
    - ``hidden`` -- returns a list of pairs giving the name and info key for the hidden inputs
    """
    _ex_col_width = 170 # only used for box layout
    sort_knowl = None
    sorts = None # Provides an easy way to implement sort_order: a list of triples (name, display, sort -- as a list of columns or pairs (col, +-1)), or a dictionary indexed on the value of self._st()
    null_column_explanations = {} # Can override the null warnings for a column by including False as a value, or customize the error message by giving a formatting string (see search_wrapper.py)
    noun = "result"
    plural_noun = "results"
    def sort_order(self, info):
        # Override this method to add a dropdown for sort order
        if self.sorts is not None:
            sorts = self.sorts if isinstance(self.sorts, list) else self.sorts.get(self._st(info))
            if sorts is not None:
                #for name, display, prefix in self.sorts:
                #    yield (name, display + " &#9650;")
                #    yield (name + "op", display + " &#9660;")
                return [(name, display) for (name, display, sort_order) in sorts]

    def _search_again(self, info, search_types):
        if info is None:
            return search_types
        st = self._st(info)
        return [(st, "Search again")] + [(v, d) for v, d in search_types if v != st]

    def search_types(self, info):
        # Override this method to change the displayed search buttons
        if info is None:
            return [("List", "List of %s" % self.plural_noun), ("Random", "Random %s" % self.noun)]
        else:
            return [("List", "Search again"), ("Random", "Random %s" % self.noun)]

    def hidden(self, info):
        # Override this method to change the hidden inputs
        return [("start", "start"), ("count", "count"), ("hst", "search_type")]

    def main_array(self, info):
        if info is None:
            return self.browse_array
        else:
            return self.refine_array

    def _print_table(self, grid, info, layout_type):
        if not grid:
            return ""
        lines = []
        for row in grid:
            if isinstance(row, Spacer):
                lines.append("\n      " + row.html(info))
            elif layout_type == 'vertical':
                if any(box.has_label(info) for box in row):
                    labels = [box.label_html(info) for box in row if (not isinstance(box, SneakyBox) or info is None or box.name in info)]
                    lines.append("".join("\n      " + label for label in labels))
                inputs = [box.input_html(info) for box in row if (not isinstance(box, SneakyBox) or info is None or box.name in info)]
                lines.append("".join("\n      " + inp for inp in inputs))
            elif layout_type == 'horizontal':
                cols = []
                for box in row:
                    if isinstance(box, SneakyBox) and info is not None and box.name not in info:
                        continue
                    cols.append(box.label_html(info))
                    cols.append(box.input_html(info))
                    ex = box.example_html(info)
                    if ex:
                        cols.append(ex)
                lines.append("".join("\n      " + col for col in cols))
            elif layout_type == 'box':
                top_cols = []
                bot_cols = []
                for box in row:
                    if isinstance(box, SneakyBox) and info is not None and box.name not in info:
                        continue
                    top_cols.append(box.label_html(info))
                    bot_cols.append(box.input_html(info))
                    ex = box.example_html(info)
                    if ex:
                        top_cols.append('<td width="%s"></td>' % self._ex_col_width)
                        bot_cols.append(ex)
                lines.append("".join("\n      " + col for col in top_cols))
                lines.append("".join("\n      " + col for col in bot_cols))
        return (
            '  <table border="0">'
            + "".join("\n    <tr>" + line + "\n    </tr>" for line in lines)
            + "\n  </table>"
        )

    def _st(self, info):
        if info is not None:
            return info.get("search_type", info.get("hst", "List"))

    def dynstats_array(self, info):
        if self._st(info) == "DynStats":
            array = [RowSpacer(30)]
            vheader = BasicSpacer("Variables")
            vheader.wrap_mixins = {"class": "table_h2"}
            array.append([vheader])
            for i in [1,2]:
                cols = SelectBox(
                    name="col%s" % i,
                    id="col%s_select" % i,
                    label="",
                    width=150,
                    options=info["stats"]._dynamic_cols,
                    extra=['onchange="set_buckets(this, \'buckets%s\')"'%i])
                buckets = TextBox(
                    name="buckets%s" % i,
                    id="buckets%s" % i,
                    label="Buckets" if i == 1 else "",
                    knowl="stats.buckets" if i == 1 else None,
                    width=310)
                totals = CheckBox(
                    name="totals%s" % i,
                    label="Totals" if i == 1 else "",
                    knowl="stats.totals" if i == 1 else None)
                proportions = SelectBox(
                    name="proportions",
                    width=150,
                    options=[("recurse", "Vs unconstrained"),
                             ("rows", "By rows"),
                             ("cols", "By columns"),
                             ("none", "None")],
                    label="Proportions" if i == 1 else "",
                    rowspan=(1, 2),
                    knowl="stats.proportions" if i == 1 else None)
                if i == 1:
                    array.append([cols, buckets, totals, proportions])
                else:
                    array.append([cols, buckets, totals])
            return array
        else:
            return []

    def hidden_inputs(self, info=None):
        if info is None:
            return ""
        else:
            return "\n".join('<input type="hidden" name="%s" value="%s"/>' % (name, info.get(val)) for (name, val) in self.hidden(info))

    def main_table(self, info=None):
        layout_type = "horizontal" if info is None else "vertical"
        s = self._print_table(self.main_array(info), info, layout_type=layout_type)
        dstats = self.dynstats_array(info)
        if dstats:
            s += "\n" + self._print_table(dstats, info, layout_type=layout_type)
        return s

    def has_advanced_inputs(self, info=None):
        for row in self.main_array(info):
            if isinstance(row, TdElt) and row.advanced:
                return True
            for col in row:
                if col.advanced:
                    return True
        return False

    def buttons(self, info=None):
        st = self._st(info)
        buttons = []
        spacer = RowSpacer(8)
        if st == "DynStats":
            buttons.append(SearchButton("DynStats", "Generate statistics"))
        else:
            if st is None:
                buttons.append(BasicSpacer("Display:"))
            for but in self.search_types(info):
                if isinstance(but, TdElt):
                    buttons.append(but)
                else:
                    buttons.append(SearchButton(*but))
            if st is not None:
                sort = self.sort_order(info)
                if sort:
                    spacer = RowSpacer(6)
                    cur_sort = info.get('sort_order', '')
                    cur_dir = info.get('sort_dir', '')
                    options = []
                    for name, disp in sort:
                        if name == cur_sort:
                            if cur_dir == 'op':
                                options.append((name, '▼ ' + disp)) # the space is U+2006, a 1/6 em space
                            else:
                                options.append((name, '▲ ' + disp)) # the space is U+2006, a 1/6 em space
                        else:
                            options.append((name, '  ' + disp)) # the spaces are U+2006 and U+2003, totaling 7/6 em
                    buttons.append(SortController(options, self.sort_knowl))
                buttons.append(ColumnController())
        return self._print_table([spacer,buttons], info, layout_type="vertical")

    def html(self, info=None):
        return "\n".join([self.hidden_inputs(info), self.main_table(info), self.buttons(info)])

    def jump_box(self, info):
        jump_example = info.get("jump_example", getattr(self, "jump_example", ""))
        jump_width = info.get("jump_width", getattr(self, "jump_width", 320))
        jump_egspan = info.get("jump_egspan", getattr(self, "jump_egspan", ""))
        jump_prompt = info.get("jump_prompt", getattr(self, "jump_prompt", "Label"))
        jump_knowl = info.get("jump_knowl", getattr(self, "jump_knowl", ""))
        # We don't use SearchBoxes since we want the example to be below, and the button directly to the right of the input (regardless of how big the example is)
        return """<table><tr><td>%s</td><td><input type='text' name='jump' placeholder='%s' style='width:%spx;' value='%s'></td><td>
<button type='submit'>Find</button></td><td></tr><tr><td></td><td colspan="2"><span class='formexample'>%s</span></td></tr></table>
""" % (display_knowl(jump_knowl, jump_prompt),jump_example, jump_width, info.get("jump", ""), jump_egspan)
