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
            ('Modular curve labels', url_for(".labels_page"))]

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
    #info["level_list"] = ["1-4", "5-8", "9-12", "13-16", "17-23", "24-"]
    #info["genus_list"] = ["0", "1", "2", "3", "4-6", "7-20", "21-100", "101-"]
    #info["rank_list"] = ["0", "1", "2", "3", "4-6", "7-20", "21-100", "101-"]
    #info["stats"] = HMSurface_stats()
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

def hmsurface_lmfdb_label(label):
    #Recognize other labels/names as in modular curves?
    label_type = "label"
    lmfdb_label = label
    return lmfdb_label, label_type
    
def hmsurface_jump(info):
    #No direct products here
    label = info["jump"]
    return redirect(url_for_hmsurface_label(label))

#Add more search boxes later
hmsurface_columns = SearchColumns([
    LinkCol("label", "hmsurface.label", "Label", url_for_hmsurface_label, default=True),
    MathCol("chi", "hmsurface.chi", "Arithmetic genus", default=True),
])

#No family parsing

@search_wrap(
    table=db.hmsurfaces_invs,
    title="Modular surface search results",
    err_title="Modular surfaces search input error",
    shortcuts={"jump": hmsurface_jump},
    columns=hmsurface_columns,
    bread=lambda: get_bread("Search results"),
    url_for_label=url_for_hmsurface_label,
)
def hmsurface_search(info, query):
    parse_ints(info, query, "chi")

class HMSurfaceSearchArray(SearchArray):
    noun = "surface"
    jump_example = "2.2.5.1-1.1-1.1-gl-0"
    jump_egspan = "e.g. 2.2.5.1-1.1-1.1-gl-0"
    jump_prompt = "Label"
    jump_knowl = "hmsurface.search_input"

    #See main.py in modular_curves for select boxes, etc.
    def __init__(self):
        chi = TextBox(
            name="chi",
            knowl="hmsurface.chi",
            label="Arithmetic genus",
            example="1",
            example_span="1, 3-4",
        )
        count = CountBox()

        self.browse_array = [
            [chi],
        ]

        self.refine_array = [
            [chi],
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
            fr'The database currently contains {self.nsurfaces} {hmsurface_knowl}. You can <a>href="{url_for(".statistics")}">browse further statistics</a>.'
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

