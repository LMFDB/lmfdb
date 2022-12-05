# -*- coding: utf-8 -*-


from lmfdb.app import app
import re
from flask import render_template, url_for, request, redirect, abort
from sage.all import gcd, euler_phi, PolynomialRing, QQ
from lmfdb.utils import (
    to_dict, flash_error, SearchArray, YesNoBox, display_knowl, ParityBox,
    TextBox, CountBox, parse_bool, parse_ints, search_wrap, raw_typeset_poly,
    StatsDisplay, totaler, proportioners, comma, flash_warning)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, MathCol, LinkCol, CheckCol, ProcessedCol, MultiProcessedCol
from lmfdb.characters.utils import url_character
from lmfdb.api import datapage
from lmfdb.characters.web_character import (
    WebSmallDirichletCharacter,
    WebDBDirichletCharacter,
    WebDBDirichletGroup,
    WebSmallDirichletGroup,
    WebDBDirichletOrbit
)
from lmfdb.characters.ListCharacters import get_character_modulus
from lmfdb.characters import characters_page
from sage.databases.cremona import class_to_int, cremona_letter_code
from lmfdb import db

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
    plural_noun = "characters"
    sorts = [("", "modulus", ["modulus", "orbit_index"]),
             ("conductor", "conductor", ["conductor", "prim_orbit_index", "modulus", "orbit_index"]),
             ("order", "order", ["order", "modulus", "orbit_index"])]
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
            [modulus, conductor, order, is_real], [parity, is_primitive, is_minimal, count],
        ]
        self.browse_array = [
            [modulus],
            [conductor],
            [order],
            [parity],
            [is_primitive],
            [is_real],
            [is_minimal],
            [count],
        ]

    def search_types(self, info):
        return self._search_again(info, [
            ('List', 'List of characters'),
            ('Random', 'Random character')])


def common_parse(info, query):
    parse_ints(info, query, "modulus", name="modulus")
    parse_ints(info, query, "conductor", name="conductor")
    parse_ints(info, query, "order", name="order")
    if 'parity' in info:
        parity = info['parity']
        if parity == 'even':
            query['parity'] = 1
        elif parity == 'odd':
            query['parity'] = -1
    parse_bool(info, query, "is_primitive", name="is_primitive")
    parse_bool(info, query, "is_real", name="is_real")
    parse_bool(info, query, "is_minimal", name="is_minimal")


def validate_label(label):

    if re.match(r'^\d+\.([\da-z]+)+$', label):
        return True
    else:
        raise ValueError(("It must be of the form modulus.number, with modulus "
                          "and number positive natural numbers"))


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
    modulus, number = label.split(".")
    modulus = int(modulus)
    number = label_to_number(modulus, number)
    return url_for(".render_Dirichletwebpage", modulus=modulus, number=number)

def display_galois_orbit(orbit, modulus):
    trunc = (len(orbit) > 5)
    if trunc:
        orbit = [orbit[0], orbit[-1]]
    disp = [r'<a href="{0}/{1}">\(\chi_{{{0}}}({1}, \cdot)\)</a>'.format(modulus, o) for o in orbit]
    if trunc:
        disp = r"$, \cdots ,$".join(disp)
    else:
        disp = "$,$&nbsp".join(disp)
    return f'<p style="margin-top: 0px;margin-bottom:0px;">\n{disp}\n</p>'

character_columns = SearchColumns([
    LinkCol("label", "character.dirichlet.galois_orbit_label", "Orbit label", lambda label: label.replace(".", "/"), default=True, align="center"),
    MultiProcessedCol("conrey", "character.dirichlet.conrey'", "Conrey labels", ["galois_orbit", "modulus"],
                      display_galois_orbit, default=True, align="center", short_title="Conrey labels"),
    MathCol("modulus", "character.dirichlet.modulus", "Modulus", default=True),
    MathCol("conductor", "character.dirichlet.conductor", "Conductor", default=True),
    MathCol("order", "character.dirichlet.order", "Order", default=True),
    ProcessedCol("parity", "character.dirichlet.primitive", "Parity", lambda parity: "even" if parity == 1 else "odd", default=True),
    CheckCol("is_primitive", "character.dirichlet.primitive", "Primitive", default=True)])

character_columns.dummy_download = True

@search_wrap(
    table=db.char_dir_orbits,
    title="Dirichlet character search results",
    err_title="Dirichlet character search input error",
    columns=character_columns,
    shortcuts={"jump": jump},
    url_for_label=url_for_label,
    learnmore=learn,
    random_projection="label",
    bread=lambda: bread("Search results"),
)
def dirichlet_character_search(info, query):
    common_parse(info, query)


def label_to_number(modulus, number, all=False):
    """
    Takes the second part of a character label and converts it to the second
    part of a Conrey label.  This could be trivial (just casting to an int)
    or could require converting from an orbit label to a number.

    If the label is invalid, returns 0.
    """
    try:
        number = int(number)
    except ValueError:
        # encoding Galois orbit
        if modulus < 10000:
            try:
                orbit_label = '{0}.{1}'.format(modulus, 1 + class_to_int(number))
            except ValueError:
                raise ValueError("Dirichlet Character of this label not found in database")
            else:
                number = db.char_dir_orbits.lucky({'orbit_label': orbit_label}, 'galois_orbit')
                if number is None:
                    raise ValueError("Dirichlet Character of this label not found in database")
                if not all:
                    number = number[0]
        else:
            raise ValueError("The modulus cannot be larger than 10,000")
    else:
        if number <= 0:
            raise ValueError("The number after the '.' cannot be negative")
        elif gcd(modulus, number) != 1:
            raise ValueError("The two numbers either side of '.' must be coprime")
        elif number > modulus:
            raise ValueError("The number after the '.' must be less than the number before")
    return number


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
            info['cols'] = sorted(list({r[1] for r in entries}))
            return render_template("ModulusList.html", **info)
    except ValueError as err:
        flash_error("Error raised in parsing: %s", err)

    if request.args:
        # hidden_search_type for prev/next buttons
        info = to_dict(request.args, search_array=DirichSearchArray())
        info["search_type"] = search_type = info.get("search_type", info.get("hst", "List"))
        if search_type in ['List', 'Random']:
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
    if modulus <= 10000:
        if number is None:
            if get_bread:
                bread_crumbs = bread(
                    [('%s' % modulus, url_for(".render_Dirichletwebpage", modulus=modulus)),
                     ('%s' % orbit_label, url_for(".render_Dirichletwebpage", modulus=modulus, orbit_label=orbit_label))])
                return WebDBDirichletOrbit(**args), bread_crumbs
            return WebDBDirichletOrbit(**args)
        if args.get('orbit_label') is None:
            db_orbit_label = db.char_dir_values.lookup("{}.{}".format(modulus, number), projection='orbit_label')
            orbit_label = cremona_letter_code(int(db_orbit_label.partition('.')[-1]) - 1)
            args['orbit_label'] = orbit_label
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

    if number is None:
        if orbit_label is None:

            if modulus <= 10000:
                info = WebDBDirichletGroup(**args).to_dict()
                info['show_orbit_label'] = True
            else:
                info = WebSmallDirichletGroup(**args).to_dict()

            info['title'] = 'Group of Dirichlet characters of modulus ' + str(modulus)
            info['bread'] = bread([('%s' % modulus, url_for(".render_Dirichletwebpage", modulus=modulus))])
            info['learnmore'] = learn()
            info['code'] = dict([(k[4:], info[k]) for k in info if k[0:4] == "code"])
            info['code']['show'] = {lang: '' for lang in info['codelangs']}  # use default show names
            if 'gens' in info:
                info['generators'] = ', '.join(r'<a href="%s">$\chi_{%s}(%s,\cdot)$' % (url_for(".render_Dirichletwebpage", modulus=modulus, number=g), modulus, g) for g in info['gens'])
            return render_template('CharGroup.html', **info)
        else:
            if modulus <= 10000:
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
                info['code'] = dict([(k[4:], info[k]) for k in info if k[0:4] == "code"])
                info['code']['show'] = {lang: '' for lang in info['codelangs']}  # use default show names
                info['bread'] = bread(
                    [('%s' % modulus, url_for(".render_Dirichletwebpage", modulus=modulus)),
                     ('%s' % orbit_label, url_for(".render_Dirichletwebpage", modulus=modulus, orbit_label=orbit_label))])
                return render_template('CharacterGaloisOrbit.html', **info)
            else:
                flash_error(
                    "Galois orbits have only been computed for modulus up to 10,000, but you entered %s", modulus)
            return redirect(url_for(".render_DirichletNavigation"))

    try:
        number = label_to_number(modulus, number)
    except ValueError:
        flash_error(
            "the value %s is invalid. It should either be a positive integer "
            "coprime to and no greater than the modulus %s, or a letter that "
            "corresponds to a valid orbit index.", args['number'], args['modulus']
        )
        return redirect(url_for(".render_DirichletNavigation"))

    if modulus <= 10000:
        db_orbit_label = db.char_dir_values.lookup("{}.{}".format(modulus, number), projection='orbit_label')
        # The -1 in the line below is because labels index at 1, not 0
        real_orbit_label = cremona_letter_code(int(db_orbit_label.partition('.')[-1]) - 1)
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
    info['code'] = dict([(k[4:], info[k]) for k in info if k[0:4] == "code"])
    info['code']['show'] = {lang: '' for lang in info['codelangs']}  # use default show names
    info['KNOWL_ID'] = 'character.dirichlet.%s.%s' % (modulus, number)
    return render_template('Character.html', **info)

@characters_page.route("/Dirichlet/data/<label>")
def dirchar_data(label):
    if label.count(".") == 2:
        modulus, orbit_label, number = label.split(".")
        title = f"Dirichlet character data - {modulus}.{number}"
        tail = [(f"{modulus}.{number}", url_for(".render_Dirichletwebpage", modulus=modulus, number=number)),
                ("Data", " ")]
        return datapage([f"{modulus}.{orbit_label}", f"{modulus}.{number}"], ["char_dir_orbits", "char_dir_values"], title=title, bread=bread(tail), label_cols=["label", "label"])
    elif label.count(".") == 1:
        modulus, orbit_label = label.split(".")
        title = f"Dirichlet character data - {modulus}.{orbit_label}"
        tail = [(label, url_for(".render_Dirichletwebpage", modulus=modulus, orbit_label=orbit_label)),
                ("Data", " ")]
        return datapage(label, "char_dir_orbits", title=title, bread=bread(tail))
    else:
        return abort(404, f"Invalid label {label}")

def _dir_knowl_data(label, orbit=False):
    modulus, number = label.split('.')
    modulus = int(modulus)
    try:
        numbers = label_to_number(modulus, number, all=True)
    except ValueError:
        return "Invalid label for Dirichlet character: %s" % label
    try:
        if isinstance(numbers, list):
            number = numbers[0]

            def conrey_link(i):
                return "<a href='%s'> %s.%s</a>" % (url_for("characters.render_Dirichletwebpage", modulus=modulus, number=i), modulus, i)
            if len(numbers) <= 2:
                numbers = [conrey_link(k) for k in numbers]
            else:
                numbers = [conrey_link(numbers[0]), '&#8230;', conrey_link(numbers[-1])]
        else:
            number = numbers
            numbers = None

        args = {'type': 'Dirichlet', 'modulus': modulus, 'number': number}
        webchar = make_webchar(args)

        if orbit and modulus <= 10000:
            inf = "Dirichlet character orbit %s.%s\n" % (modulus, webchar.orbit_label)
        else:
            inf = r"Dirichlet character \(\chi_{%s}(%s, \cdot)\)" % (modulus, number) + "\n"
        inf += "<div><table class='chardata'>\n"

        def row_wrap(header, val):
            return "<tr><td>%s: </td><td>%s</td></tr>\n" % (header, val)
        inf += row_wrap('Conductor', webchar.conductor)
        inf += row_wrap('Order', webchar.order)
        inf += row_wrap('Degree', euler_phi(webchar.order))
        inf += row_wrap('Minimal', webchar.isminimal)
        inf += row_wrap('Parity', webchar.parity)
        if numbers:
            inf += row_wrap('Characters', ",&nbsp;".join(numbers))
        if modulus <= 10000:
            if not orbit:
                inf += row_wrap('Orbit label', '%s.%s' % (modulus, webchar.orbit_label))
            inf += row_wrap('Orbit Index', webchar.orbit_index)
        inf += '</table></div>\n'
        if orbit:
            inf += '<div align="right">\n'
            inf += '<a href="%s">%s.%s home page</a>\n' % (str(url_for("characters.render_Dirichletwebpage", modulus=modulus, orbit_label=webchar.orbit_label)), modulus, webchar.orbit_label)
            inf += '</div>\n'
        elif numbers is None:
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
        db.char_dir_values,
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
    table = db.char_dir_orbits
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
    buckets = {"conductor": ["1-10", "11-100", "101-1000", "1001-10000"],
               "modulus": ["1-10", "11-100", "101-1000", "1001-10000"],
               "order": ["1-10", "11-100", "101-1000", "1001-10000"]}
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
        self.nchars = db.char_dir_values.count()
        self.norbits = db.char_dir_orbits.count()
        self.maxmod = db.char_dir_orbits.max("modulus")

    @property
    def short_summary(self):
        return 'The database currently contains %s %s of %s up to %s, lying in %s %s.  Among these, L-functions are available for characters of modulus up to 2,800 (and some of higher modulus).  Here are some <a href="%s">further statistics</a>.' % (
            comma(self.nchars),
            display_knowl("character.dirichlet", "Dirichlet characters"),
            display_knowl("character.dirichlet.modulus", "modulus"),
            comma(self.maxmod),
            comma(self.norbits),
            display_knowl("character.dirichlet.galois_orbit", "Galois orbits"),
            url_for(".statistics"))

    @property
    def summary(self):
        return "The database currently contains %s %s of %s up to %s, lying in %s %s.  The tables below show counts of Galois orbits." % (
            comma(self.nchars),
            display_knowl("character.dirichlet", "Dirichlet characters"),
            display_knowl("character.dirichlet.modulus", "modulus"),
            comma(self.maxmod),
            comma(self.norbits),
            display_knowl("character.dirichlet.galois_orbit", "Galois orbits"))
