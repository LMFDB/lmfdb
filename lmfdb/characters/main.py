from lmfdb.app import app
import re
from flask import render_template, url_for, request, redirect, abort
from sage.all import euler_phi, PolynomialRing, QQ, gcd, ZZ
from sage.databases.cremona import class_to_int
from lmfdb.utils import (
    to_dict, flash_error, SearchArray, YesNoBox, display_knowl, ParityBox,
    TextBox, CountBox, parse_bool, parse_ints, search_wrap, raw_typeset_poly,
    StatsDisplay, totaler, proportioners, comma, flash_warning, Downloader)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_parsing import parse_range3
from lmfdb.utils.search_columns import SearchColumns, MathCol, LinkCol, CheckCol, ProcessedCol, MultiProcessedCol
from lmfdb.characters.utils import url_character
from lmfdb.characters.TinyConrey import ConreyCharacter
from lmfdb.api import datapage
from lmfdb.number_fields.web_number_field import formatfield
from lmfdb.characters.web_character import (
    valuefield_from_order,
    WebSmallDirichletCharacter,
    WebDBDirichletCharacter,
    WebDBDirichletGroup,
    WebSmallDirichletGroup,
    WebDBDirichletOrbit
)
from lmfdb.characters.ListCharacters import get_character_modulus
from lmfdb.characters import characters_page
from lmfdb import db

ORBIT_MAX_MOD = 1000000

# make url_character available from templates


@app.context_processor
def ctx_characters():
    chardata = {}
    chardata['url_character'] = url_character
    return chardata


def bread(tail=[]):
    base = [('Characters', url_for(".render_characterNavigation")),
            ('Dirichlet', url_for(".render_DirichletNavigation"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail


def learn(current=None):
    r = []
    if current != 'source':
        r.append(('Source and acknowledgments', url_for(".how_computed_page")))
    if current != 'extent':
        r.append(('Completeness of the data', url_for(".extent_page")))
    if current != 'reliability':
        r.append(('Reliability of the data', url_for(".reliability")))
    if current != 'labels':
        r.append(('Dirichlet character labels', url_for(".labels_page")))
    if current != 'orbit_labels':
        r.append(('Dirichlet character orbit labels', url_for(".orbit_labels_page")))
    return r

###############################################################################
#   Route functions
#   Do not use url_for on these, use url_character defined in lmfdb.utils
###############################################################################


@characters_page.route("/")
def render_characterNavigation():
    """
    FIXME: replace query by ?browse=<key>&start=<int>&end=<int>
    """
    return redirect(url_for(".render_DirichletNavigation"), 301)


class DirichSearchArray(SearchArray):
    noun = "character"
    sorts = [("", "modulus", ["modulus", "orbit"]),
             ("conductor", "conductor", ["conductor", "modulus", "orbit"]),
             ("order", "order", ["order", "modulus", "orbit"])]
    jump_example = "13.2"
    jump_egspan = r"e.g. 13.2 for the Dirichlet character \(\displaystyle\chi_{13}(2,·)\),or 13.f for its Galois orbit."
    jump_knowl = "character.dirichlet.search_input"
    jump_prompt = "Label"

    def __init__(self):
        modulus = TextBox(
            "modulus",
            knowl="character.dirichlet.modulus",
            label="Modulus",
            example="13",
            example_span="13",
        )
        conductor = TextBox(
            "conductor",
            knowl="character.dirichlet.conductor",
            label="Conductor",
            example="5",
            example_span="5 or 10,20",
        )
        order = TextBox(
            "order",
            label="Order",
            knowl="character.dirichlet.order",
            example="2",
            example_span="2 or 3-5"
        )
        inducing = TextBox(
            "inducing",
            label="Induced by",
            knowl="character.dirichlet.primitive",
            example="3.b"
        )
        parity = ParityBox(
            "parity",
            knowl="character.dirichlet.parity",
            label="Parity",
            example="odd"
        )
        is_primitive = YesNoBox(
            "is_primitive",
            label="Primitive",
            knowl="character.dirichlet.primitive",
            example="yes"
        )
        is_real = YesNoBox(
            "is_real",
            label="Real",
            knowl="character.dirichlet.real",
            example="yes"
        )
        is_minimal = YesNoBox(
            "is_minimal",
            label="Minimal",
            knowl="character.dirichlet.minimal",
            example="yes"
        )
        count = CountBox()

        self.refine_array = [
            [modulus, conductor, order, inducing], [parity, is_primitive, is_minimal, is_real], [count],
        ]
        self.browse_array = [
            [modulus],
            [conductor],
            [order],
            [inducing],
            [parity],
            [is_primitive],
            [is_real],
            [is_minimal],
            [count],
        ]

    def search_types(self, info):
        return self._search_again(info, [
            ('', 'List of characters'),
            ('Random', 'Random character')])


def common_parse(info, query):
    parse_ints(info, query, "modulus", name="modulus")
    parse_ints(info, query, "conductor", name="conductor")
    parse_ints(info, query, "order", name="order")
    if 'inducing' in info:
        try:
            validate_label(info['inducing'])
            parts_of_label = info['inducing'].split(".")
            if len(parts_of_label) != 2:
                raise ValueError("Invalid character orbit label format, expected N.a")
            if not str.isalpha(parts_of_label[1]):
                chi = ConreyCharacter(int(parts_of_label[0]), int(parts_of_label[1]))
                label = db.char_dirichlet.lucky({'modulus': chi.modulus, 'first': chi.min_conrey_conj}, projection='label')
                parts_of_label = label.split(".")
            primitive_modulus = int(parts_of_label[0])
            primitive_orbit = class_to_int(parts_of_label[1])+1
            if db.char_dirichlet.count({'modulus':primitive_modulus,'is_primitive':True,'orbit':primitive_orbit}) == 0:
                raise ValueError("Primitive character orbit not found")

            def incompatible(query):
                cond = query.get('conductor')
                if cond is None:
                    return False
                if isinstance(cond, int):
                    return cond != primitive_modulus
                opts = parse_range3(info['conductor'], lower_bound=1, upper_bound=ORBIT_MAX_MOD)
                for opt in opts:
                    if (isinstance(opt, int) and opt == primitive_modulus
                        or not isinstance(opt, int) and opt[0] <= primitive_modulus <= opt[1]):
                        return False
                return True
            if incompatible(query):
                query["primitive_orbit"] = 0
            else:
                query["conductor"] = primitive_modulus
                query["primitive_orbit"] = primitive_orbit
        except ValueError:
            flash_error("%s is not the label of a primitive character in the database", info['inducing'])
            raise ValueError
    if 'parity' in info:
        parity = info['parity']
        if parity == 'even':
            query['is_even'] = True
        elif parity == 'odd':
            query['is_even'] = False
    parse_bool(info, query, "is_primitive", name="is_primitive")
    parse_bool(info, query, "is_real", name="is_real")
    parse_bool(info, query, "is_minimal", name="is_minimal")


def validate_label(label):

    if re.match(r'^\d+\.[a-z]+$', label):  # label is an orbit
        return True
    elif re.match(r'^\d+\.\d+$', label):  # label is a character
        return True
    elif re.match(r'^\d+\.[a-z]+\.\d+$', label):  # label has both orbit and number
        return True
    else:
        raise ValueError("It must be of the form modulus.number, or "
                          "modulus.letter, or modulus.letter.number, "
                          "with modulus and number positive natural numbers "
                          " and letter an alphabetic letter."
                          )

def jump(info):
    jump_box = info["jump"].strip()  # only called when this present
    try:
        validate_label(jump_box)
    except ValueError as err:
        flash_error("%s is not a valid label: %s.", jump_box, str(err))
        return redirect(url_for(".render_DirichletNavigation"))
    return redirect(url_for_label(jump_box))


def url_for_label(label):
    label = label.replace(" ", "")
    try:
        validate_label(label)
    except ValueError as err:
        flash_error("%s is not a valid label: %s.", label, str(err))
        return redirect(url_for(".render_DirichletNavigation"))

    parts_of_label = label.split(".")

    if len(parts_of_label) == 2:
        modulus = int(parts_of_label[0])
        if str.isalpha(parts_of_label[1]):
            orbit_label = parts_of_label[1]
            return url_for(".render_Dirichletwebpage", modulus=modulus, orbit_label=orbit_label)
        else:
            number = int(parts_of_label[1])
            return url_for(".render_Dirichletwebpage", modulus=modulus, number=number)
    else: ## i.e. there are three parts
        modulus = int(parts_of_label[0])
        orbit_label = parts_of_label[1]
        number = int(parts_of_label[2])
        return url_for(".render_Dirichletwebpage", modulus=modulus, orbit_label=orbit_label, number=number)

def display_galois_orbit(modulus, first, last, degree):
    if degree == 1:
        disp = r'<a href="{0}/{1}">\(\chi_{{{0}}}({1}, \cdot)\)</a>'.format(modulus, first)
        return f'<p style="margin-top: 0px;margin-bottom:0px;">\n{disp}\n</p>'
    else:
        orbit = [first, last]
        disp = [r'<a href="{0}/{1}">\(\chi_{{{0}}}({1}, \cdot)\)</a>'.format(modulus, o) for o in orbit]
        if degree == 2:
            disp = "$,$&nbsp".join(disp)
            return f'<p style="margin-top: 0px;margin-bottom:0px;">\n{disp}\n</p>'
        else:
            disp = r"$, \cdots ,$".join(disp)
            return f'<p style="margin-top: 0px;margin-bottom:0px;">\n{disp}\n</p>'

def display_kernel_field(modulus, first, order):
    if order > 12:
        return "not computed"
    else:
        coeffs = ConreyCharacter(modulus,first).kernel_field_poly()
        return formatfield([ZZ(x) for x in coeffs])

character_columns = SearchColumns([
    LinkCol("label", "character.dirichlet.galois_orbit_label", "Orbit label", lambda label: label.replace(".", "/"), align="center"),
    MultiProcessedCol("conrey", "character.dirichlet.conrey", "Conrey labels", ["modulus", "first", "last", "degree"],
                      display_galois_orbit, align="center", short_title="Conrey labels", apply_download=False),
    MathCol("modulus", "character.dirichlet.modulus", "Modulus"),
    MathCol("conductor", "character.dirichlet.conductor", "Conductor"),
    MathCol("order", "character.dirichlet.order", "Order"),
    MultiProcessedCol("first", "character.dirichlet.field_cut_out", "Kernel field", ["modulus", "first", "order"], display_kernel_field, align="center", default=False, apply_download=False),
    ProcessedCol("order", "character.dirichlet.value_field", "Value field", valuefield_from_order, align="center", apply_download=False),
    ProcessedCol("is_even", "character.dirichlet.parity", "Parity", lambda is_even: "even" if is_even else "odd"),
    CheckCol("is_real", "character.dirichlet.real", "Real"),
    CheckCol("is_primitive", "character.dirichlet.primitive", "Primitive"),
    CheckCol("is_minimal", "character.dirichlet.minimal", "Minimal"),
    ])

@search_wrap(
    table=db.char_dirichlet,
    title="Dirichlet character search results",
    err_title="Dirichlet character search input error",
    columns=character_columns,
    shortcuts={"jump": jump, "download": Downloader(db.char_dirichlet)},
    url_for_label=url_for_label,
    learnmore=learn,
    random_projection="label",
    bread=lambda: bread("Search results"),
)
def dirichlet_character_search(info, query):
    common_parse(info, query)


@characters_page.route("/Dirichlet")
@characters_page.route("/Dirichlet/")
def render_DirichletNavigation():
    try:
        if 'modbrowse' in request.args:
            arg = request.args['modbrowse']
            arg = arg.split('-')
            modulus_start = int(arg[0])
            modulus_end = int(arg[1])
            info = {'args': request.args}
            info['title'] = 'Dirichlet characters of modulus ' + str(modulus_start) + '-' + str(modulus_end)
            info['bread'] = bread('Modulus')
            info['learnmore'] = learn()
            headers, entries, rows, cols = get_character_modulus(modulus_start, modulus_end, limit=8)
            info['entries'] = entries
            info['rows'] = list(range(modulus_start, modulus_end + 1))
            info['cols'] = sorted({r[1] for r in entries})
            return render_template("ModulusList.html", **info)
    except ValueError as err:
        flash_error("Error raised in parsing: %s", err)

    if request.args:
        # hidden_search_type for prev/next buttons
        info = to_dict(request.args, search_array=DirichSearchArray())
        info["search_type"] = search_type = info.get("search_type", info.get("hst", ""))
        if search_type in ['List', '', 'Random']:
            return dirichlet_character_search(info)
        assert False

    info = to_dict(request.args, search_array=DirichSearchArray(), stats=DirichStats())
    info['bread'] = bread()
    info['learnmore'] = learn()
    info['title'] = 'Dirichlet characters'
    info['modulus_list'] = ['1-20', '21-40', '41-60']
    info['conductor_list'] = ['1-9', '10-99', '100-999', '1000-9999']
    info['order_list'] = list(range(1, 13))
    return render_template('CharacterNavigate.html', info=info, **info)


@characters_page.route("/Dirichlet/Labels")
def labels_page():
    info = {}
    info['title'] = 'Dirichlet character labels'
    info['bread'] = bread('Labels')
    info['learnmore'] = learn('labels')
    return render_template("single.html", kid='character.dirichlet.conrey',
                           **info)


@characters_page.route("/Dirichlet/OrbitLabels")
def orbit_labels_page():
    info = {}
    info['title'] = 'Dirichlet character orbit labels'
    info['bread'] = bread('Orbit Labels')
    info['learnmore'] = learn('orbit_labels')
    return render_template("single.html",
                           kid='character.dirichlet.conrey.orbit_label',
                           **info)


@characters_page.route("/Dirichlet/Source")
def how_computed_page():
    info = {}
    info['title'] = 'Source and acknowledgments for Dirichlet character data'
    info['bread'] = bread('Source')
    info['learnmore'] = learn('source')
    return render_template("multi.html", kids=['rcs.source.character.dirichlet',
                            'rcs.ack.character.dirichlet',
                            'rcs.cite.character.dirichlet'],
                           **info)


@characters_page.route("/Dirichlet/Reliability")
def reliability():
    info = {}
    info['title'] = 'Reliability of Dirichlet character data'
    info['bread'] = bread('Reliability')
    info['learnmore'] = learn('reliability')
    return render_template("single.html", kid='rcs.rigor.character.dirichlet', **info)


@characters_page.route("/Dirichlet/Completeness")
def extent_page():
    info = {}
    info['title'] = 'Completeness of Dirichlet character data'
    info['bread'] = bread('Extent')
    info['learnmore'] = learn('extent')
    return render_template("single.html", kid='rcs.cande.character.dirichlet',
                           **info)


def make_webchar(args, get_bread=False):
    modulus = int(args['modulus'])
    number = int(args['number']) if 'number' in args else None
    orbit_label = args.get('orbit_label', None)
    if modulus <= ORBIT_MAX_MOD:
        if number is None:
            if get_bread:
                bread_crumbs = bread(
                    [('%s' % modulus, url_for(".render_Dirichletwebpage", modulus=modulus)),
                     ('%s' % orbit_label, url_for(".render_Dirichletwebpage", modulus=modulus, orbit_label=orbit_label))])
                return WebDBDirichletOrbit(**args), bread_crumbs
            return WebDBDirichletOrbit(**args)
        if args.get('orbit_label') is None:
            chi = ConreyCharacter(modulus, number)
            db_orbit_label = db.char_dirichlet.lucky(
            {'modulus': modulus, 'first': chi.min_conrey_conj},
            projection='label'
            )
            args['orbit_label'] = db_orbit_label.split('.')[-1]
        if get_bread:
            bread_crumbs = bread(
                [('%s' % modulus, url_for(".render_Dirichletwebpage", modulus=modulus)),
                 ('%s' % orbit_label, url_for(".render_Dirichletwebpage", modulus=modulus, orbit_label=orbit_label)),
                 ('%s' % number, url_for(".render_Dirichletwebpage", modulus=modulus, orbit_label=orbit_label, number=number))])
            return WebDBDirichletCharacter(**args), bread_crumbs
        return WebDBDirichletCharacter(**args)
    else:
        if get_bread:
            bread_crumbs = bread(
                [('%s' % modulus, url_for(".render_Dirichletwebpage", modulus=modulus)),
                 ('%s' % number, url_for(".render_Dirichletwebpage", modulus=modulus, number=number))])
            return WebSmallDirichletCharacter(**args), bread_crumbs
        return WebSmallDirichletCharacter(**args)


@characters_page.route("/Dirichlet/<modulus>")
@characters_page.route("/Dirichlet/<modulus>/")
@characters_page.route("/Dirichlet/<int:modulus>/<int:number>")
@characters_page.route("/Dirichlet/<int:modulus>/<orbit_label>")  # orbit_label is a Cremona_letter_code identifying the orbit
@characters_page.route("/Dirichlet/<int:modulus>/<orbit_label>/<int:number>")
def render_Dirichletwebpage(modulus=None, orbit_label=None, number=None):

    if number is None and orbit_label is None and re.match(r'^[1-9][0-9]*\.[1-9][0-9]*$', modulus):
        modulus, number = modulus.split('.')
        return redirect(url_for(".render_Dirichletwebpage", modulus=modulus, number=number), 301)
    if number is not None and number > modulus:
        return redirect(url_for(".render_Dirichletwebpage", modulus=modulus, number=number % modulus), 301)
    if modulus == 1 and number == 0:
        return redirect(url_for(".render_Dirichletwebpage", modulus=1, number=1), 301)

    args = {}
    args['type'] = 'Dirichlet'
    args['modulus'] = modulus
    args['orbit_label'] = orbit_label
    args['number'] = number
    try:
        modulus = int(modulus)
    except ValueError:
        modulus = 0
    if modulus <= 0:
        flash_error("%s is not a valid modulus for a Dirichlet character. It should be a positive integer.", args['modulus'])
        return redirect(url_for(".render_DirichletNavigation"))
    if modulus > 10**20:
        flash_error("specified modulus %s is too large, it should be less than $10^{20}$.", modulus)
        return redirect(url_for(".render_DirichletNavigation"))
    if modulus == 1:
        number = 1
    if number is None:
        if orbit_label is None:

            if modulus <= ORBIT_MAX_MOD:
                info = WebDBDirichletGroup(**args).to_dict()
                info['show_orbit_label'] = True
            else:
                info = WebSmallDirichletGroup(**args).to_dict()

            info['title'] = 'Group of Dirichlet characters of modulus ' + str(modulus)
            info['bread'] = bread([('%s' % modulus, url_for(".render_Dirichletwebpage", modulus=modulus))])
            info['learnmore'] = learn()
            info['code'] = {k[4:]: info[k] for k in info if k[0:4] == "code"}
            info['code']['show'] = {lang: '' for lang in info['codelangs']}  # use default show names
            if 'gens' in info:
                info['generators'] = ', '.join(r'<a href="%s">$\chi_{%s}(%s,\cdot)$' % (url_for(".render_Dirichletwebpage", modulus=modulus, number=g), modulus, g) for g in info['gens'])
            return render_template('CharGroup.html', **info)
        else:
            if modulus <= ORBIT_MAX_MOD:
                try:
                    info = WebDBDirichletOrbit(**args).to_dict()
                except ValueError:
                    flash_error(
                        "No Galois orbit of Dirichlet characters with label %s.%s was found in the database.", modulus, orbit_label
                    )
                    return redirect(url_for(".render_DirichletNavigation"))

                info['show_orbit_label'] = True
                info['downloads'] = [('Underlying data', url_for('.dirchar_data', label=f"{modulus}.{orbit_label}"))]
                info['learnmore'] = learn()
                info['code'] = {k[4:]: info[k] for k in info if k[0:4] == "code"}
                info['code']['show'] = {lang: '' for lang in info['codelangs']}  # use default show names
                info['bread'] = bread(
                    [('%s' % modulus, url_for(".render_Dirichletwebpage", modulus=modulus)),
                     ('%s' % orbit_label, url_for(".render_Dirichletwebpage", modulus=modulus, orbit_label=orbit_label))])
                return render_template('CharacterGaloisOrbit.html', **info)
            else:
                flash_error(
                    "Galois orbits have only been computed for modulus up to 100,000, but you entered %s", modulus)
            return redirect(url_for(".render_DirichletNavigation"))
    else:
        if gcd(modulus,number) != 1:
            flash_error("%s is not a valid Conrey label (number must be coprime to modulus).", "%s.%s" % (args['modulus'],args['number']))
            return redirect(url_for(".render_DirichletNavigation"))

    try:
        number = int(number)
    except ValueError:
        flash_error(
            "the value %s is invalid. It should either be a positive integer "
            "coprime to and no greater than the modulus %s, or a letter that "
            "corresponds to a valid orbit index.", args['number'], args['modulus']
        )
        return redirect(url_for(".render_DirichletNavigation"))

    if modulus <= ORBIT_MAX_MOD:
        chi = ConreyCharacter(modulus, number)
        db_orbit_label = db.char_dirichlet.lucky(
        {'modulus': modulus, 'first': chi.min_conrey_conj},
        projection='label'
        )
        real_orbit_label = db_orbit_label.split('.')[-1]

        if orbit_label is not None:
            if orbit_label != real_orbit_label:
                flash_warning(
                    "The supplied character orbit label %s.%s was wrong. "
                    "The correct orbit label is %s.%s. The URL has been duly corrected.",
                    modulus, orbit_label, modulus, real_orbit_label)
                return redirect(url_for("characters.render_Dirichletwebpage",
                                        modulus=modulus,
                                        orbit_label=real_orbit_label,
                                        number=number))
        args['orbit_label'] = real_orbit_label
        downloads = [('Underlying data', url_for(".dirchar_data", label=f"{modulus}.{real_orbit_label}.{number}"))]
    else:
        if orbit_label is not None:
            flash_warning(
                "You entered the character orbit label %s.%s. However, such labels "
                "have not been computed for this modulus. The supplied orbit "
                "label has therefore been ignored and expunged from the URL.",
                modulus, orbit_label)
            return redirect(url_for("characters.render_Dirichletwebpage",
                                    modulus=modulus,
                                    number=number))
        downloads = []

    args['number'] = number
    webchar, bread_crumbs = make_webchar(args, get_bread=True)
    info = webchar.to_dict()
    info['bread'] = bread_crumbs
    info['learnmore'] = learn()
    info['downloads'] = downloads
    info['code'] = {k[4:]: info[k] for k in info if k[0:4] == "code"}
    info['code']['show'] = {lang: '' for lang in info['codelangs']}  # use default show names
    info['KNOWL_ID'] = 'character.dirichlet.%s.%s' % (modulus, number)
    return render_template('Character.html', **info)

@characters_page.route("/Dirichlet/data/<label>")
def dirchar_data(label):
    if label.count(".") == 1:
        modulus, orbit_label = label.split(".")
        title = f"Dirichlet character data - {modulus}.{orbit_label}"
        tail = [(label, url_for(".render_Dirichletwebpage", modulus=modulus, orbit_label=orbit_label)),
                ("Data", " ")]
        return datapage(label, "char_dirichlet", title=title, bread=bread(tail))
    elif label.count(".") == 2:
        modulus, orbit_label, number = label.split(".")
        title = f"Dirichlet character data - {modulus}.{orbit_label}.{number}"
        tail = [(label, url_for(".render_Dirichletwebpage", modulus=modulus, number=number)),
                ("Data", " ")]
        return datapage(f"{modulus}.{orbit_label}", "char_dirichlet", title=title, bread=bread(tail))
    else:
        return abort(404, f"Invalid label {label}")

def _dir_knowl_data(label, orbit=False):
    try:
        parts = label.split('.')
        modulus = int(parts[0])
        if orbit:
            assert (modulus <= ORBIT_MAX_MOD)
            args = {'type': 'Dirichlet', 'modulus': modulus, 'orbit_label': parts[1]}
        else:
            number = int(parts[1])
            args = {'type': 'Dirichlet', 'modulus': modulus, 'number': number}
        webchar = make_webchar(args)

        if orbit:
            inf = "Dirichlet character orbit %s.%s\n" % (modulus, webchar.orbit_label)
        else:
            inf = r"Dirichlet character \(\chi_{%s}(%s, \cdot)\)" % (modulus, parts[1]) + "\n"
        inf += "<div><table class='chardata'>\n"

        def row_wrap(header, val):
            return "<tr><td>%s: </td><td>%s</td></tr>\n" % (header, val)
        inf += row_wrap('Conductor', webchar.conductor)
        inf += row_wrap('Order', webchar.order)
        inf += row_wrap('Degree', euler_phi(webchar.order))
        inf += row_wrap('Minimal', webchar.isminimal)
        inf += row_wrap('Parity', webchar.parity)
        if modulus <= ORBIT_MAX_MOD:
            if not orbit:
                inf += row_wrap('Orbit label', '%s.%s' % (modulus, webchar.orbit_label))
            inf += row_wrap('Orbit Index', webchar.orbit_index)
        inf += '</table></div>\n'
        if orbit:
            inf += '<div align="right">\n'
            inf += '<a href="%s">%s.%s home page</a>\n' % (str(url_for("characters.render_Dirichletwebpage", modulus=modulus, orbit_label=webchar.orbit_label)), modulus, webchar.orbit_label)
            inf += '</div>\n'
        else:
            inf += '<div align="right">\n'
            inf += '<a href="%s">%s home page</a>\n' % (str(url_for("characters.render_Dirichletwebpage", modulus=modulus, number=number)), label)
            inf += '</div>\n'
    except Exception:  # yes we really want to catch everything here
        return "Unable to construct knowl for Dirichlet character label %s, please report this as a bug (include the URL of this page)." % label
    return inf


def dirichlet_character_data(label):
    return _dir_knowl_data(label, orbit=False)


def dirichlet_orbit_data(label):
    return _dir_knowl_data(label, orbit=True)


@app.context_processor
def ctx_dirchar():
    return {'dirichlet_character_data': dirichlet_character_data,
            'dirichlet_orbit_data': dirichlet_orbit_data}


@characters_page.route('/Dirichlet/random')
def random_Dirichletwebpage():
    return redirect(url_for('.render_DirichletNavigation', search_type="Random"))


@characters_page.route('/Dirichlet/interesting')
def interesting():
    return interesting_knowls(
        "character.dirichlet",
        db.char_dirichlet,
        url_for_label=url_for_label,
        title="Some interesting Dirichlet characters",
        bread=bread("Interesting"),
        learnmore=learn())


@characters_page.route('/Dirichlet/stats')
def statistics():
    title = "Dirichlet characters: statistics"
    return render_template("display_stats.html", info=DirichStats(), title=title, bread=bread("Statistics"), learnmore=learn())


@characters_page.route("/calc-<calc>/Dirichlet/<int:modulus>/<int:number>")
def dc_calc(calc, modulus, number):
    val = request.args.get("val", [])
    args = {'type': 'Dirichlet', 'modulus': modulus, 'number': number}
    if not val:
        return abort(404)
    try:
        if calc == 'value':
            return WebSmallDirichletCharacter(**args).value(val)
        if calc == 'gauss':
            return WebSmallDirichletCharacter(**args).gauss_sum(val)
        elif calc == 'jacobi':
            return WebSmallDirichletCharacter(**args).jacobi_sum(val)
        elif calc == 'kloosterman':
            return WebSmallDirichletCharacter(**args).kloosterman_sum(val)
        else:
            return abort(404)
    except Warning as e:
        return "<span style='color:gray;'>%s</span>" % e
    except Exception:
        return "<span style='color:red;'>Error: bad input</span>"

###############################################################################
# TODO: refactor the following
###############################################################################


@characters_page.route("/Dirichlet/table")
def dirichlet_table():
    args = to_dict(request.args)
    mod = args.get('modulus', 1)
    return redirect(url_for('characters.render_Dirichletwebpage', modulus=mod))

# FIXME: these group table pages are used by number fields pages.
# should refactor this into WebDirichlet.py


@characters_page.route("/Dirichlet/grouptable")
def dirichlet_group_table(**args):
    modulus = request.args.get("modulus", 1, type=int)
    info = to_dict(args)
    if "modulus" not in info:
        info["modulus"] = modulus
    info['bread'] = bread('Group')
    char_number_list = request.args.get("char_number_list", None)
    if char_number_list is not None:
        try:
            info['char_number_list'] = char_number_list
            char_number_list = [int(a) for a in char_number_list.split(',')]
            info['poly'] = request.args.get("poly", '???')
        except (ValueError, AttributeError, TypeError) as err:
            flash_error("<span style='color:black'>%s</span> is not a valid input for <span style='color:black'>%s</span>. %s", char_number_list, 'char_number_list', str(err))
            return abort(404, 'grouptable needs a valid char_number_list argument')
    else:
        return abort(404, 'grouptable needs char_number_list argument')
    h, c = get_group_table(modulus, char_number_list)
    info['headers'] = h
    info['contents'] = c
    info['title'] = 'Group of Dirichlet characters'
    if info['poly'] != '???':
        try:
            info['poly'] = PolynomialRing(QQ, 'x')(info['poly'])
            info['poly'] = raw_typeset_poly(info['poly'])
        except Exception:
            pass
    return render_template("CharacterGroupTable.html", **info)


def get_group_table(modulus, char_list):
    # Move 1 to the front of the list
    char_list.insert(0, char_list.pop(next(j for j in range(len(char_list)) if char_list[j] == 1)))
    headers = list(char_list)  # Just a copy
    if modulus == 1:
        rows = [[1]]
    else:
        rows = [[(j * k) % modulus for k in char_list] for j in char_list]
    return headers, rows


def yesno(x):
    return "yes" if x in ["yes", True] else "no"


class DirichStats(StatsDisplay):
    table = db.char_dirichlet
    baseurl_func = ".render_DirichletNavigation"
    stat_list = [
        {"cols": ["conductor"]},
        {"cols": ["order", "modulus"],
         "title_joiner": " by ",
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["is_primitive", "modulus"],
         "title_joiner": " by ",
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["is_real", "modulus"],
         "title_joiner": " by ",
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["is_minimal", "modulus"],
         "title_joiner": " by ",
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
    ]
    buckets = {"conductor": ["1-10", "11-100", "101-1000", "1001-10000", "10001-100000", "100001-1000000"],
               "modulus": ["1-10", "11-100", "101-1000", "1001-10000", "10001-100000", "100001-1000000"],
               "order": ["1-10", "11-100", "101-1000", "1001-10000", "10001-100000", "100001-1000000"]}
    knowls = {"conductor": "character.dirichlet.conductor",
              "modulus": "character.dirichlet.modulus",
              "order": "character.dirichlet.order",
              "is_minimal": "character.dirichlet.minimal",
              "is_primitive": "character.dirichlet.primitive",
              "is_real": "character.dirichlet.real"}
    short_display = {"is_minimal": "minimal",
                     "is_primitive": "primitive",
                     "is_real": "real"}
    top_titles = {"order": "order",
                  "is_minimal": "minimality",
                  "is_primitive": "primitivity",
                  "is_real": "real characters"}
    formatters = {"is_minimal": yesno,
                  "is_primitive": yesno,
                  "is_real": yesno}

    def __init__(self):
        self.nchars = db.char_dirichlet.sum('degree')
        self.norbits = db.char_dirichlet.count()
        self.maxmod = db.char_dirichlet.max("modulus")

    @property
    def short_summary(self):
        return 'The database currently contains %s %s of %s %s of %s up to %s.  L-functions are available for characters of modulus up to 2,800 (and some of higher modulus).  Here are some <a href="%s">further statistics</a>.' % (
            comma(self.norbits),
            display_knowl("character.dirichlet.galois_orbit", "Galois orbits"),
            comma(self.nchars),
            display_knowl("character.dirichlet", "Dirichlet characters"),
            display_knowl("character.dirichlet.modulus", "modulus"),
            comma(self.maxmod),
            url_for(".statistics"))

    @property
    def summary(self):
        return "The database currently contains %s %s of %s %s of %s up to %s. The tables below count Galois orbits." % (
            comma(self.norbits),
            display_knowl("character.dirichlet.galois_orbit", "Galois orbits"),
            comma(self.nchars),
            display_knowl("character.dirichlet", "Dirichlet characters"),
            display_knowl("character.dirichlet.modulus", "modulus"),
            comma(self.maxmod))
