# -*- coding: utf-8 -*-
#*****************************************************************************
#  Copyright (C) 2010 Fredrik Strömberg <fredrik314@gmail.com>,
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#  The full text of the GPL is available at:
#
#                  http://www.gnu.org/licenses/
#*****************************************************************************
r"""
Utilities file for elliptic (holomorphic) modular forms.

AUTHOR: Fredrik Strömberg

"""
import random
import sage.plot.plot
from flask import jsonify
from lmfdb.utils import *
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf, emf_logger, default_prec
logger = emf_logger
from sage.all import dimension_new_cusp_forms, vector, dimension_modular_forms, dimension_cusp_forms, is_odd, loads, dumps, Gamma0, Gamma1, Gamma
from sage.misc.cachefunc import cached_function 
from lmfdb.modular_forms.backend.mf_utils import my_get
from plot_dom import draw_fundamental_domain
import lmfdb.base
from bson.binary import *
from lmfdb.number_fields.number_field import poly_to_field_label, field_pretty
from lmfdb.utils import web_latex_split_on_re, web_latex_split_on_pm

try:
    from dirichlet_conrey import *
except:
    emf_logger.critical("Could not import dirichlet_conrey!")

def newform_label(level, weight, character, label, embedding=None, make_cache_label=False):
    l = ''
    if make_cache_label:
        l = 'emf.'
    if embedding is None:
        l += "{0}.{1}.{2}{3}".format(level, weight, character, label)
    else:
        l += "{0}.{1}.{2}{3}.{4}".format(level, weight, character, label, embedding)
    return l

def parse_newform_label(label):
    r"""
    Essentially the inverse of the above. Given "N.k.ix" it returns N,k,i,x
    or given "N.k.ix.d" return N,k,i,x,d
    """
    if not isinstance(label,basestring):
        raise ValueError,"Need label in string format"
    l = label.split(".")
    if len(l) not in [3,4]:
        raise ValueError,"{0} is not a valid newform label!".format(label)
    if not l[0].isdigit() or not l[1].isdigit():
        raise ValueError,"{0} is not a valid newform label!".format(label)
    level = int(l[0]); weight = int(l[1])
    character = "".join([x for x in l[2] if x.isdigit()])
    orbit_label = "".join([x for x in l[2] if x.isalpha()])
    if orbit_label == "" or not character.isdigit():
        raise ValueError,"{0} is not a valid newform label!".format(label)
    if len(l)==4:
        emb = int(l[3])
        return level,weight,int(character),orbit_label,emb
    else:
        return level,weight,int(character),orbit_label
        
def space_label(level, weight, character, make_cache_label=False):
    l = ''
    if make_cache_label:
        l = 'emf.'
    return l+"{0}.{1}.{2}".format(level, weight, character)

def parse_space_label(label):
    if not isinstance(label,basestring):
        raise ValueError,"Need label in string format"    
    l = label.split(".")
    level = int(l[0]); weight = int(l[1]); character = int(l[2])
    return level,weight,character

def parse_range(arg, parse_singleton=int):
    # TODO: graceful errors
    if type(arg) == parse_singleton:
        return arg
    if ',' in arg:
        return [parse_range(a) for a in arg.split(',')]
    elif '-' in arg[1:]:
        ix = arg.index('-', 1)
        start, end = arg[:ix], arg[ix + 1:]
        q = {}
        if start:
            q['min'] = parse_singleton(start)
        if end:
            q['max'] = parse_singleton(end)
        return q
    else:
        return parse_singleton(arg)


def extract_limits_as_tuple(arg, field, defaults=(1, 10)):
    if type(arg.get(field)) == dict:
        limits = (arg[field]['min'], arg[field]['max'])
    else:
        if arg.get(field):
            limits = (arg[field], arg[field])
        else:
            limits = defaults
    return limits


def extract_data_from_jump_to(s):
    label = ''
    weight = 0
    character = 0
    level = 1
    if s == 'delta':
        weight = 12
        level = 1
        label = "a"
    else:
        # first see if we have a label or not, i.e. if we have precisely one string of letters at the end
        test = re.findall("[a-z]+", s)
        if len(test) == 1:
            label = test[0]
            # emf_logger.debug("label1={0}".format(label))
            # the first string of integers should be the level
        test = re.findall("\d+", s)
        if not test is None and len(test)>0:
            level = int(test[0])
            if len(test) > 1:  # we also have weight
                weight = int(test[1])
            if len(test) > 2:  # we also have character
                character = int(test[2])
    emf_logger.debug("label=%s" % label)
    emf_logger.debug("level=%s" % level)
    args = dict()
    args['level'] = int(level)
    args['weight'] = int(weight) 
    args['character'] = int(character)
    if label: args['label'] = label
    return args


def ajax_more2(callback, *arg_list, **kwds):
    r"""
    Like ajax_more but accepts increase in two directions.
    Call with
    ajax_more2(function,{'arg1':[x1,x2,...,],'arg2':[y1,y2,...]},'text1','text2')
    where function takes two named argument 'arg1' and 'arg2'
    """
    inline = kwds.get('inline', True)
    text = kwds.get('text', 'more')
    emf_logger.debug("inline={0}".format(inline))
    emf_logger.debug("text={0}".format(text))
    text0 = text[0]
    text1 = text[1]
    emf_logger.debug("arglist={0}".format(arg_list))
    nonce = hex(random.randint(0, 1 << 128))
    if inline:
        args = arg_list[0]
        emf_logger.debug("args={0}".format(args))
        key1, key2 = args.keys()
        l1 = args[key1]
        l2 = args[key2]
        emf_logger.debug("key1={0}".format(key1))
        emf_logger.debug("key2={0}".format(key2))
        emf_logger.debug("l1={0}".format(l1))
        emf_logger.debug("l2={0}".format(l2))
        args = {key1: l1[0], key2: l2[0]}
        l11 = l1[1:]
        l21 = l2[1:]
        # arg_list = arg_list[1:]
        arg_list1 = {key1: l1, key2: l21}
        arg_list2 = {key1: l11, key2: l2}
        # emf_logger.debug("arglist1={0}".format(arg_list))
        if isinstance(args, tuple):
            res = callback(*arg_list)
        elif isinstance(args, dict):
            res = callback(**args)
        else:
            res = callback(args)
            res = web_latex(res)
    else:
        res = ''
    emf_logger.debug("arg_list1={0}".format(arg_list1))
    emf_logger.debug("arg_list2={0}".format(arg_list2))
    arg_list1 = (arg_list1,)
    arg_list2 = (arg_list2,)
    if arg_list1 or arg_list2:
        url1 = ajax_url(ajax_more2, callback, *arg_list1, inline=True, text=text)
        url2 = ajax_url(ajax_more2, callback, *arg_list2, inline=True, text=text)
        emf_logger.debug("arg_list1={0}".format(url1))
        emf_logger.debug("arg_list2={0}".format(url2))
        s0 = """<span id='%(nonce)s'>%(res)s """  % locals()
        s1 = """[<a onclick="$('#%(nonce)s').load('%(url1)s', function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text0)s</a>""" % locals()
        t = """| <a onclick="$('#%(nonce)s').load('%(url2)s', function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text1)s</a>]</span>""" % locals()
        return (s0 + s1 + t)
    else:
        return res


def ajax_url(callback, *args, **kwds):
    if '_ajax_sticky' in kwds:
        _ajax_sticky = kwds.pop('_ajax_sticky')
    else:
        _ajax_sticky = False
    if not isinstance(args, tuple):
        args = args,
    nonce = hex(random.randint(0, 1 << 128))
    pending[nonce] = callback, args, kwds, _ajax_sticky
    return url_for('ajax_result', id=nonce)


def ajax_once(callback, *arglist, **kwds):
    r"""
    """

    text = kwds.get('text', 'more')
    emf_logger.debug("text={0}".format(text))
    emf_logger.debug("arglist={0}".format(arglist))
    emf_logger.debug("kwds={0}".format(kwds))
    # emf_logger.debug("req={0}".format(request.args
    nonce = hex(random.randint(0, 1 << 128))
    res = callback()
    url = ajax_url(ajax_once, arglist, kwds, inline=True)
    s0 = """<span id='%(nonce)s'>%(res)s """  % locals()
    # s1 = """[<a onclick="$('#%(nonce)s').load('%(url)s',
    # {'level':22,'weight':4},function() {
    # MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return
    # false;" href="#">%(text)s</a>""" % locals()
    s1 = """[<a onclick="$('#%(nonce)s').load('%(url)s', {a:1},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text)s</a>""" % locals()
    return s0 + s1


def ajax_later(callback, *arglist, **kwds):
    r"""
    Try to make a function that gets called after displaying the page.
    """

    text = kwds.get('text', 'more')
    text = 'more'
    emf_logger.debug("text={0}".format(text))
    emf_logger.debug("arglist={0}".format(arglist))
    emf_logger.debug("kwds={0}".format(kwds))
    emf_logger.debug("callback={0}".format(callback))
    # emf_logger.debug("req={0}".format(request.args
    nonce = hex(random.randint(0, 1 << 128))
    # do not call the first time around
    if "do_now" in kwds:
        if kwds['do_now'] == 1:
            do_now = 0
        else:
            do_now = 1
    else:
        do_now = 0
    if not do_now:
        url = ajax_url(ajax_later, callback, *arglist, inline=True, do_now=do_now, _ajax_sticky=True)
        emf_logger.debug("ajax_url={0}".format(url))
        s0 = """<span id='%(nonce)s'></span>"""  % locals()
        s1 = """<a class='later' href=# id='%(nonce)s' onclick='this_fun()'>%(text)s</a>""" % locals()
        s2 = """<script>
        function this_fun(){
        $.getJSON('%(url)s',{do_now:1},
        function(data) {
        $(\"span#%(nonce)s\").text(data.result);
        });
        return true;
        };
        </script>

        """ % locals()
        emf_logger.debug("s0+s1={0}".format(s2 + s0))
        return s2 + s0 + s1
    else:
        res = callback(do_now=do_now)
        return jsonify(result=res)


def render_fd_plot(level, info, **kwds):
    group = None
    grouptype = None
    if('group' in info):
        group = info['group']
        # we only allow standard groups
    if 'grouptype' in info:
        grouptype = int(info['grouptype'])
        if info['grouptype'] == 0:
            group = 'Gamma0'
        elif info['grouptype'] == 1:
            group = 'Gamma1'
    if (group not in ['Gamma0', 'Gamma', 'Gamma1']):
        group = 'Gamma0'
        grouptype = int(0)
    else:
        if grouptype is None:
            if group == 'Gamma':
                grouptype = int(-1)
            elif group == 'Gamma0':
                grouptype = int(0)
            else:
                grouptype = int(1)
    db_name = 'SL2Zsubgroups'
    collection = 'groups'
    C = lmfdb.base.getDBConnection()
    emf_logger.debug("C={0}, level={1}, grouptype={2}".format(C, level, grouptype))
    if not C:
        emf_logger.critical("Could not connect to Database! C={0}".format(C))
    if not db_name in C.database_names():
        emf_logger.critical("Incorrect database name {0}. \n Available databases are:{1}".format(
            db_name, C.database_names()))
    if not collection in C[db_name].collection_names():
        emf_logger.critical("Incorrect collection {0} in database {1}. \n Available collections are:{2}".format(collection, db_name, C[db_name].collection_names()))

    find = C[db_name][collection].find_one({'level': int(level), 'type': int(grouptype)})
    if find:
        if find.get('domain'):
            # domain=loads(str(find['domain']))
            domain = find['domain']
        emf_logger.debug('Found fundamental domain in database')
    else:
        emf_logger.debug('Drawing fundamental domain for group {0}({1})'.format(group, level))
        domain = draw_fundamental_domain(level, group, **kwds)
            # G=Gamma0(level)
            # C[db_name][collection].insert({'level':int(level), 'type':type, 'index':int(G.index), 'G':bson.binary.Binary(dumps(G)), 'domain': bson.binary.Binary(dumps(domain))})
            # emf_logger.debug('Inserting group and fundamental domain in database')
    return domain


def sage_character_to_conrey_index(chi, N):
    r"""
    For Dirichlet character chi,
    we return the corresponding Conrey Index n, so that x(m)=chi_N(n,m).
    """
    Dc = DirichletGroup_conrey(N)
    for c in Dc:
        if c.sage_character() == chi:
            return c.number()
    return -1


@cached_function
def dirichlet_character_sage_galois_orbits_reps(N):
    """
    Return representatives for the Galois orbits of Dirichlet characters of level N.
    """
    return [X[0] for X in DirichletGroup(N).galois_orbits()]

@cached_function
def dirichlet_character_conrey_galois_orbits_reps(N):
    """
    Return list of representatives for the Galois orbits of Conrey Dirichlet characters of level N.
    We always take the one that has the smallest index.
    """
    D = DirichletGroup_conrey(N)
    if N == 1:
        return [D[1]]
    Ds = dirichlet_character_sage_galois_orbits_reps(N)
    Dl = list(D)
    reps=[]
    for x in D:
        if x not in Dl:
            continue
        orbit_of_x = sorted(x.galois_orbit())
        reps.append(orbit_of_x[0])
        for xx in orbit_of_x:
            if xx not in Dl:
                continue
            Dl.remove(xx)
    return reps
    

@cached_function
def dimension_from_db(level,weight,chi=None,group='gamma0'):
    import json
    db = lmfdb.base.getDBConnection()['modularforms2']['webmodformspace_dimension']
    q = db.find_one({'group':group})
    dim_table = {}
    if q:
        dim_table = q.get('data',{})
        dim_table = json.loads(dim_table)
    if group=='gamma0' and chi<>None:
        d,t = dim_table.get(str(level),{}).get(str(weight),{}).get(str(chi),[-1,0])
        return  d,t
    elif chi is None:
        d,t = dim_table.get(str(level),{}).get(str(weight),[-1,0])
        return  d,t
    elif chi == 'all':
        res = {level: {weight:{}}}
        dtable = dim_table.get(str(level),{}).get(str(weight),{})
        for i in dtable.keys():
            res[level][weight][int(i)] = dtable[i]
        return res

def field_label(F, pretty = True, check=False):
    r"""
      Returns the LMFDB label of the field F.
    """
    if F.absolute_degree() == 1:
        p = 'x'
    else:
        pp = F.absolute_polynomial()
        x = pp.parent().gen()
        p = str(pp).replace(str(x), 'x')
    l = poly_to_field_label(p)
    if l is None:
        if check:
            return False
        else:
            if pretty:
                return web_latex_split_on_pm(pp)
            else:
                return pp
    else:
        if check:
            return True
    if pretty:
        return field_pretty(l)
    else:
        return l

@cached_function
def dirichlet_character_conrey_galois_orbit_embeddings(N,xi):
    r"""
       Returns a dictionary that maps the Conrey numbers
       of the Dirichlet characters in the Galois orbit of x
       to the powers of $\zeta_{\phi(N)}$ so that the corresponding
       embeddings map the labels.

       Let $\zeta_{\phi(N)}$ be the generator of the cyclotomic field
       of $N$-th roots of unity which is the base field
       for the coefficients of a modular form contained in the database.
       Considering the space $S_k(N,\chi)$, where $\chi = \chi_N(m, \cdot)$,
       if embeddings()[m] = n, then $\zeta_{\phi(N)}$ is mapped to
       $\zeta_{\phi(N)}^n = \mathrm{exp}(2\pi i n /\phi(N))$.
    """    
    embeddings = {}
    base_number = 0
    base_number = xi
    embeddings[base_number] = 1
    for n in range(2,N):
        if gcd(n,N) == 1:
            embeddings[Mod(base_number,N)**n] = n
    return embeddings
