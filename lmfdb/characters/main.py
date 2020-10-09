# -*- coding: utf-8 -*-

from __future__ import absolute_import
from lmfdb.app import app
import ast
import re
from six import BytesIO
from flask import render_template, url_for, request, redirect, abort, send_file
from sage.all import gcd, randint, euler_phi
from lmfdb.utils import to_dict, flash_error, SearchArray, YesNoBox, display_knowl, ParityBox, TextBox, CountBox, parse_bool, parse_ints, search_wrap
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.characters.utils import url_character
from lmfdb.characters.web_character import (
        WebDirichletGroup,
        WebSmallDirichletGroup,
        WebDirichletCharacter,
        WebSmallDirichletCharacter,
        WebDBDirichletCharacter,
        WebDBDirichletGroup
)
from lmfdb.characters.web_character import WebHeckeExamples, WebHeckeFamily, WebHeckeGroup, WebHeckeCharacter
from lmfdb.number_fields.web_number_field import WebNumberField
from lmfdb.characters import characters_page
from sage.databases.cremona import class_to_int
from lmfdb import db
from . import ListCharacters
from .ListCharacters import info_from_db_orbit


#### make url_character available from templates
@app.context_processor
def ctx_characters():
    chardata = {}
    chardata['url_character'] = url_character
    return chardata

def learn(current = None):
    r = []
    if current != 'extent':
        r.append( ('Completeness of the data', url_for(".extent_page")) )
    if current != 'source':
        r.append( ('Source of the data', url_for(".how_computed_page")) )
    if current != 'reliability':
        r.append( ('Reliability of the data', url_for(".reliability")) )
    if current != 'labels':
        r.append( ('Dirichlet character labels', url_for(".labels_page")) )
    return r

dirich_credit = "" # TODO should anyone be credited?
def get_bread(tail=[]):
    base = [('Characters',url_for(".render_characterNavigation")),
            ('Dirichlet', url_for(".render_Dirichletwebpage"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

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
    jump_example = "13.2"
    jump_egspan = "e.g. 13.2 for the Dirichlet character \(\displaystyle\chi_{13}(2,·)\), or 13 for the group of characters modulo 13, or 13.f for characters in that Galois orbit."
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
            knowl = "character.dirichlet.conductor",
            label = "Conductor",
            example = "5",
            example_span = "5 or 10,20",
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
        count = CountBox()

        self.refine_array = [
            [modulus, conductor, order], [parity, is_primitive, count],
        ]
        self.browse_array = [
            [modulus],
            [conductor],
            [order],
            [parity],
            [is_primitive],
            [count],
        ]

    def search_types(self, info):
        return self._search_again(info, [
            ('List', 'List of Dirichlet characters'),
            ('Random', 'Random Dirichlet character')])

def common_parse(info, query):
    parse_ints(info, query, "modulus", name="base field")
    parse_ints(info, query, "conductor", name="base cardinality")
    parse_ints(info, query, "order", name="dimension")
    if 'parity' in info:
        parity=info['parity']
        if parity == 'even':
            query['parity'] = 1
        elif parity == 'odd':
            query['parity'] = -1
    parse_bool(info, query, "is_primitive", name="is_primitive")

def learnmore_list():
    return [
        ('Completeness of the data', url_for(".extent_page")),
        ('Source of the data', url_for(".how_computed_page")),
        ('Reliability of the data', url_for(".reliability")),
        ('Dirichlet character labels', url_for(".labels_page")),
    ]

def validate_label(label):
    modulus, number = label.split('.')
    modulus = int(modulus)
    numbers = label_to_number(modulus, number, all=True)
    if numbers == 0:
        raise ValueError("it must be of the form modulus.number, with modulus and number natural numbers")
    return True

def jump(info):
    jump_box = info["jump"].strip() # only called when this present
    try:
        validate_label(jump_box)
    except ValueError as err:
        flash_error("%s is not a valid label: %s.", jump_box, str(err))
    return redirect(url_for_label(jump_box))

def url_for_label(label):
    label = label.replace(" ", "")
    try:
        validate_label(label)
    except ValueError as err:
        flash_error("%s is not a valid label: %s.", label, str(err))
        return redirect(url_for(".render_DirichletNavigation"))
    modulus, number = label.split(".")
    modulus, number = int(modulus), int(number)
    return url_for(".render_Dirichletwebpage", modulus=modulus, number=number)

def download_search(info):
    dltype = info["Submit"]
    #R = PolynomialRing(ZZ, "x")
    #delim = "bracket"
    #com = r"\\"  # single line comment start
    #com1 = ""  # multiline comment start
    #com2 = ""  # multiline comment end
    filename = "weil_polynomials.gp"
    #mydate = time.strftime("%d %B %Y")
    if dltype == "sage":
        com = "#"
        filename = "weil_polynomials.sage"
    if dltype == "magma":
        com = ""
        com1 = "/*"
        com2 = "*/"
        delim = "magma"
        filename = "weil_polynomials.m"
    #s = com1 + "\n"
    #s += com + " Weil polynomials downloaded from the LMFDB on %s.\n" % (mydate)
    #s += com + " Below is a list (called data), collecting the weight 1 L-polynomial\n"
    #s += com + " attached to each isogeny class of an abelian variety.\n"
    #s += "\n" + com2
    #s += "\n"

    #if dltype == "magma":
    #    s += "P<x> := PolynomialRing(Integers()); \n"
    #    s += "data := ["
    #else:
    #    if dltype == "sage":
    #        s += "x = polygen(ZZ) \n"
    #    s += "data = [ "
    #s += "\\\n"
    s= ""
    for f in db.char_dir_orbits.search(ast.literal_eval(info["query"])):
        s += str(f) + "\n"
    #s = s[:-3]
    #s += "]\n"
    #if delim == "magma":
    #    s = s.replace("[", "[*")
    #    s = s.replace("]", "*]")
    #    s += ";"
    strIO = BytesIO()
    strIO.write(s.encode('utf-8'))
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)

@search_wrap(
    template="character_search_results.html",
    table=db.char_dir_orbits,
    title="Dirichlet character search results",
    err_title="Dirichlet character search input error",
    shortcuts={
        "jump": jump,
        "download": download_search
    },
    postprocess=lambda res, info, query: sum([info_from_db_orbit(x) for x in res],[]),
    url_for_label=url_for_label,
    learnmore=learnmore_list,
    bread=lambda: get_bread(("Search results", " ")),
    credit=lambda: dirich_credit,
)
def dirichlet_character_search(info, query):
    common_parse(info, query)

@characters_page.route("/Dirichlet/Labels")
def labels_page():
    info = {}
    info['title'] = 'Dirichlet character labels'
    info['bread'] = get_bread(('Labels', ''))
    info['learnmore'] = learn('labels')
    return render_template("single.html", kid='character.dirichlet.conrey', **info)

@characters_page.route("/Dirichlet/Source")
def how_computed_page():
    info = {}
    info['title'] = 'Source of Dirichlet character data'
    info['bread'] = get_bread(('Source', ''))
    info['learnmore'] = learn('source')
    return render_template("single.html", kid='rcs.source.character.dirichlet', **info)

@characters_page.route("/Dirichlet/Reliability")
def reliability():
    info = {}
    info['title'] = 'Reliability of Dirichlet character data'
    info['bread'] = get_bread(('Reliability', ''))
    info['learnmore'] = learn('reliability')
    return render_template("single.html", kid='rcs.rigor.character.dirichlet', **info)

@characters_page.route("/Dirichlet/Completeness")
def extent_page():
    info = {}
    info['title'] = 'Completeness of Dirichlet character data'
    info['bread'] = get_bread(('Extent', ''))
    info['learnmore'] = learn('extent')
    return render_template("single.html", kid='dq.character.dirichlet.extent',
                           **info)

def make_webchar(args):
    modulus = int(args['modulus'])
    if modulus < 10000:
        return WebDBDirichletCharacter(**args)
    elif modulus < 100000:
        return WebDirichletCharacter(**args)
    else:
        return WebSmallDirichletCharacter(**args)

<<<<<<< HEAD
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
                return 0
            else:
                number = db.char_dir_orbits.lucky({'orbit_label':orbit_label}, 'galois_orbit')
                if number is None:
                    return 0
                if not all:
                    number = number[0]
        else:
            return 0
    else:
        if number <= 0 or gcd(modulus, number) != 1 or number > modulus:
            return 0
    return number

@characters_page.route("/Dirichlet")
@characters_page.route("/Dirichlet/")
def render_DirichletNavigation():
    info = to_dict(request.args, search_array=DirichSearchArray())
    if request.args:
        # hidden_search_type for prev/next buttons
        info["search_type"] = search_type = info.get("search_type", info.get("hst", "List"))
        if search_type in ['List', 'Random']:
            return dirichlet_character_search(info)
        assert False
    #else:
        #return dirichlet_character_browse(info)
    args = to_dict(request.args)
    info = {'args': request.args}
    info['bread'] = get_bread()
=======
    info = {'args':args}
    info['bread'] = get_bread()
>>>>>>> 05f565bd7632b97784cd5a5825bbd59fdb410c68
    info['learnmore'] = learn()

    try:
        if 'modbrowse' in args:
            arg = args['modbrowse']
            arg = arg.split('-')
            modulus_start = int(arg[0])
            modulus_end = int(arg[1])
            info['title'] = 'Dirichlet characters of modulus ' + str(modulus_start) + '-' + str(modulus_end)
            info['credit'] = 'Sage'
            h, c, rows, cols = ListCharacters.get_character_modulus(modulus_start, modulus_end)
            info['contents'] = c
            info['headers'] = h
            info['rows'] = rows
            info['cols'] = cols
            return render_template("ModulusList.html", **info)

        elif 'condbrowse' in args:
            arg = args['condbrowse']
            arg = arg.split('-')
            conductor_start = int(arg[0])
            conductor_end = int(arg[1])
            info['conductor_start'] = conductor_start
            info['conductor_end'] = conductor_end
            info['title'] = 'Dirichlet characters of conductor ' + str(conductor_start) + '-' + str(conductor_end)
            info['credit'] = "Sage"
            info['contents'] = ListCharacters.get_character_conductor(conductor_start, conductor_end + 1)
            return render_template("ConductorList.html", **info)

        elif 'ordbrowse' in args:
            arg = args['ordbrowse']
            arg = arg.split('-')
            order_start = int(arg[0])
            order_end = int(arg[1])
            info['order_start'] = order_start
            info['order_end'] = order_end
            info['title'] = 'Dirichlet characters of orders ' + str(order_start) + '-' + str(order_end)
            info['credit'] = 'SageMath'
            info['contents'] = ListCharacters.get_character_order(order_start, order_end + 1)
            return render_template("OrderList.html", **info)

        elif 'label' in args:
            label = args['label'].replace(' ','')
            if re.match(r'^[1-9][0-9]*\.[1-9][0-9]*$', label):
                slabel = label.split('.')
                m,n = int(slabel[0]), int(slabel[1])
                if m==n==1 or n < m and gcd(m,n) == 1:
                    return redirect(url_for(".render_Dirichletwebpage", modulus=slabel[0], number=slabel[1]))
            if re.match(r'^[1-9][0-9]*\.[a-z]+$', label):
                slabel = label.split('.')
                return redirect(url_for(".render_Dirichletwebpage", modulus=int(slabel[0]), number=slabel[1]))
            if re.match(r'^[1-9][0-9]*$', label):
                return redirect(url_for(".render_Dirichletwebpage", modulus=label), 301)

            flash_error("%s is not a valid label for a Dirichlet character.  It should be of the form <span style='color:black'>q.n</span>, where q and n are coprime positive integers with n < q, or q=n=1.", label)
            return render_template('CharacterNavigate.html', **info)
    except ValueError as err:
        flash_error("Error raised in parsing: %s", err)
        return render_template('CharacterNavigate.html', title='Dirichlet characters')

    if args:
        # if user clicked refine search, reset start to 0
        if args.get('refine'):
            args['start'] = '0'
        try:
            search = ListCharacters.CharacterSearch(args)
        except ValueError as err:
            info['err'] = str(err)
            return render_template("CharacterNavigate.html" if "search" in args else "character_search_results.html" , **info)
        info['info'] = search.results()
        info['title'] = 'Dirichlet character search results'
<<<<<<< HEAD
        info['bread'] = get_bread(('Search results', ''))
        info['credit'] = 'SageMath'
        return render_template("character_search_results.html", **info)
    else:
        info = to_dict(request.args, search_array=DirichSearchArray())
        info['title'] = 'Dirichlet characters'
        return render_template('CharacterNavigate.html', info=info,**info)


=======
        info['bread'] = get_bread('Search results')
        info['credit'] = 'SageMath'
        return render_template("character_search_results.html", **info)
    else:
       info['title'] = 'Dirichlet characters'
       return render_template('CharacterNavigate.html', **info)

@characters_page.route("/Dirichlet/Labels")
def labels_page():
    info = {}
    info['title'] = 'Dirichlet character labels'
    info['bread'] = get_bread('Labels')
    info['learnmore'] = learn('labels')
    return render_template("single.html", kid='character.dirichlet.conrey', **info)

@characters_page.route("/Dirichlet/Source")
def how_computed_page():
    info = {}
    info['title'] = 'Source of Dirichlet character data'
    info['bread'] = get_bread('Source')
    info['learnmore'] = learn('source')
    return render_template("single.html", kid='rcs.source.character.dirichlet', **info)

@characters_page.route("/Dirichlet/Reliability")
def reliability():
    info = {}
    info['title'] = 'Reliability of Dirichlet character data'
    info['bread'] = get_bread('Reliability')
    info['learnmore'] = learn('reliability')
    return render_template("single.html", kid='rcs.rigor.character.dirichlet', **info)

@characters_page.route("/Dirichlet/Completeness")
def extent_page():
    info = {}
    info['title'] = 'Completeness of Dirichlet character data'
    info['bread'] = get_bread('Extent')
    info['learnmore'] = learn('extent')
    return render_template("single.html", kid='dq.character.dirichlet.extent',
                           **info)

def make_webchar(args):
    modulus = int(args['modulus'])
    if modulus < 10000:
        return WebDBDirichletCharacter(**args)
    elif modulus < 100000:
        return WebDirichletCharacter(**args)
    else:
        return WebSmallDirichletCharacter(**args)

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
                return 0
            else:
                number = db.char_dir_orbits.lucky({'orbit_label':orbit_label}, 'galois_orbit')
                if number is None:
                    return 0
                if not all:
                    number = number[0]
        else:
            return 0
    else:
        if number <= 0 or gcd(modulus, number) != 1 or number > modulus:
            return 0
    return number

def url_for_label(label):
    """
    INPUT:

    - label -- a string such as "1052.279" giving a specific Dirichlet character (not an orbit)

    OUTPUT:

    the URL for that Dirichlet character's homepage
    """
    modulus, number = label.split(".")
    return url_for(".render_Dirichletwebpage", modulus=modulus, number=number)

@characters_page.route("/Dirichlet")
@characters_page.route("/Dirichlet/")
>>>>>>> 05f565bd7632b97784cd5a5825bbd59fdb410c68
@characters_page.route("/Dirichlet/<modulus>")
@characters_page.route("/Dirichlet/<modulus>/")
@characters_page.route("/Dirichlet/<modulus>/<number>")
def render_Dirichletwebpage(modulus=None, number=None):

    modulus = modulus.replace(' ','')
    if number is None and re.match(r'^[1-9][0-9]*\.([1-9][0-9]*|[a-z]+)$', modulus):
        modulus, number = modulus.split('.')
        return redirect(url_for(".render_Dirichletwebpage", modulus=modulus, number=number), 301)

    args={}
    args['type'] = 'Dirichlet'
    args['modulus'] = modulus
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
        if modulus < 10000:
            info = WebDBDirichletGroup(**args).to_dict()
            info['show_orbit_label'] = True
        elif modulus < 100000:
            info = WebDirichletGroup(**args).to_dict()
        else:
            info = WebSmallDirichletGroup(**args).to_dict()
        info['title'] = 'Group of Dirichlet characters of modulus ' + str(modulus)
        info['bread'] = get_bread([('%d'%modulus, url_for(".render_Dirichletwebpage", modulus=modulus))])
        info['learnmore'] = learn()
        info['code'] = dict([(k[4:],info[k]) for k in info if k[0:4] == "code"])
        info['code']['show'] = { lang:'' for lang in info['codelangs'] } # use default show names
        if 'gens' in info:
            info['generators'] = ', '.join([r'<a href="%s">$\chi_{%s}(%s,\cdot)$'%(url_for(".render_Dirichletwebpage",modulus=modulus,number=g),modulus,g) for g in info['gens']])
        return render_template('CharGroup.html', **info)

    number = label_to_number(modulus, number)
    if number == 0:
        flash_error(
            "the value %s is invalid. It should either be a positive integer "
            "coprime to and no greater than the modulus %s, or a letter that "
            "corresponds to a valid orbit index.", args['number'], args['modulus']
        )
        return redirect(url_for(".render_DirichletNavigation"))
    args['number'] = number
    webchar = make_webchar(args)
    info = webchar.to_dict()
        [('%s'%modulus, url_for(".render_Dirichletwebpage", modulus=modulus)),
         ('%s'%number, url_for(".render_Dirichletwebpage", modulus=modulus, number=number)) ])
    info['learnmore'] = learn()
    info['code'] = dict([(k[4:],info[k]) for k in info if k[0:4] == "code"])
    info['code']['show'] = { lang:'' for lang in info['codelangs'] } # use default show names
    info['KNOWL_ID'] = 'character.dirichlet.%s.%s' % (modulus, number)
    return render_template('Character.html', **info)

def _dir_knowl_data(label, orbit=False):
    modulus, number = label.split('.')
    modulus = int(modulus)
    numbers = label_to_number(modulus, number, all=True)
    if numbers == 0:
        return "Invalid label for Dirichlet character: %s" % label
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
    args={'type': 'Dirichlet', 'modulus': modulus, 'number': number}
    webchar = make_webchar(args)
    if orbit and modulus <= 10000:
        inf = "Dirichlet character orbit %d.%s\n" % (modulus, webchar.orbit_label)
    else:
        inf = r"Dirichlet character \(\chi_{%d}(%d, \cdot)\)" % (modulus, number) + "\n"
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
            inf += row_wrap('Orbit label', '%d.%s' % (modulus, webchar.orbit_label))
        inf += row_wrap('Orbit Index', webchar.orbit_index)
    inf += '</table></div>\n'
    if numbers is None:
        inf += '<div align="right">\n'
        inf += '<a href="%s">%s home page</a>\n' % (str(url_for("characters.render_Dirichletwebpage", modulus=modulus, number=number)), label)
        inf += '</div>\n'
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
    modulus = randint(1,9999)
    number = randint(1,modulus-1)
    while gcd(modulus,number) > 1:
        number = randint(1,modulus-1)
    return redirect(url_for('.render_Dirichletwebpage', modulus=str(modulus), number=str(number)))

@characters_page.route('/Dirichlet/interesting')
def interesting():
    return interesting_knowls(
        "character.dirichlet",
        db.char_dir_values,
        url_for_label=url_for_label,
        title="Some interesting Dirichlet characters",
        bread=get_bread("Interesting"),
        credit="SageMath",
        learnmore=learn())

@characters_page.route("/calc-<calc>/Dirichlet/<int:modulus>/<int:number>")
def dc_calc(calc, modulus, number):
    val = request.args.get("val", [])
    args = {'type': 'Dirichlet', 'modulus': modulus, 'number': number}
    if not val:
        return abort(404)
    try:
        if calc == 'value':
            return WebDirichletCharacter(**args).value(val)
        if calc == 'gauss':
            return WebDirichletCharacter(**args).gauss_sum(val)
        elif calc == 'jacobi':
            return WebDirichletCharacter(**args).jacobi_sum(val)
        elif calc == 'kloosterman':
            return WebDirichletCharacter(**args).kloosterman_sum(val)
        else:
            return abort(404)
    except Warning as e:
        return "<span style='color:gray;'>%s</span>" % e
    except Exception:
        return "<span style='color:red;'>Error: bad input</span>"

@characters_page.route("/Hecke/")
@characters_page.route("/Hecke/<number_field>")
@characters_page.route("/Hecke/<number_field>/<modulus>")
@characters_page.route("/Hecke/<number_field>/<modulus>/<number>")
def render_Heckewebpage(number_field=None, modulus=None, number=None):
    #args = request.args
    #temp_args = to_dict(args)

    args = {}
    args['type'] = 'Hecke'
    args['number_field'] = number_field
    args['modulus'] = modulus
    args['number'] = number

    if number_field is None:
        info = WebHeckeExamples(**args).to_dict()
        return render_template('Hecke.html', **info)
    else:
        WNF = WebNumberField(number_field)
        if WNF.is_null():
            return abort(404, "Number field %s not found." % number_field)

    if modulus is None:
        try:
            info = WebHeckeFamily(**args).to_dict()
        except (ValueError,KeyError,TypeError) as err:
            return abort(404, err.args)
        return render_template('CharFamily.html', **info)
    elif number is None:
        try:
            info = WebHeckeGroup(**args).to_dict()
        except (ValueError,KeyError,TypeError):
            # Typical failure case is a GP error inside bnrinit which we don't really want to display
            return abort(404, 'Unable to construct modulus %s for number field %s' % (modulus, number_field))
        m = info['modlabel']
        info['bread'] = [('Characters', url_for(".render_characterNavigation")),
                         ('Hecke', url_for(".render_Heckewebpage")),
                         ('Number field %s'%number_field, url_for(".render_Heckewebpage", number_field=number_field)),
                         ('%s'%m,  url_for(".render_Heckewebpage", number_field=number_field, modulus=m))]
        info['code'] = dict([(k[4:],info[k]) for k in info if k[0:4] == "code"])
        info['code']['show'] = { lang:'' for lang in info['codelangs'] } # use default show names
        return render_template('CharGroup.html', **info)
    else:
        try:
            X = WebHeckeCharacter(**args)
        except (ValueError,KeyError,TypeError):
            return abort(404, 'Unable to construct Hecke character %s modulo %s in number field %s.' % (number,modulus,number_field))
        info = X.to_dict()
        info['bread'] = [('Characters',url_for(".render_characterNavigation")),
                         ('Hecke',  url_for(".render_Heckewebpage")),
                         ('Number field %s'%number_field,url_for(".render_Heckewebpage", number_field=number_field)),
                         ('%s'%X.modulus, url_for(".render_Heckewebpage", number_field=number_field, modulus=X.modlabel)),
                         ('%s'%X.number2label(X.number), '')]
        info['code'] = dict([(k[4:],info[k]) for k in info if k[0:4] == "code"])
        info['code']['show'] = { lang:'' for lang in info['codelangs'] } # use default show names
        return render_template('Character.html', **info)

@characters_page.route("/calc-<calc>/Hecke/<number_field>/<modulus>/<number>")
def hc_calc(calc, number_field, modulus, number):
    val = request.args.get("val", [])
    args = {'type':'Hecke', 'number_field':number_field, 'modulus':modulus, 'number':number}
    if not val:
        return abort(404)
    try:
        if calc == 'value':
            return WebHeckeCharacter(**args).value(val)
        else:
            return abort(404)
    except Exception as e:
        return "<span style='color:red;'>ERROR: %s</span>" % e

###############################################################################
##  TODO: refactor the following
###############################################################################

@characters_page.route("/Dirichlet/table")
def dirichlet_table():
    args = to_dict(request.args)
    mod = args.get('modulus',1)
    return redirect(url_for('characters.render_Dirichletwebpage',modulus=mod))

# FIXME: these group table pages are used by number fields pages.
# should refactor this into WebDirichlet.py
@characters_page.route("/Dirichlet/grouptable")
def dirichlet_group_table(**args):
    modulus = request.args.get("modulus", 1, type=int)
    info = to_dict(args)
    if "modulus" not in info:
        info["modulus"] = modulus
    info['bread'] = get_bread(('Table', ' '))
    info['credit'] = 'SageMath'
    char_number_list = request.args.get("char_number_list",None)
    if char_number_list is not None:
        info['char_number_list'] = char_number_list
        char_number_list = [int(a) for a in char_number_list.split(',')]
        info['poly'] = request.args.get("poly", '???')
    else:
        return abort(404, 'grouptable needs char_number_list argument')
    h, c = get_group_table(modulus, char_number_list)
    info['headers'] = h
    info['contents'] = c
    info['title'] = 'Group of Dirichlet characters'
    return render_template("CharacterGroupTable.html", **info)


def get_group_table(modulus, char_list):
    # Move 1 to the front of the list
    char_list.insert(0, char_list.pop(next(j for j in range(len(char_list)) if char_list[j]==1)))
    headers = [j for j in char_list]  # Just a copy
    if modulus == 1:
        rows = [[1]]
    else:
        rows = [[(j * k) % modulus for k in char_list] for j in char_list]
    return headers, rows
