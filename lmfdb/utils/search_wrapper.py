from random import randrange
from flask import render_template, jsonify, redirect
from psycopg2.extensions import QueryCanceledError, binary_types
from psycopg2.errors import NumericValueOutOfRange
from sage.misc.decorators import decorator_keywords
from sage.misc.cachefunc import cached_function

from lmfdb.app import app, ctx_proc_userdata, is_debug_mode
from lmfdb.utils.search_parsing import parse_start, parse_count, SearchParsingError
from lmfdb.utils.utilities import flash_error, flash_info, flash_success, to_dict
from lmfdb.utils.completeness import results_complete

# For diagram_wrap:
from psycodict.base import number_types
from .search_boxes import SelectBox, CountBox


def use_split_ors(info, query, split_ors, offset, table):
    """
    Whether to split the $or part of a query into multiple queries when passing to postgres.

    INPUT:

    - ``info`` -- the info dictionary passed in from the front end
    - ``query`` -- the processed query dictionary for passage to postgres
    - ``split_ors`` -- either None (never split ors), or a list of fields in ``query['$or']`` whose presence will lead to splitting ors.
    - ``offset`` -- the current offset for the query
    - ``table`` -- the search table on which the query will be executed
    """
    return (
        split_ors is not None
        and len(query.get("$or", [])) > 1
        and any(field in opt for field in split_ors for opt in query["$or"])
        # We don't support large offsets since sorting in Python requires
        # fetching all records, starting from 0
        and offset < table._count_cutoff
    )


class Wrapper:
    def __init__(
        self,
        f,
        template,
        table,
        title,
        err_title,
        postprocess=None,
        one_per=None,
        **kwds,
    ):
        self.f = f
        self.template = template
        self.table = table
        self.title = title
        self.err_title = err_title
        self.postprocess = postprocess
        self.one_per = one_per
        self.kwds = kwds

    def get_sort(self, info, query):
        sort = query.pop("__sort__", None)
        SA = info.get("search_array")
        if sort is None and SA is not None and SA.sorts is not None:
            sorts = (
                SA.sorts.get(SA._st(info), [])
                if isinstance(SA.sorts, dict)
                else SA.sorts
            )
            sord = info.get("sort_order", "")
            sop = info.get("sort_dir", "")
            for name, display, S in sorts:
                if name == sord:
                    if sop == "op":
                        return [
                            (col, -1) if isinstance(col, str) else (col[0], -col[1])
                            for col in S
                        ]
                    return S
        return sort

    def make_query(self, info, random=False):
        query = {}
        template_kwds = {key: info.get(key, val()) for key, val in self.kwds.items()}
        try:
            errpage = self.f(info, query)
        except Exception as err:
            # Errors raised in parsing; these should mostly be SearchParsingErrors
            if is_debug_mode():
                raise
            info["err"] = str(err)
            err_title = query.pop("__err_title__", self.err_title)
            return render_template(
                self.template, info=info, title=err_title, **template_kwds
            )
        else:
            err_title = query.pop("__err_title__", self.err_title)
        if errpage is not None:
            return errpage
        table = query.pop("__table__", self.table)
        sort = self.get_sort(info, query)
        # We want to pop __title__ even if overridden by info.
        title = query.pop("__title__", self.title)
        title = info.get("title", title)
        template = query.pop("__template__", self.template)
        one_per = query.pop("__one_per__", self.one_per)
        if isinstance(one_per, str):
            one_per = [one_per]
        return query, sort, table, title, err_title, template, one_per

    def query_cancelled_error(
        self, info, query, err, err_title, template, template_kwds
    ):
        ctx = ctx_proc_userdata()
        flash_error(
            'The search query took longer than expected! Please try again later, or use https://beta.lmfdb.org.  If your search still times out, please help us improve by reporting this error  <a href="%s" target=_blank>here</a>.'
            % ctx["feedbackpage"]
        )
        info["err"] = str(err)
        info["query"] = dict(query)
        return render_template(
            template, info=info, title=self.err_title, **template_kwds
        )

    def raw_parsing_error(self, info, query, err, err_title, template, template_kwds):
        flash_error("Error parsing %s.", str(err))
        info["err"] = str(err)
        info["query"] = dict(query)
        return render_template(
            template, info=info, title=self.err_title, **template_kwds
        )

    def oob_error(self, info, query, err, err_title, template, template_kwds):
        # The error string is long and ugly, so we just describe the type of issue
        flash_error("Input number larger than allowed by integer type in database.")
        info["err"] = str(err)
        info["query"] = dict(query)
        return render_template(
            template, info=info, title=self.err_title, **template_kwds
        )


class SearchWrapper(Wrapper):
    def __init__(
        self,
        f,
        template="search_results.html",
        table=None,
        title=None,
        err_title=None,
        per_page=50,
        shortcuts={},
        longcuts={},
        columns=None,
        projection=1,
        url_for_label=None,
        cleaners={},
        postprocess=None,
        split_ors=None,
        random_projection=0,  # i.e., the label_column
        **kwds,
    ):
        Wrapper.__init__(
            self, f, template, table, title, err_title, postprocess, **kwds
        )
        self.per_page = per_page
        self.shortcuts = shortcuts
        self.longcuts = longcuts
        self.columns = columns
        if columns is None:
            self.projection = projection
        else:
            self.projection = columns.db_cols
        self.url_for_label = url_for_label
        self.cleaners = cleaners
        self.split_ors = split_ors
        self.random_projection = random_projection

    def __call__(self, info):
        info = to_dict(info, exclude=["bread"])  # I'm not sure why this is required...
        #  if search_type starts with 'Random' returns a random label
        search_type = info.get("search_type", info.get("hst", ""))
        if search_type == "List":
            # Backward compatibility
            search_type = ""
        info["search_type"] = search_type
        info["columns"] = self.columns
        random = info["search_type"].startswith("Random")
        template_kwds = {key: info.get(key, val()) for key, val in self.kwds.items()}
        for key, func in self.shortcuts.items():
            if info.get(key, "").strip():
                try:
                    return func(info)
                except Exception as err:
                    # Errors raised in jump box, for example
                    # Using the search results is an okay default, though some
                    # jump boxes will use their own error processing
                    if is_debug_mode():
                        raise
                    if "%s" in str(err):
                        flash_error(str(err), info[key])
                    else:
                        flash_error(str(err))
                    info["err"] = str(err)
                    return render_template(
                        self.template, info=info, title=self.err_title, **template_kwds
                    )
        data = self.make_query(info, random)
        if not isinstance(data, tuple):
            return data
        query, sort, table, title, err_title, template, one_per = data
        if random:
            query.pop("__projection__", None)
        proj = query.pop("__projection__", self.projection)
        # It's fairly common to add virtual columns in postprocessing that are then used in MultiProcessedCols.
        # These virtual columns won't be present in the database, so we just strip them out
        # We have to do this here since we didn't have access to the table in __init__
        if isinstance(proj, list):
            proj = [col for col in proj if col in table.search_cols]
        if "result_count" in info:
            if one_per:
                nres = table.count_distinct(one_per, query)
            else:
                nres = table.count(query)
            return jsonify({"nres": str(nres)})
        count = parse_count(info, self.per_page)
        start = parse_start(info)
        try:
            split_ors = not one_per and use_split_ors(
                info, query, self.split_ors, start, table
            )
            if random:
                # Ignore __projection__: it's intended for searches
                if split_ors:
                    queries = table._split_ors(query)
                else:
                    queries = [query]
                if len(queries) > 1:
                    # The following method won't produce a uniform distribution
                    # if there's overlap between queries.  But it's simple,
                    # and in many use cases (e.g. galois group for number fields)
                    # the subqueries are disjoint.
                    counts = [table.count(Q) for Q in queries]
                    pick = randrange(sum(counts))
                    accum = 0
                    for Q, cnt in zip(queries, counts):
                        accum += cnt
                        if pick < accum:
                            query = Q
                            break
                label = table.random(query, projection=self.random_projection)
                if label is None:
                    res = []
                    # ugh; we have to set these manually
                    info["query"] = dict(query)
                    info["number"] = 0
                    info["count"] = count
                    info["start"] = start
                    info["exact_count"] = True
                else:
                    return redirect(self.url_for_label(label), 307)
            else:
                res = table.search(
                    query,
                    proj,
                    limit=count,
                    offset=start,
                    sort=sort,
                    info=info,
                    one_per=one_per,
                    split_ors=split_ors,
                )
        except QueryCanceledError as err:
            return self.query_cancelled_error(
                info, query, err, err_title, template, template_kwds
            )
        except SearchParsingError as err:
            # These can be raised when the query includes $raw keys.
            return self.raw_parsing_error(
                info, query, err, err_title, template, template_kwds
            )
        except NumericValueOutOfRange as err:
            # This is caused when a user inputs a number that's too large for a column search type
            return self.oob_error(info, query, err, err_title, template, template_kwds)
        else:
            try:
                if self.cleaners:
                    for v in res:
                        for name, func in self.cleaners.items():
                            v[name] = func(v)
                if self.postprocess is not None:
                    res = self.postprocess(res, info, query)
            except ValueError as err:
                # Errors raised in postprocessing
                flash_error(str(err))
                info["err"] = str(err)
                return render_template(
                    template, info=info, title=err_title, **template_kwds
                )
            for key, func in self.longcuts.items():
                if info.get(key, "").strip():
                    return func(res, info, query)
            info["results"] = res
            # Display warning message if user searched on column(s) with null values
            if query:
                nulls = table.stats.null_counts()
                try:
                    complete, msg, caveat = results_complete(table.search_table, query, table._db, info.get("search_array"))
                    if complete:
                        flash_success("The results below are complete, since the LMFDB contains all " + msg)
                    elif nulls: # TODO: We already run a version of this inside results_complete.  Should be combined
                        search_columns = table._columns_searched(query)
                        nulls = {col: cnt for col, cnt in nulls.items() if col in search_columns}
                        col_display = {}
                        if "search_array" in info:
                            for row in info["search_array"].refine_array:
                                if isinstance(row, (list, tuple)):
                                    for item in row:
                                        if hasattr(item, "name") and hasattr(item, "label"):
                                            col_display[item.name] = item.label
                            for col, cnt in list(nulls.items()):
                                override = info["search_array"].null_column_explanations.get(col)
                                if override is False:
                                    del nulls[col]
                                elif override:
                                    nulls[col] = override
                                else:
                                    nulls[col] = f"{col_display.get(col, col)} ({cnt} objects)"
                        else:
                            for col, cnt in list(nulls.items()):
                                nulls[col] = f"{col} ({cnt} objects)"
                        if nulls:
                            msg = 'Search results may be incomplete due to <a href="Completeness">uncomputed quantities</a>: '
                            msg += ", ".join(nulls.values())
                            flash_info(msg)
                    if caveat:
                        flash_info("The completeness " + caveat)
                except Exception as err:
                    import traceback
                    msg = f"There was an error in the completeness checking code, so the search results below may or may not be complete: \n{err}"
                    flash_info(msg)
                    msg += "\n" + traceback.format_exc()
                    app.logger.warning(msg)
            return render_template(template, info=info, title=title, **template_kwds)


class CountWrapper(Wrapper):
    """
    A variant on search wrapper that returns a dictionary of counts, grouped by values of specified columns.

    The default postprocessor fills in 0s and Nones based on the ``overall`` dictionary, which should give the counts for the empty query
    """

    def __init__(
        self,
        f,
        template,
        table,
        groupby,
        title,
        err_title,
        postprocess=None,
        overall=None,
        **kwds,
    ):
        Wrapper.__init__(
            self, f, template, table, title, err_title, postprocess=postprocess, **kwds
        )
        self.groupby = groupby
        if postprocess is None and overall is None:

            @cached_function
            def overall():
                return table.stats.column_counts(groupby)

        self.overall = overall

    def __call__(self, info):
        info = to_dict(info, exclude=["bread"])  # I'm not sure why this is required...
        data = self.make_query(info)
        if not isinstance(data, tuple):
            return data  # error page
        query, sort, table, title, err_title, template, one_per = data
        groupby = query.pop("__groupby__", self.groupby)
        template_kwds = {key: info.get(key, val()) for key, val in self.kwds.items()}
        try:
            if query:
                res = table.count(query, groupby=groupby)
            else:
                # We want to use column_counts since it caches results, but it also sorts the input columns and doesn't adjust the results
                res = table.stats.column_counts(groupby)
                sgroupby = sorted(groupby)
                if sgroupby != groupby:
                    perm = [sgroupby.index(col) for col in groupby]
                    res = {
                        tuple(key[i] for i in perm): val for (key, val) in res.items()
                    }
        except QueryCanceledError as err:
            return self.query_cancelled_error(
                info, query, err, err_title, template, template_kwds
            )
        else:
            try:
                if self.postprocess is not None:
                    res = self.postprocess(res, info, query)
                else:
                    for row in info["row_heads"]:
                        for col in info["col_heads"]:
                            if (row, col) not in res:
                                if (row, col) in self.overall():
                                    res[row, col] = 0
                                else:
                                    res[row, col] = None
                info["count"] = (
                    50  # put count back in so that it doesn't show up as none in url
                )

            except ValueError as err:
                # Errors raised in postprocessing
                flash_error(str(err))
                info["err"] = str(err)
                return render_template(
                    template, info=info, title=err_title, **template_kwds
                )
            info["results"] = res
            return render_template(template, info=info, title=title, **template_kwds)


class EmbedWrapper(Wrapper):
    """
    A variant on search wrapper that is intended for embedding a fixed set of search results in a page.

    For an example, see families of modular curves.
    """

    def __init__(
        self,
        f,
        template,
        table,
        title=None,
        err_title=None,
        per_page=50,
        columns=None,
        projection=1,
        **kwds,
    ):
        super().__init__(f, template, table, title, err_title, **kwds)
        self.per_page = per_page
        self.columns = columns
        if columns is None:
            self.projection = projection
        else:
            self.projection = columns.db_cols

    def __call__(self, info):
        info["columns"] = self.columns
        template_kwds = {key: info.get(key, val()) for key, val in self.kwds.items()}
        data = self.make_query(info, False)
        if not isinstance(data, tuple):
            return data
        query, sort, table, title, err_title, template, one_per = data
        proj = query.pop("__projection__", self.projection)
        if isinstance(proj, list):
            proj = [col for col in proj if col in table.search_cols]
        if "result_count" in info:
            if one_per:
                nres = table.count_distinct(one_per, query)
            else:
                nres = table.count(query)
            return jsonify({"nres": str(nres)})
        count = parse_count(info, self.per_page)
        start = parse_start(info)
        try:
            res = table.search(
                query,
                proj,
                limit=count,
                offset=start,
                sort=sort,
                info=info,
                one_per=one_per,
            )
        except QueryCanceledError as err:
            return self.query_cancelled_error(
                info, query, err, err_title, template, template_kwds
            )
        except SearchParsingError as err:
            # These can be raised when the query includes $raw keys.
            return self.raw_parsing_error(
                info, query, err, err_title, template, template_kwds
            )
        except NumericValueOutOfRange as err:
            # This is caused when a user inputs a number that's too large for a column search type
            return self.oob_error(info, query, err, err_title, template, template_kwds)
        else:
            try:
                if self.postprocess is not None:
                    res = self.postprocess(res, info, query)
            except ValueError as err:
                raise
                flash_error(str(err))
                info["err"] = str(err)
                return render_template(
                    template, info=info, title=err_title, **template_kwds
                )
            info["results"] = res
            return render_template(template, info=info, title=title, **template_kwds)


class YieldWrapper(Wrapper):
    """
    A variant on search wrapper that is intended to replace the database table with a Python function
    that yields rows.

    The Python function should also accept a boolean random keyword (though it's allowed to raise an error)
    """

    def __init__(
        self,
        f,  # still a function that parses info into a query dictionary
        template="search_results.html",
        yielder=None,
        title=None,
        err_title=None,
        per_page=50,
        columns=None,
        url_for_label=None,
        **kwds,
    ):
        Wrapper.__init__(
            self, f, template, yielder, title, err_title, postprocess=None, **kwds
        )
        self.per_page = per_page
        self.columns = columns
        self.url_for_label = url_for_label

    def __call__(self, info):
        info = to_dict(info)
        #  if search_type starts with 'Random' returns a random label
        search_type = info.get("search_type", info.get("hst", ""))
        info["search_type"] = search_type
        info["columns"] = self.columns
        random = info["search_type"].startswith("Random")
        template_kwds = {key: info.get(key, val()) for key, val in self.kwds.items()}
        data = self.make_query(info, random)
        if not isinstance(data, tuple):
            return data
        query, sort, yielder, title, err_title, template, one_per = data
        if "result_count" in info:
            if one_per:
                nres = yielder(query, one_per=one_per, count=True)
            else:
                nres = yielder(query, count=True)
            return jsonify({"nres": str(nres)})
        count = parse_count(info, self.per_page)
        start = parse_start(info)
        try:
            if random:
                label = yielder(query, random=True)
                if label is None:
                    res = []
                    # ugh; we have to set these manually
                    info["query"] = dict(query)
                    info["number"] = 0
                    info["count"] = count
                    info["start"] = start
                    info["exact_count"] = True
                else:
                    return redirect(self.url_for_label(label), 307)
            else:
                res = yielder(
                    query,
                    limit=count,
                    offset=start,
                    sort=sort,
                    info=info,
                    one_per=one_per,
                )
        except ValueError as err:
            flash_error(str(err))
            info["err"] = str(err)
            title = err_title
            raise
        else:
            info["results"] = res
        return render_template(template, info=info, title=title, **template_kwds)


class DiagramWrapper(Wrapper):
    """
    A variant on search wrapper that is intended for displaying data in d3.js
    """

    def __init__(
        self,
        f,
        template="d3_diagram",
        table=None,
        title=None,
        url_for_label=None,
        err_title=None,
        columns=None,
        projection=1,
        split_ors=None,
        x_axis_default=None,
        y_axis_default=None,
        result_count_default=1000,
        **kwds,
    ):
        super().__init__(f, template, table, title, err_title, **kwds)
        self.columns = columns
        self.split_ors = split_ors
        self.url_for_label = url_for_label
        self.x_axis_default = x_axis_default
        self.y_axis_default = y_axis_default
        self.result_count_default = result_count_default

        if columns is None:
            self.projection = projection
        else:
            self.projection = columns.db_cols

    def __call__(self, info):
        info = to_dict(info, exclude=["bread"])  # I'm not sure why this is required...
        search_type = info.get("search_type", info.get("hst", ""))
        info["search_type"] = search_type
        info["columns"] = self.columns

        # TODO: modify search array to remove random
        SA = info.get("search_array")

        def flatten(L):         # flatten nested list
            return [x for xs in L for x in xs]

        diagram_fields = {box.name: box.label for box in
                            flatten(SA.browse_array) +
                            flatten(SA.refine_array)}
        
        # Get numerical and binary fields only
        valid_fields = self.table.col_type
        
        numerical_fields = [(name, label) for (name,label) in diagram_fields.items()
                            if valid_fields.get(name) in number_types.keys()]
        binary_fields = [(name, label) for (name, label) in diagram_fields.items()
                            if valid_fields.get(name) == "boolean"]

        print("\t diagram fields are:", diagram_fields)
        
        diagram_boxes = [
            SelectBox(
                name="x-axis",
                label="x-axis",
                options=numerical_fields,
            ),
            SelectBox(
                name="y-axis",
                label="y-axis",
                options=numerical_fields,
            ),
            SelectBox(
                name="color", label="color", options=numerical_fields + binary_fields
            ),
        ]

        # Add diagram-specific boxes if not already present.
        # Checking all fields ensures that we don't add an extra
        # set of boxes when the search is updated (which the naive solution does).

        if not any(x.name == "x-axis" for arr in SA.browse_array for x in arr):
            SA.browse_array = [
                x for x in SA.browse_array if not isinstance(x, CountBox)
            ]
            SA.browse_array.append(diagram_boxes)
        if not any(x.name == "x-axis" for arr in SA.refine_array for x in arr):
            SA.refine_array.append(diagram_boxes + [CountBox()])

        # Override hidden() to exclude "count" from hidden inputs, since we
        # have a visible CountBox in refine_array.  Without this, the form
        # would contain both a hidden <input name="count"> (from hidden_inputs)
        # and the visible CountBox <input name="count">, causing the hidden
        # one to silently override the user's value on re-search.
        original_hidden = SA.hidden

        def hidden_without_count(info):
            return [
                (name, val) for name, val in original_hidden(info) if name != "count"
            ]

        SA.hidden = hidden_without_count

        info["search_array"] = SA

        template_kwds = {key: info.get(key, val()) for key, val in self.kwds.items()}
        data = self.make_query(info, False)
        if not isinstance(data, tuple):
            return data
        query, sort, table, title, err_title, template, one_per = data

        # TODO: make sure we only search for fields that we actually need!

        # It's fairly common to add virtual columns in postprocessing that are then used in MultiProcessedCols.
        # These virtual columns won't be present in the database, so we just strip them out
        # We have to do this here since we didn't have access to the table in __init__
        proj = query.pop("__projection__", self.projection)
        if isinstance(proj, list):
            proj = [col for col in proj if col in table.search_cols]

        count = parse_count(info, self.result_count_default)
        try:
            res = table.search(
                query,
                proj,
                limit=count,
                offset=0,
                sort=sort,
                info=info,
                one_per=one_per,
            )
        except QueryCanceledError as err:
            return self.query_cancelled_error(
                info, query, err, err_title, template, template_kwds
            )
        except SearchParsingError as err:
            # These can be raised when the query includes $raw keys.
            return self.raw_parsing_error(
                info, query, err, err_title, template, template_kwds
            )
        except NumericValueOutOfRange as err:
            # This is caused when a user inputs a number that's too large for a column search type
            return self.oob_error(info, query, err, err_title, template, template_kwds)
        else:
            try:
                if self.postprocess is not None:
                    res = self.postprocess(res, info, query)
            except ValueError as err:
                # Errors raised in postprocessing
                flash_error(str(err))
                info["err"] = str(err)
                return render_template(
                    template, info=info, title=err_title, **template_kwds
                )
            if not res:
                return render_template(
                    template, info=info, title=title, **template_kwds
                )

            def make_d3_data(info, res):
                # TODO: this can probably be refactored
                if "x-axis" not in info:
                    if self.x_axis_default is not None:
                        info["x-axis"] = self.x_axis_default
                    else:
                        info["x-axis"] = numerical_fields[0]

                if "y-axis" not in info:
                    if self.y_axis_default is not None:
                        info["y-axis"] = self.y_axis_default
                    else:
                        info["y-axis"] = numerical_fields[1]

                x_key = info["x-axis"]
                y_key = info["y-axis"]

                col_key = info.get("color")

                # Elliptic curves have "lmfdb_label" and "Clabel"
                label_str = "lmfdb_label" if res[0].get("label") is None else "label"
                print("\t Keys for result:", res[0].keys())
                return [ {"x": str(r[x_key]),
                          "y": str(r[y_key]),
                          "color": str(r.get(col_key)),
                          "path": self.url_for_label(r[label_str]),
                          "label": r[label_str],
                          } for r in res ]

            info["d3_data"] = make_d3_data(info, res)
            # label names for printing above the axes
            info["x-axis-label"] = diagram_fields[info["x-axis"]]
            info["y-axis-label"] = diagram_fields[info["y-axis"]]

            # Display warning message if user searched on column(s) with null values
            return render_template(template, info=info, title=title, **template_kwds)


@decorator_keywords
def search_wrap(f, **kwds):
    return SearchWrapper(f, **kwds)


@decorator_keywords
def count_wrap(f, **kwds):
    return CountWrapper(f, **kwds)


@decorator_keywords
def embed_wrap(f, **kwds):
    return EmbedWrapper(f, **kwds)


@decorator_keywords
def yield_wrap(f, **kwds):
    return YieldWrapper(f, **kwds)


@decorator_keywords
def diagram_wrap(f, **kwds):
    return DiagramWrapper(f, **kwds)
