# -*- coding: utf-8 -*-

import re
from lmfdb import db

from flask import render_template, url_for, request, redirect, abort

from sage.all import ZZ

from lmfdb.utils import (
    SearchArray,
    TextBox,
    TextBoxWithSelect,
    SelectBox,
    SneakyTextBox,
    YesNoBox,
    YesNoMaybeBox,
    CountBox,
    redirect_no_cache,
    display_knowl,
    flash_error,
    search_wrap,
    to_dict,
    parse_ints,
    parse_noop,
    parse_bool,
    parse_floats,
    parse_interval,
    parse_element_of,
    parse_bool_unknown,
    parse_nf_string,
    parse_nf_jinv,
    integer_divisors,
    StatsDisplay,
    Downloader,
    comma,
    proportioners,
    totaler,
)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import (
    SearchColumns, MathCol, FloatCol, CheckCol, LinkCol, ProcessedCol, MultiProcessedCol,
)
from lmfdb.utils.search_parsing import search_parser
from lmfdb.api import datapage
from lmfdb.backend.encoding import Json

from lmfdb.number_fields.number_field import field_pretty
from lmfdb.number_fields.web_number_field import nf_display_knowl
from lmfdb.hilbert_modular_surfaces import hmsurface_page
from lmfdb.hilbert_modular_surfaces.web_hmsurface import (
    WebHMSurface, get_bread,
    #canonicalize_name, name_to_latex, factored_conductor,
    #formatted_dims, url_for_EC_label, url_for_ECNF_label, showj_nf,
)
from string import ascii_lowercase

LABEL_RE = re.compile(r"\d+\.\d+\.\d+\.\d+-\d+\.\d+-\d+\.\d+-[sg]l-[01f]")
#NAME_RE = re.compile(r"X_?(0|1|NS|NS\^?\+|SP|SP\^?\+|S4)?\(\d+\)")

def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Hilbert surface labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]

@hmsurface_page.route("/")
def index():
    return redirect(url_for(".index_Q", **request.args))

@hmsurface_page.route("/Q/")
def index_Q():
    info = to_dict(request.args, search_array=HMSurfaceSearchArray())
    if len(info) > 1:
        return hmsurface_search(info)
    title = r"Hilbert modular surfaces"
    info["discr_list"] = ["5", "8", "12", "13", "17-47", "53-97", "101-"]
    info["level_norm_list"] = ["1", "2-4", "5-8", "9-12", "13-16", "17-23", "24-"]
    info["kodaira_list"] = ["-1", "0", "1", "2"]
    info["stats"] = HMSurface_stats()
    return render_template(
        "hmsurface_browse.html",
        info=info,
        title=title,
        bread=get_bread(),
        learnmore=learnmore_list(),
    )

@hmsurface_page.route("/Q/random/")
@redirect_no_cache
def random_surface():
    label = db.hmsurfaces_invs.random()
    return url_for_hmsurface_label(label)

@hmsurface_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "hmsurface",
        db.hmsurfaces_invs,
        url_for_hmsurface_label,
        title="Some interesting modular surfaces",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list(),
    )

@hmsurface_page.route("/Q/<label>/")
def by_label(label):
    if not LABEL_RE.fullmatch(label):
        flash_error("Invalid label %s", label)
        return redirect(url_for(".index"))
    surface = WebHMSurface(label)
    if surface.is_null():
        flash_error("There is no modular surface %s in the database", label)
        return redirect(url_for(".index"))
    return render_template(
        "hmsurface.html",
        surface=surface,
        properties=surface.properties,
        friends=surface.friends,
        bread=surface.bread,
        title=surface.title,
        downloads=surface.downloads,
        KNOWL_ID=f"hmsurface.{label}",
        learnmore=learnmore_list(),
    )

def url_for_hmsurface_label(label):
    return url_for(".by_label", label=label)
    
def hmsurface_jump(info):
    label = info["jump"]
    return redirect(url_for_hmsurface_label(label))

hmsurface_columns = SearchColumns([
    LinkCol("label", "hmsurface.label", "Label", url_for_hmsurface_label, default=True),
    MathCol("chi", "hmsurface.chi", "Arithmetic genus", default=True),
])

@search_wrap(
    table=db.hmsurfaces_invs,
    title="Hilbert modular surface search results",
    err_title="Hilbert modular surfaces search input error",
    shortcuts={"jump": hmsurface_jump},
    columns=hmsurface_columns,
    bread=lambda: get_bread("Search results"),
    url_for_label=url_for_hmsurface_label,
)
def hmsurface_search(info, query):
    parse_ints(info, query, "field_discr")    
    if "group_type" in info:
        if info["group_type"] == "gamma0-gl":
            query["group_type"] = "gl";
            query["gamma_type"] = "0";
        elif info["group_type"] == "gamma0-sl":
            query["group_type"] = "sl";
            query["gamma_type"] = "0";
    if "comp" in info:
        if info["comp"] == "trivial":
            query["component_label"] = "1.1";
        elif info["comp"] == "pp":
            query["is_pp"] = True;
        elif info["comp"] == "other":
            query["component_label"] = {'$not': '1.1'}
            query["is_pp"] = False
    parse_ints(info, query, "narrow_class_nb")
    parse_ints(info, query, "level_norm")
    if info.get('level_norm_quantifier'):
        if info['level_norm_quantifier'] == 'divides':
            if not isinstance(query.get('level_norm'), int):
                err = "You must specify a single level norm"
                flash_error(err)
                raise ValueError(err)
            else:
                query['level_norm'] = {'$in': integer_divisors(ZZ(query['level_norm']))}
    parse_ints(info, query, "h20")
    parse_ints(info, query, "h11")
    parse_ints(info, query, "chi")
    parse_ints(info, query, "K2")
    if info.get('kodaira_dims'):
        try:
            ZZ(info["kodaira_dims"])
        except:
            err = "You must specify a single Kodaira dimension"
            flash_error(err)
            raise ValueError(err)            
        if info['kodaira_quantifier'] == 'exactly':
            query["kodaira_dims"] = [info["kodaira_dims"]]
        elif info['kodaira_quantifier'] == 'possibly':
            query["kodaira_dims"] = {'$contains': info["kodaira_dims"]}
    parse_ints(info, query, "nb_cusps")
    parse_ints(info, query, "nb_ell")
    parse_ints(info, query, "nb_ell2")
    parse_ints(info, query, "nb_ell3")
    parse_ints(info, query, "nb_ell4")
    parse_ints(info, query, "nb_ell5")
    parse_ints(info, query, "nb_ell6")
    parse_ints(info, query, "len_cusp_res")
    parse_ints(info, query, "len_ell_res")
    parse_ints(info, query, "len_res")
    parse_ints(info, query, "euler_nb");
    

class HMSurfaceSearchArray(SearchArray):
    noun = "surface"
    jump_example = "2.2.5.1-1.1-1.1-gl-0"
    jump_egspan = "e.g. 2.2.5.1-1.1-1.1-gl-0"
    jump_prompt = "Label"
    jump_knowl = "hmsurface.search_input"

    #See main.py in modular_curves for select boxes, etc.
    def __init__(self):
        field_discr = TextBox(
            name="field_discr",
            knowl="hmsurface.todo",
            label="Field discriminant",
            example="12",
            example_span="12, 5-100"
        )
        narrow_class_nb = TextBox(
            name="narrow_class_nb",
            knowl="nf.narrow_class_number",
            label="Narrow class number",
            example="1",
            example_span="1, 2-4"
        )
        group_type = SelectBox(
            name="group_type",
            options=[('',''),
                     ('gamma0-gl', 'Gamma_0(N)_b'),
                     ('gamma0-sl', 'Gamma_0^1(N)_b'),
                     ],
            knowl="hmsurface.todo",
            label="Congruence subgroup type",
            example=r"$\Gamma_0(\mathfrak{N})_{\mathfrak{b}}$"
        )
        comp = SelectBox(
            name="comp",
            options=[('',''),
                     ('trivial', 'ideal (1)'),
                     ('pp', 'inverse different'),
                     ('other', 'other'),
                     ],
            knowl="hmsurface.todo",
            label="Component ideal",
            example=r"(1), inverse different"
        )
        level_norm_quantifier = SelectBox(
            name="level_norm_quantifier",
            options=[('',''),
                     ('divides','divides')
                     ],
            min_width=85
        )
        level_norm = TextBoxWithSelect(
            name="level_norm",
            knowl="hmsurface.level",
            label="Norm of level ideal",
            example="1",
            example_span="1, 10-20",
            select_box=level_norm_quantifier
        )
        nb_cusps = TextBox(
            name="nb_cusps",
            knowl="hmsurface.cusps",
            label="Cusps",
            example="1",
            example_span="1, 1-10"
        )
        nb_ell = TextBox(
            name = "nb_ell",
            knowl = "hmsurface.elliptic_point",
            label = "Elliptic points",
            example = "0",
            example_span = "2-10"
        )
        nb_ell2 = TextBox(
            name = "nb_ell2",
            knowl = "hmsurface.elliptic_point",
            label = "Elliptic points of order 2",
            example = "2",
            example_span = "1-5"
        )
        nb_ell3 = TextBox(
            name = "nb_ell2",
            knowl = "hmsurface.elliptic_point",
            label = "Elliptic points of order 3",
            example = "2",
            example_span = "1-5"
        )
        nb_ell4 = TextBox(
            name = "nb_ell2",
            knowl = "hmsurface.elliptic_point",
            label = "Elliptic points of order 4",
            example = "2",
            example_span = "1-5"
        )
        nb_ell5 = TextBox(
            name = "nb_ell2",
            knowl = "hmsurface.elliptic_point",
            label = "Elliptic points of order 5",
            example = "2",
            example_span = "1-5"
        )
        nb_ell6 = TextBox(
            name = "nb_ell2",
            knowl = "hmsurface.elliptic_point",
            label = "Elliptic points of order 6",
            example = "2",
            example_span = "1-5"
        )
        len_ell_res = TextBox(
            name = "len_ell_res",
            knowl = "hmsurface.elliptic_point_resolution",
            label = "Length of elliptic point resolutions",
            example = "2",
            example_span = "1-5"
        )
        len_cusp_res = TextBox(
            name = "len_cusp_res",
            knowl = "hmsurface.cusp_resolution",
            label = "Length of cusp resolutions",
            example = "2",
            example_span = "1-5"
        )
        len_res = TextBox(
            name = "len_res",
            knowl = "hmsurface.resolution",
            label = "Length of all resolutions",
            example = "2",
            example_span = "1-5",
        )
        h20 = TextBox(
            name="h20",
            knowl="hmsurface.hodge_numbers",
            label=r"Hodge number $h^{2,0}$",
            example="0",
            example_span="0, 3-6"
        )
        h11 = TextBox(
            name="h11",
            knowl="hmsurface.hodge_numbers",
            label=r"Hodge number $h^{1,1}$",
            example="13",
            example_span="13, 20-30"
        )        
        chi = TextBox(
            name="chi",
            knowl="hmsurface.chi",
            label="Holomorphic Euler characteristic",
            example="1",
            example_span="1, 3-4",
        )
        K2 = TextBox(
            name="K2",
            knowl="hmsurface.k2",
            label=r"Self-intersection $K^2$",
            example="-3",
            example_span="-3, 0-2"
        )
        euler_nb = TextBox(
            name = "euler_nb",
            knowl = "hmsurface.euler_nb",
            label = "Euler number",
            example = "2",
            example_span = "1-5"
        )        
        kodaira_quantifier = SelectBox(
            name="kodaira_quantifier",
            options=[('exactly', 'exactly'),
                     ('possibly', 'possibly'),
                     ],
            min_width = 85
        )
        kodaira_dims = TextBoxWithSelect(
            name = "kodaira_dims",
            knowl = "hmsurface.kodaira_dimension",
            label = "Kodaira dimension",
            example = "-1",
            example_span = "-1, 2",
            select_box = kodaira_quantifier,
        )
            
        count = CountBox()

        self.browse_array = [
            [field_discr, narrow_class_nb],
            [level_norm, group_type],
            [comp],
            [nb_cusps, nb_ell],
            [nb_ell2, nb_ell3],
            [nb_ell4, nb_ell5],
            [nb_ell6, len_cusp_res],
            [len_ell_res, len_res],            
            [h20, h11],
            [chi, K2],
            [euler_nb, kodaira_dims]
        ]

        self.refine_array = [
            [field_discr, group_type, level_norm, comp],
            [narrow_class_nb, nb_cusps, nb_ell, nb_ell2],
            [nb_ell3, nb_ell4, nb_ell5, nb_ell6],
            [len_cusp_res, len_ell_res, len_res],
            [h20, h11, chi, K2],
            [euler_nb, kodaira_dims]
        ]

    sort_knowl = "hmsurface.sort_order"
    sorts = [
        #No sort yet
    ]

class HMSurface_stats(StatsDisplay):
    def __init__(self):
        self.nsurfaces = comma(db.hmsurfaces_invs.count())
        #No level information yet

    @property
    def short_summary(self):
        hmsurface_knowl = display_knowl("hmsurface", title="Hilbert modular surfaces")
        return (
            fr'The database currently contains {self.nsurfaces} {hmsurface_knowl}. You can <a>href="{url_for(".statistics")}">browse further statistics</a>.<br><br>'
        )

    @property
    def summary(self):
        hmsurface_knowl = display_knowl("hmsurface", title="modular surfaces")
        return (
            fr'The database currently contains {self.nsurfaces} {hmsurface_knowl}.'
        )
    
    table = db.hmsurfaces_invs
    baseurl_func = ".index"
    #No buckets
    #No knowls
    #No stat_list

@hmsurface_page.route("/Q/stats")
def statistics():
    title = 'Hilbert modular surfaces: Statistics'
    return render_template("display_stats.html", info=HMSurface_stats(), title=title, bread=get_bread('Statistics'), learnmore=learnmore_list())

@hmsurface_page.route("/Source")
def how_computed_page():
    t = r'Source and acknowledgments for Hilbert modular surface data'
    bread = get_bread('Source')
    return render_template("multi.html",
                           kids=['rcs.source.hmsurface',
                           'rcs.ack.hmsurface',
                           'rcs.cite.hmsurface'],
                           title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@hmsurface_page.route("/Completeness")
def completeness_page():
    t = r'Completeness of Hilbert modular surfaces data'
    bread = get_bread('Completeness')
    return render_template("single.html", kid='rcs.cande.hmsurface',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@hmsurface_page.route("/Reliability")
def reliability_page():
    t = r'Reliability of Hilbert modular surface data'
    bread = get_bread('Reliability')
    return render_template("single.html", kid='rcs.rigor.hmsurface',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@hmsurface_page.route("/Labels")
def labels_page():
    t = r'Labels for Hilbert modular surfaces'
    bread = get_bread('Labels')
    return render_template("single.html", kid='hmsurface.label',
                           title=t, bread=bread, learnmore=learnmore_list_remove('labels'))

@hmsurface_page.route("/data/<label>")
def hmsurface_data(label):
    bread = get_bread([(label, url_for_hmsurface_label(label)), ("Data", " ")])
    if LABEL_RE.fullmatch(label):
        return datapage([label], ["hmsurfaces_invs"], title=f"Modular surface data - {label}", bread=bread)
    else:
        return abort(404)

class HMSurface_download(Downloader):
    table = db.hmsurfaces_invs
    title = "Hilbert modular surfaces"
    
    def download_hmsurface_magma_str(self, label):
        #No download yet
        pass

    def download_hmsurface_magma(self, label):
        s = self.download_hmsurface_magma_str(label)
        return self._wrap(s, label, lang="magma")

    def download_hmsurface_sage(self, label):
        s = self.download_hmsurface_magma_str(label)
        s = s.replace(":=", "=")
        s = s.replace(";", "")
        s = s.replace("//", "#")
        return self._wrap(s, label, lang="sage")

    def download_hmsurface(self, label, lang):
        if lang == "magma":
            return self.download_hmsurface_magma(label)
        elif lang == "sage":
            return self.download_hmsurface_sage(label)
        elif lang == "text":
            data = db.hmsurfaces_invs.lookup(label)
            if data is None:
                return abort(404, "Label not found: %s" % label)
            return self._wrap(Json.dumps(data),
                              label,
                              title='Data for modular surface with label %s,'%label)

@hmsurface_page.route("/download_to_magma/<label>")
def hmsurface_magma_download(label):
    return HMSurface_download().download_hmsurface(label, lang="magma")

@hmsurface_page.route("/download_to_sage/<label>")
def hmsurface_sage_download(label):
    return HMSurface_download().download_hmsurface(label, lang="sage")

@hmsurface_page.route("/download_to_text/<label>")
def hmsurface_text_download(label):
    return HMSurface_download().download_hmsurface(label, lang="text")

