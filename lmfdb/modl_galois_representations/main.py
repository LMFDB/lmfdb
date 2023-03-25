# -*- coding: utf-8 -*-

import re
from lmfdb import db

from flask import render_template, url_for, request, redirect, abort

from sage.all import ZZ, QQ

from lmfdb.utils import (
    SearchArray,
    TextBox,
    TextBoxWithSelect,
    SelectBox,
    SubsetBox,
    YesNoBox,
    CountBox,
    redirect_no_cache,
    display_knowl,
    flash_error,
    search_wrap,
    to_dict,
    parse_ints,
    parse_bool,
    parse_primes,
    parse_rats,
    integer_divisors,
    StatsDisplay,
    comma,
    proportioners,
    totaler,
    web_latex_factored_integer,
)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import (
    SearchColumns, MathCol, CheckCol, SearchCol, LinkCol, ProcessedCol, MultiProcessedCol,
)
from lmfdb.api import datapage

from lmfdb.number_fields.web_number_field import formatfield
from lmfdb.modl_galois_representations import modlgal_page
from lmfdb.modl_galois_representations.web_modlgal import WebModLGalRep, get_bread, codomain, image_pretty

LABEL_RE = re.compile(r"[1-9]\d*.[1-9]\d*.[1-9]\d*.[1-9]\d*")

def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Mod-$\ell$ Galois representation labels', url_for(".labels_page"))]

def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]

def learnmore_list_add(learnmore_label, learnmore_url):
    return learnmore_list() + [(learnmore_label, learnmore_url)]

@modlgal_page.route("/")
def index():
    return redirect(url_for(".index_Q", **request.args))

@modlgal_page.route("/Q/")
def index_Q():
    info = to_dict(request.args, search_array=ModLGalRepSearchArray())
    if len(info) > 1:
        return modlgal_search(info)
    title = r"Mod-$\ell$ Galois representations"
    codomains = ["GL,1,2,1","GL,2,2,1","GL,2,3,1","GL,2,5,1","GSp,4,2,1"]
    info["codomain_list"] = [[codomain(*a.split(",")),a] for a in codomains]
    info["conductor_list"] = ["1-100", "101-1000", "1001-10000"]
    info["stats"] = ModLGalRep_stats()
    return render_template(
        "modlgal_browse.html",
        info=info,
        title=title,
        bread=get_bread(),
        learnmore=learnmore_list(),
    )

@modlgal_page.route("/Q/random/")
@redirect_no_cache
def random_rep():
    label = db.modlgal_reps.random()
    return url_for_modlgal_label(label)

@modlgal_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "modlgal",
        db.modlgal_reps,
        url_for_modlgal_label,
        title=r"Some interesting mod-$\ell$ Galois representations",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list(),
    )

def modlgal_link(label):
    if int(label.split(".")[0]) <= 70:
        return '<a href=%s>%s</a>' % (url_for("modlgal.by_label", label=label), label)
    else:
        return label

@modlgal_page.route("/Q/<label>/")
def by_label(label):
    if not LABEL_RE.fullmatch(label):
        flash_error("Invalid label %s", label)
        return redirect(url_for(".index"))
    rep = WebModLGalRep(label)
    if rep.is_null():
        flash_error(r"There is no mod-$\ell$ Galois representation %s in the database", label)
        return redirect(url_for(".index"))
    return render_template(
        "modlgal_rep.html",
        rep=rep,
        properties=rep.properties,
        friends=rep.friends,
        bread=rep.bread,
        title=rep.title,
        KNOWL_ID=f"modlgal.{label}",
    )

def url_for_modlgal_label(label):
    return url_for(".by_label", label=label)

def modlgal_jump(info):
    return redirect(url_for_modlgal_label(info.get("jump")))

def blankzeros(n):
    return "$%o$"%n if n else ""

modlgal_columns = SearchColumns(
    [
        LinkCol("label", "modlgal.label", "Label", url_for_modlgal_label, default=True),
        MathCol("base_ring_characteristic", "modlgal.base_ring_characteristic", r"$\ell$", default=True),
        MathCol("dimension", "modlgal.dimension", "Dim", short_title="dimension", default=True),
        ProcessedCol("conductor", "modlgal.conductor", "Conductor", web_latex_factored_integer, default=True, align="center"),
        SearchCol("top_slope_rational", "modlgal.top_slope", "Top slope", align="center", default=lambda info: info.get("top_slope")),
        MultiProcessedCol("image", "modlgal.image", "Image", ["image_label", "is_surjective", "algebraic_group", "dimension", "base_ring_order", "base_ring_is_field"],
                          image_pretty, default=True, align="center"),
        SearchCol("image_index", "modgal.image_index", "Index", short_title="image index"),
        SearchCol("image_order", "modgal.image_order", "Order", short_title="image order"),
        CheckCol("is_surjective", "modlgal.is_surjective", "Surjective", default=True),
        CheckCol("is_absolutely_irreducible", "modlgal.is_absolutely_irreducible", "Abs irred", short_title="absolutely irreducible"),
        CheckCol("is_solvable", "modlgal.is_solvable", "Solvable"),
        LinkCol("determinant_label", "modlgal.determinant_label", "Determinant", url_for_modlgal_label, align="center"),
        ProcessedCol("generating_primes", "modlgal.generating_primes", "Generators", lambda ps: "$" + ",".join([str(p) for p in ps]) + "$", align="center"),
        ProcessedCol("kernel_polynomial", "modlgal.kernel_polynomial", "Kernel sibling", formatfield, default=True),
        ProcessedCol("projective_kernel_polynomial", "modlgal.projective_kernel_polynomial", "Projective kernel", formatfield),
    ],
    db_cols=["label", "dimension", "base_ring_characteristic", "base_ring_order", "base_ring_is_field", "algebraic_group", "conductor", "image_label",
             "is_surjective", "is_absolutely_irreducible", "is_solvable", "determinant_label", "kernel_polynomial", "projective_kernel_polynomial",
             "image_index", "image_order", "top_slope_rational", "generating_primes"]
    )

@search_wrap(
    table=db.modlgal_reps,
    title=r"Mod-$\ell$ Galois representation search results",
    err_title=r"Mod-$\ell$ Galois representations search input error",
    shortcuts={"jump": modlgal_jump },
    columns=modlgal_columns,
    bread=lambda: get_bread("Search results"),
    url_for_label=url_for_modlgal_label,
)
def modlgal_search(info, query):
    parse_ints(info, query, "base_ring_characteristic")
    parse_ints(info, query, "dimension")
    parse_ints(info, query, "conductor")
    parse_ints(info, query, "image_index")
    parse_ints(info, query, "image_order")
    if info.get('conductor_type'):
        if info['conductor_type'] == 'prime':
            query['conductor_num_primes'] = 1
            query['conductor_is_squarefree'] = True
        elif info['conductor_type'] == 'prime_power':
            query['conductor_num_primes'] = 1
        elif info['conductor_type'] == 'squarefree':
            query['conductor_is_squarefree'] = True
        elif info['conductor_type'] == 'divides':
            if not isinstance(query.get('conductor'), int):
                err = "You must specify a single level"
                flash_error(err)
                raise ValueError(err)
            else:
                query['conductor'] = {'$in': integer_divisors(ZZ(query['conductor']))}
    parse_primes(info, query, 'conductor_primes', name='ramified primes', mode=info.get('conductor_primes_quantifier'))
    parse_rats(info, query,'top_slope', qfield='top_slope_real',name='Top slope')
    if 'top_slope_real' in query and '/' in info['top_slope']:
        # this code should really go into parse_rats
        a = query['top_slope_real']
        if isinstance(a,dict):
            e = 0.000001
            query['top_slope_real'] = {k : float(QQ(a[k]))-e if '/' in a[k] and k[:2] == '$g' else (float(QQ(a[k]))+e if '/' in a[k] and k[:2] == '$l' else a[k]) for k in a}
        else:
            query['top_slope_rational'] = query.pop('top_slope_real')
    if info.get('codomain'):
        query['algebraic_group'], query['dimension'], query['base_ring_order'], query['base_ring_is_field'] = info.get('codomain').split(',')
    parse_bool(info, query, "is_surjective")
    parse_bool(info, query, "is_solvable")
    parse_bool(info, query, "is_absolutely_irreducible")


class ModLGalRepSearchArray(SearchArray):
    noun = "representation"
    plural_noun = "representations"
    jump_example = "2.2.11.1"
    jump_egspan = "e.g. 2.3.11.1 or 2.4.173.1"
    jump_prompt = "Label"
    jump_knowl = "modlgal.search_input"

    def __init__(self):
        conductor_quantifier = SelectBox(
            name='conductor_type',
            options=[('', ''),
                     ('prime', 'prime'),
                     ('prime_power', 'p-power'),
                     ('squarefree', 'sq-free'),
                     ('divides','divides'),
                     ],
            )
        conductor = TextBoxWithSelect(
            name="conductor",
            knowl="modlgal.conductor",
            label="Conductor",
            example="11",
            example_span="11 or 100-200",
            select_box=conductor_quantifier)
        base_ring_characteristic = TextBox(
            name="base_ring_characteristic",
            knowl="modlgal.base_ring_characteristic",
            label="Characteristic",
            example="2",
            example_span="2, 3, or 5")
        dimension = TextBox(
            name="dimension",
            knowl="modlgal.dimension",
            label="Dimension",
            example="2",
            example_span="1, 2, or 4")
        conductor_primes_quantifier = SubsetBox(
            name="conductor_primes_quantifier")
        conductor_primes = TextBoxWithSelect(
            name="conductor_primes",
            knowl="modlgal.ramified",
            label="Ramified",
            example="11",
            example_span="5,7",
            select_box=conductor_primes_quantifier
        )
        top_slope = TextBox(
            name="top_slope",
            label="Top slope",
            knowl="modlgal.top_slope",
            example="2",
            example_span="2 or 4/3 or 1-1.5"
        )
        codomain_opts = ([('', ''), ('GL,1,2,1', 'GL(1,2)'), ('GL,2,2,1', 'GL(2,2)'), ('GL,2,3,1', 'GL(2,3)'), ('GL,2,5,1', 'GL(2,5)'), ('GSp,4,2,1', 'GSp(4,2)')])
        codomain = SelectBox(
            name="codomain",
            knowl="modlgal.codomain",
            label="Codomain",
            example="GL(2,3)",
            options=codomain_opts)
        surjective = YesNoBox(
            name="is_surjective",
            knowl="modlgal.surjective",
            label="Surjective",
            example_col=True,
        )
        solvable = YesNoBox(
            name="is_solvable",
            knowl="modlgal.solvable",
            label="Solvable",
            example_col=True,
        )
        absolutely_irreducible = YesNoBox(
            name="is_absolutely_irreducible",
            knowl="modlgal.absolutely_irreducible",
            label="Absolutely irreducible",
            example_col=True,
        )
        image_index = TextBox(
            name="image_index",
            knowl="modlgal.image_index",
            label="Image index",
            example="2",
            example_span="12, 10-20")
        image_order = TextBox(
            name="image_order",
            knowl="modlgal.image_order",
            label="Image order",
            example="2",
            example_span="12, 10-20")
        count = CountBox()

        self.browse_array = [
            [conductor, codomain],
            [conductor_primes, surjective],
            [dimension, absolutely_irreducible],
            [top_slope, solvable],
            [base_ring_characteristic, image_index],
            [count, image_order],
        ]

        self.refine_array = [
            [conductor, conductor_primes, dimension, top_slope],
            [codomain, surjective, absolutely_irreducible, solvable],
            [base_ring_characteristic, image_index, image_order]
        ]

    sort_knowl = "modlgal.sort_order"
    sorts = [
        ("label", "label", ["dimension", "base_ring_order", "conductor", "num"]),
        ("conductor", "conductor", ["conductor", "dimension", "base_ring_order", "conductor", "num"]),
        ("characteristic", "characteristic", ["base_ring_characteristic", "dimension", "base_ring_order", "conductor", "num"]),
        ("image_index", "image index", ["image_index", "dimension", "base_ring_order", "conductor", "num"]),
    ]

class ModLGalRep_stats(StatsDisplay):
    def __init__(self):
        self.nreps = comma(db.modlgal_reps.count())
        self.max_cond = db.modlgal_reps.max("conductor")
        self.max_dim = db.modlgal_reps.max("dimension")
        self.max_ell = db.modlgal_reps.max("base_ring_order")

    @property
    def short_summary(self):
        modlgal_knowl = display_knowl("modlgal", title=r"mod-$\ell$ Galois representations")
        return (
            fr'The database currently contains {self.nreps} {modlgal_knowl} of $\Gal_\Q$ of conductor $N\le {self.max_cond}$ and dimension $d\le {self.max_dim}$ for $\ell \le {self.max_ell}$.  You can <a href="{url_for(".statistics")}">browse further statistics</a>.<br><br>'
        )

    @property
    def summary(self):
        modlgal_knowl = display_knowl("modlgal", title=r"mod-$\ell$ Galois representations")
        return (
            fr'The database currently contains {self.nreps} {modlgal_knowl} of $\Gal_\Q$ of conductor $N\le {self.max_cond}$ and dimension $d\le {self.max_dim}$ for $\ell \le {self.max_ell}$.  You can <a href="{url_for(".statistics")}">browse further statistics</a>.<br><br>'
        )

    table = db.modlgal_reps
    baseurl_func = ".index"
    buckets = {'conductor': ['1-100', '101-500', '501-1000', '1001-5000', '5001-10000', '10001-'],
               'dimension': ['1', '2', '4'],
               }
    knowls = {'conductor': 'modlgal.conductor',
              'dimension': 'modgal.dim',
              }
    stat_list = [
        {'cols': ['conductor', 'dimension'],
         'proportioner': proportioners.per_row_total,
         'totaler': totaler()},
    ]

@modlgal_page.route("/Q/stats")
def statistics():
    title = r'Mod-$\ell$ Galois representations: Statistics'
    return render_template("display_stats.html", info=ModLGalRep_stats(), title=title, bread=get_bread('Statistics'), learnmore=learnmore_list())

@modlgal_page.route("/Source")
def how_computed_page():
    t = r'Source and acknowledgments for mod-$\ell$ Galois representation data'
    bread = get_bread('Source')
    return render_template("multi.html",
                           kids=['rcs.source.modlgal',
                           'rcs.ack.modlgal',
                           'rcs.cite.modlgal'],
                           title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@modlgal_page.route("/Completeness")
def completeness_page():
    t = r'Completeness of mod-$\ell$ Galois representation data'
    bread = get_bread('Completeness')
    return render_template("single.html", kid='rcs.cande.modlgal',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@modlgal_page.route("/Reliability")
def reliability_page():
    t = r'Reliability of mod-$\ell$ Galois representation data'
    bread = get_bread('Reliability')
    return render_template("single.html", kid='rcs.rigor.modlgal',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@modlgal_page.route("/Labels")
def labels_page():
    t = r'Labels for mod-$\ell$ Galois representations'
    bread = get_bread('Labels')
    return render_template("single.html", kid='modlgal.label',
                           title=t, bread=bread, learnmore=learnmore_list_remove('labels'))

@modlgal_page.route("/data/<label>")
def modlgal_data(label):
    bread = get_bread([(label, url_for_modlgal_label(label)), ("Data", " ")])
    if LABEL_RE.fullmatch(label):
        return datapage([label], ["modlgal_reps"], title=fr"Mod-$\ell$ Galois representation data - {label}", bread=bread)
    else:
        return abort(404)
