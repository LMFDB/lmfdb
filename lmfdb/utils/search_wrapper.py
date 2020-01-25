from random import randrange
from flask import render_template, jsonify, redirect
from psycopg2.extensions import QueryCanceledError
from sage.misc.decorators import decorator_keywords

from lmfdb.app import ctx_proc_userdata
from lmfdb.utils.search_parsing import parse_start, parse_count
from lmfdb.utils.utilities import flash_error, to_dict


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
        and
        # We don't support large offsets since sorting in Python requires
        # fetching all records, starting from 0
        offset < table._count_cutoff
    )


class Wrapper(object):
    def __init__(self, f, template, table, title, err_title, postprocess=None, **kwds):
        self.f = f
        self.template = template
        self.table = table
        self.title = title
        self.err_title = err_title
        self.postprocess = postprocess
        self.kwds = kwds

    def make_query(self, info, random=False):
        query = {}
        template_kwds = {}
        for key in self.kwds:
            template_kwds[key] = info.get(key, self.kwds[key]())
        try:
            errpage = self.f(info, query)
        except ValueError as err:
            # Errors raised in parsing
            info["err"] = str(err)
            err_title = query.pop("__err_title__", self.err_title)
            return render_template(
                self.template, info=info, title=err_title, **template_kwds
            )
        else:
            err_title = query.pop("__err_title__", self.err_title)
        if errpage is not None:
            return errpage
        sort = query.pop("__sort__", None)
        table = query.pop("__table__", self.table)
        # We want to pop __title__ even if overridden by info.
        title = query.pop("__title__", self.title)
        title = info.get("title", title)
        template = query.pop("__template__", self.template)
        return query, template_kwds, sort, table, title, err_title, template

    def query_cancelled_error(
        self, info, query, err, err_title, template, template_kwds
    ):
        ctx = ctx_proc_userdata()
        flash_error(
            'The search query took longer than expected! Please help us improve by reporting this error  <a href="%s" target=_blank>here</a>.'
            % ctx["feedbackpage"]
        )
        info["err"] = str(err)
        info["query"] = dict(query)
        return render_template(
            template, info=info, title=self.err_title, **template_kwds
        )


class SearchWrapper(Wrapper):
    def __init__(
        self,
        f,
        template,
        table,
        title,
        err_title,
        per_page=50,
        shortcuts={},
        longcuts={},
        projection=1,
        url_for_label=None,
        cleaners={},
        postprocess=None,
        split_ors=None,
        **kwds
    ):
        Wrapper.__init__(
            self, f, template, table, title, err_title, postprocess, **kwds
        )
        self.per_page = per_page
        self.shortcuts = shortcuts
        self.longcuts = longcuts
        self.projection = projection
        self.url_for_label = url_for_label
        self.cleaners = cleaners
        self.split_ors = split_ors

    def __call__(self, info, random=False):
        # If random is True, returns a random label
        info = to_dict(info, exclude=["bread"])  # I'm not sure why this is required...
        for key, func in self.shortcuts.items():
            if info.get(key, "").strip():
                return func(info)
        data = self.make_query(info, random)
        if not isinstance(data, tuple):
            return data
        query, template_kwds, sort, table, title, err_title, template = data
        if random:
            query.pop("__projection__", None)
        proj = query.pop("__projection__", self.projection)
        if "result_count" in info:
            nres = table.count(query)
            return jsonify({"nres": str(nres)})
        count = parse_count(info, self.per_page)
        start = parse_start(info)
        try:
            split_ors = use_split_ors(info, query, self.split_ors, start, table)
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
                label = table.random(query, projection=0)
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
                    split_ors=split_ors,
                )
        except QueryCanceledError as err:
            return self.query_cancelled_error(
                info, query, err, err_title, template, template_kwds
            )
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
        **kwds
    ):
        Wrapper.__init__(
            self, f, template, table, title, err_title, postprocess=postprocess, **kwds
        )
        self.groupby = groupby
        if postprocess is None and overall is None:
            overall = table.stats.column_counts(groupby)
        self.overall = overall

    def __call__(self, info):
        info = to_dict(info, exclude=["bread"])  # I'm not sure why this is required...
        data = self.make_query(info)
        if not isinstance(data, tuple):
            return data  # error page
        query, template_kwds, sort, table, title, err_title, template = data
        try:
            if query:
                res = table.count(query, groupby=self.groupby)
            else:
                res = table.stats.column_counts(self.groupby)
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
                                if (row, col) in self.overall:
                                    res[row, col] = 0
                                else:
                                    res[row, col] = None

            except ValueError as err:
                # Errors raised in postprocessing
                flash_error(str(err))
                info["err"] = str(err)
                return render_template(
                    template, info=info, title=err_title, **template_kwds
                )
            info["results"] = res
            return render_template(template, info=info, title=title, **template_kwds)


@decorator_keywords
def search_wrap(f, **kwds):
    return SearchWrapper(f, **kwds)


@decorator_keywords
def count_wrap(f, **kwds):
    return CountWrapper(f, **kwds)
