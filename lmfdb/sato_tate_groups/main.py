# -*- coding: utf-8 -*-
import re

from flask import render_template, url_for, redirect, request, abort
from sage.all import ZZ, QQ, cos, sin, pi, list_plot, circle, line2d, cached_function

from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import (
    to_dict, encode_plot, flash_error, display_knowl, search_wrap,
    SearchArray, TextBox, SelectBox, CountBox, YesNoBox,
    StatsDisplay, totaler, proportioners, prop_int_pretty,
    parse_ints, parse_rational, parse_bool, clean_input, redirect_no_cache)
from lmfdb.utils.search_parsing import search_parser
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, CheckCol, ProcessedCol
from lmfdb.api import datapage
from lmfdb.groups.abstract.main import abstract_group_namecache, abstract_group_display_knowl
from lmfdb.sato_tate_groups import st_page

###############################################################################
# Globals
###############################################################################

MU_LABEL_RE = r'^0\.1\.[1-9][0-9]*$'
MU_LABEL_NAME_RE = r'^0\.1\.mu\([1-9][0-9]*\)$'
NU1_MU_LABEL_RE = r'^[1-9][0-9]*\.2\.[1B]\.d[1-9][0-9]*$'
SU2_MU_LABEL_RE = r'^[1-9][0-9]*\.2\.[3A]\.c[1-9][0-9]*$'
ST_OLD_LABEL_RE = r'^\d+\.\d+\.\d+\.\d+\.\d+[a-z]+$'
ST_OLD_LABEL_SHORT_RE = r'^\d+\.\d+\.\d+\.\d+\.\d+$'
ST_LABEL_RE = r'^\d+\.\d+\.[A-Z]+\.\d+\.\d+[a-z]+$'
ST_LABEL_SPLIT_RE = r'(^\d+)\.(\d+)\.([A-Z]+)\.(\d+)\.(\d+)([a-z])+$'
ST_LABEL_SHORT_RE = r'^\d+\.\d+\.[A-Z]+\.\d+\.\d+$'
ST_LABEL_NAME_RE = r'^\d+\.\d+\.[a-zA-Z0-9\{\}\(\)\[\]\_\,]+$'
INFINITY = -1

def st_label_components(label):
    """ returns a list of integers representing the components of the label """
    if re.match(MU_LABEL_RE,label):
        return [0,1,0,int(label.split('.')[2])]
    else:
        from sage.databases.cremona import class_to_int
        a = re.match(ST_LABEL_SPLIT_RE,label)
        return [int(a[1]),int(a[2]),class_to_int(a[3].lower()),int(a[4]),int(a[5]),class_to_int(a[6])]

# use a list and a dictionary (for pretty printing) so that we can control the display order (switch to ordered dictionary once everyone is on python 3.1)
st0_list = (
    'SO(1)', 'SO(2)', 'SO(3)', 'SO(4)', 'SO(5)', 'SO(6)',
    'U(1)', 'SU(2)',
    'U(1)_2', 'SU(2)_2', 'U(1)xU(1)', 'U(1)xSU(2)', 'SU(2)xSU(2)', 'USp(4)',
    'U(1)_3', 'SU(2)_3', 'U(1)xU(1)_2', 'SU(2)xU(1)_2', 'U(1)xSU(2)_2', 'SU(2)xSU(2)_2', 'U(1)^3',
    'U(1)^2xSU(2)', 'U(1)xSU(2)^2', 'SU(2)^3', 'U(1)xUSp(4)', 'SU(2)xUSp(4)', 'U(3)', 'USp(6)'
)
st0_dict = {
    'SO(1)': r"\mathrm{SO}(1)",
    'SO(2)': r"\mathrm{SO}(2)",
    'SO(3)': r"\mathrm{SO}(3)",
    'SO(4)': r"\mathrm{SO}(4)",
    'SO(5)': r"\mathrm{SO}(5)",
    'SO(6)': r"\mathrm{SO}(6)",
    'U(1)': r"\mathrm{U}(1)",
    'U(2)': r"\mathrm{U}(2)",
    'SU(2)': r"\mathrm{SU}(2)",
    'U(1)_2': r"\mathrm{U}(1)_2",
    'SU(2)_2': r"\mathrm{SU}(2)_2",
    'U(1)xU(1)': r"\mathrm{U}(1)\times\mathrm{U}(1)",
    'U(1)xSU(2)': r"\mathrm{U}(1)\times\mathrm{SU}(2)",
    'SU(2)xSU(2)': r"\mathrm{SU}(2)\times\mathrm{SU}(2)",
    'USp(4)': r"\mathrm{USp}(4)",
    'U(1)_3': r"\mathrm{U}(1)_3",
    'SU(2)_3': r"\\mathrm{SU}(2)_3",
    'U(1)xU(1)_2': r"\mathrm{U}(1)\times\mathrm{U}(1)_2",
    'U(1)xSU(2)_2': r"\mathrm{U}(1)\times\mathrm{SU}(2)_2",
    'SU(2)xU(1)_2': r"\mathrm{SU}(2)\times\mathrm{U}(1)_2",
    'SU(2)xSU(2)_2': r"\mathrm{SU}(2)\times\mathrm{SU}(2)_2",
    'U(1)^3': r"\mathrm{U}(1)^3",
    'U(1)^2xSU(2)': r"\mathrm{U}(1)^2\times\mathrm{SU}(2)",
    'U(1)xSU(2)^2': r"\mathrm{U}(1)\times\mathrm{SU}(2)^2",
    'SU(2)^3': r"\mathrm{SU}(2)^3",
    'U(3)': r"\mathrm{U}(3)",
    'U(1)xUSp(4)': r"\mathrm{U}(1)\times\mathrm{USp}(4)",
    'SU(2)xUSp(4)': r"\mathrm{SU}(2)\times\mathrm{USp}(4)",
    'USp(6)': r"\mathrm{USp}(6)",
}

st_latex_dict = {
    '1.2.A.1.1a': r"\mathrm{SU}(2)",
    '1.2.B.1.1a': r"\mathrm{U}(1)",
    '1.2.B.2.1a': r"N(\mathrm{U}(1))",
    '1.4.A.1.1a': r"\mathrm{USp}(4)",
    '1.4.B.1.1a': r"\mathrm{SU}(2)\times\mathrm{SU}(2)",
    '1.4.B.2.1a': r"N(\mathrm{SU}(2)\times\mathrm{SU}(2))",
    '1.4.C.1.1a': r"\mathrm{U}(1)\times\mathrm{SU}(2)",
    '1.4.C.2.1a': r"N(\mathrm{U}(1)\times\mathrm{SU}(2))",
    '1.4.D.1.1a': r"F",
    '1.4.D.2.1a': r"F_{ab}",
    '1.4.D.2.1b': r"F_a",
    '1.4.D.4.1a': r"F_{ac}",
    '1.4.D.4.2a': r"F_{a,b}",
    '1.4.E.1.1a': r"E_1",
    '1.4.E.2.1a': r"E_2",
    '1.4.E.2.1b': r"J(E_1)",
    '1.4.E.3.1a': r"E_3",
    '1.4.E.4.1a': r"E_4",
    '1.4.E.4.2a': r"J(E_2)",
    '1.4.E.6.1a': r"J(E_3)",
    '1.4.E.6.2a': r"E_6",
    '1.4.E.8.3a': r"J(E_4)",
    '1.4.E.12.4a': r"J(E_6)",
    '1.4.F.1.1a': r"C_1",
    '1.4.F.2.1a': r"J(C_1)",
    '1.4.F.2.1b': r"C_2",
    '1.4.F.2.1c': r"C_{2,1}",
    '1.4.F.3.1a': r"C_3",
    '1.4.F.4.1a': r"C_{4,1}",
    '1.4.F.4.1b': r"C_4",
    '1.4.F.4.2a': r"D_2",
    '1.4.F.4.2b': r"J(C_2)",
    '1.4.F.4.2c': r"D_{2,1}",
    '1.4.F.6.1a': r"D_3",
    '1.4.F.6.1b': r"D_{3,2}",
    '1.4.F.6.2a': r"J(C_3)",
    '1.4.F.6.2b': r"C_{6,1}",
    '1.4.F.6.2c': r"C_6",
    '1.4.F.8.2a': r"J(C_4)",
    '1.4.F.8.3a': r"D_{4,1}",
    '1.4.F.8.3b': r"D_4",
    '1.4.F.8.3c': r"D_{4,2}",
    '1.4.F.8.5a': r"J(D_2)",
    '1.4.F.12.3a': r"T",
    '1.4.F.12.4a': r"J(D_3)",
    '1.4.F.12.4b': r"D_{6,1}",
    '1.4.F.12.4c': r"D_6",
    '1.4.F.12.4d': r"D_{6,2}",
    '1.4.F.12.5a': r"J(C_6)",
    '1.4.F.16.11a': r"J(D_4)",
    '1.4.F.24.12a': r"O_1",
    '1.4.F.24.12b': r"O",
    '1.4.F.24.13a': r"J(T)",
    '1.4.F.24.14a': r"J(D_6)",
    '1.4.F.48.48a': r"J(O)",
}

# common aliases
st_aliases = {
    '1.2.3.c1': '1.2.A.1.1a',
    'SU(2)': '1.2.A.1.1a',
    'U(1)': '1.2.B.1.1a',
    '1.2.1.d1': '1.2.B.2.1a',
    'N(U(1))': '1.2.B.2.1a',
    'USp(4)': '1.4.A.1.1a',
    'G_{3,3}': '1.4.B.1.1a',
    'SU(2)xSU(2)': '1.4.B.1.1a',
    'SU(2)XSU(2)': '1.4.B.1.1a',
    'SU(2)^2': '1.4.B.1.1a',
    'N(G_{3,3})': '1.4.B.2.1a',
    'N(SU(2)xSU(2))': '1.4.B.2.1a',
    'N(SU(2)XSU(2))': '1.4.B.2.1a',
    'N(SU(2)^2)': '1.4.B.2.1a',
    'G_{1,3}': '1.4.C.1.1a',
    'U(1)xSU(2)': '1.4.C.1.1a',
    'SU(2)xU(1)': '1.4.C.1.1a',
    'N(G_{1,3})': '1.4.C.2.1a',
    'N(U(1)xSU(2))': '1.4.C.2.1a',
    'N(SU(2)xU(1))': '1.4.C.2.1a',
    'N(U(1)XSU(2))': '1.4.C.2.1a',
    'N(SU(2)XU(1))': '1.4.C.2.1a',
    'U(1)xU(1)': '1.4.D.1.1a',
    'U(1)^2': '1.4.D.1.1a',
    'F_{ac}': '1.4.D.4.1a',
    'F_{a,b}': '1.4.D.4.2a',
    'SU(2)_2': '1.4.E.1.1a',
    'E_1': '1.4.E.1.1a',
    'E_2': '1.4.E.2.1a',
    'E_3': '1.4.E.3.1a',
    'E_4': '1.4.E.4.1a',
    'E_6': '1.4.E.6.2a',
    'J(E_1)': '1.4.E.2.1b',
    'J(E_2)': '1.4.E.4.2a',
    'J(E_3)': '1.4.E.6.1a',
    'J(E_4)': '1.4.E.8.3a',
    'J(E_6)': '1.4.E.12.4a',
    'U(1)_2': '1.4.F.1.1a',
    'J(C_2)': '1.4.F.4.2b',
    'J(C_4)': '1.4.F.8.2a',
    'J(C_6)': '1.4.F.12.5a',
    'J(D_2)': '1.4.F.8.5a',
    'J(D_3)': '1.4.F.12.4a',
    'J(D_4)': '1.4.F.16.11a',
    'J(D_6)': '1.4.F.24.14a',
    'J(T)': '1.4.F.24.13a',
    'J(O)': '1.4.F.48.48a',
    'C_{2,1}': '1.4.F.2.1c',
    'C_{6,1}': '1.4.F.6.2b',
    'D_{2,1}': '1.4.F.4.2c',
    'D_{3,2}': '1.4.F.6.1b',
    'D_{4,1}': '1.4.F.8.3a',
    'D_{4,2}': '1.4.F.8.3c',
    'D_{6,1}': '1.4.F.12.4b',
    'D_{6,2}': '1.4.F.12.4d',
    'O_1': '1.4.F.24.12a',
    'USp(6)': '1.6.A.1.1a',
    'U(3)': '1.6.B.1.1a',
    'N(U(3))': '1.6.B.2.1a',
    'SU(2)xUSp(4)': '1.6.C.1.1a',
    'SU(2)XUSp(4)': '1.6.C.1.1a',
    'USp(4)xSU(2)': '1.6.C.1.1a',
    'USp(4)XSU(2)': '1.6.C.1.1a',
    'U(1)xUSp(4)': '1.6.D.1.1a',
    'U(1)XUSp(4)': '1.6.D.1.1a',
    'USp(4)xU(1)': '1.6.D.1.1a',
    'SU(2)xSU(2)xSU(2)': '1.6.E.1.1a',
    'SU(2)XSU(2)XSU(2)': '1.6.E.1.1a',
    'SU(2)^3': '1.6.E.1.1a',
    'U(1)xSU(2)xSU(2)': '1.6.F.1.1a',
    'U(1)XSU(2)XSU(2)': '1.6.F.1.1a',
    'SU(2)xU(1)xSU(2)': '1.6.F.1.1a',
    'SU(2)XU(1)XSU(2)': '1.6.F.1.1a',
    'SU(2)xSU(2)xU(1)': '1.6.F.1.1a',
    'SU(2)XSU(2)XU(1)': '1.6.F.1.1a',
    'U(1)xSU(2)^2': '1.6.F.1.1a',
    'U(1)XSU(2)^2': '1.6.F.1.1a',
    'SU(2)^2xU(1)': '1.6.F.1.1a',
    'SU(2)^2XU(1)': '1.6.F.1.1a',
    'U(1)xU(1)xSU(2)': '1.6.G.1.1a',
    'U(1)XU(1)XSU(2)': '1.6.G.1.1a',
    'U(1)xSU(2)xU(1)': '1.6.G.1.1a',
    'U(1)XSU(2)XU(1)': '1.6.G.1.1a',
    'SU(2)xU(1)xU(1)': '1.6.G.1.1a',
    'SU(2)XU(1)XU(1)': '1.6.G.1.1a',
    'U(1)^2xSU(2)': '1.6.G.1.1a',
    'U(1)^2XSU(2)': '1.6.G.1.1a',
    'SU(2)xU(1)^2': '1.6.G.1.1a',
    'SU(2)XU(1)^2': '1.6.G.1.1a',
    'U(1)xU(1)xU(1)': '1.6.H.1.1a',
    'U(1)XU(1)XU(1)': '1.6.H.1.1a',
    'U(1)^3': '1.6.H.1.1a',
    'SU(2)_2xSU(2)': '1.6.I.1.1a',
    'SU(2)_2XSU(2)': '1.6.I.1.1a',
    'SU(2)xSU(2)_2': '1.6.I.1.1a',
    'SU(2)XSU(2)_2': '1.6.I.1.1a',
    'SU(2)_2xU(1)': '1.6.J.1.1a',
    'SU(2)_2XU(1)': '1.6.J.1.1a',
    'U(1)xSU(2)_2': '1.6.J.1.1a',
    'U(1)XSU(2)_2': '1.6.J.1.1a',
    'U(1)_2xSU(2)': '1.6.K.1.1a',
    'U(1)_2XSU(2)': '1.6.K.1.1a',
    'SU(2)xU(1)_2': '1.6.K.1.1a',
    'SU(2)XU(1)_2': '1.6.K.1.1a',
    'U(1)xU(1)_2': '1.6.L.1.1a',
    'U(1)XU(1)_2': '1.6.L.1.1a',
    'U(1)_2xU(1)': '1.6.L.1.1a',
    'U(1)_2XU(1)': '1.6.L.1.1a',
    'SU(2)_3': '1.6.M.1.1a',
    'U(1)_3': '1.6.N.1.1a',
}

###############################################################################
# Utility functions
###############################################################################

def boolean_name(value):
    return 'yes' if value else 'no'


def comma_separated_list(lst):
    return ', '.join(lst)


def string_matrix(m):
    if len(m) == 0:
        return ''
    return '\\begin{bmatrix}' + '\\\\'.join('&'.join(map(str, m[i])) for i in range(len(m))) + '\\end{bmatrix}'

def convert_label(label):
    if label in st_aliases:
        return st_aliases[label]
    d2A = {'3':'A','1':'B'}
    d4A = {'10':'A','6':'B','4':'C','2':'D','3':'E','1':'F'}
    a = label.split('.')
    if a[0] == '0':
        return label
    if a[0] == '1':
        if a[1] == '2' and a[2] in d2A:
            a[2] = d2A[a[2]]
            return '.'.join(a)
        if a[1] == '4' and a[2] in d4A:
            a[2] = d4A[a[2]]
            return '.'.join(a)
        if a[2] in st_aliases:
            return st_aliases[a[2]]
    return label

def st_name(label):
    label = convert_label(label)
    if re.match(MU_LABEL_RE, label):
        name = r'\mu(%s)'%label.split('.')[2]
    elif re.match(NU1_MU_LABEL_RE, label):
        if label.split('.')[3] == 'd1':
            if label.split('.')[0] == '1':
                label = '1.2.B.2.1a'
            name = r'N(\mathrm{U}(1))'
        else:
            name = r'\mathrm{U}(1)[D_{%s}]'%label.split('.')[3][1:]
    elif re.match(SU2_MU_LABEL_RE, label):
        if label.split('.')[3] == 'c1':
            if label.split('.')[0] == '1':
                label = '1.2.A.1.1a'
            name = r'\mathrm{SU}(2)'
        else:
            name = r'\mathrm{SU}(2)[C_{%s}]'%label.split('.')[3][1:]
    else:
        data = db.gps_st.lookup(label,projection=["name","pretty"])
        name = (data['pretty'] if data['pretty'] else data['name']) if data else None
    return name, label

def st_ambient(weight, degree):
    return '\\mathrm{USp}(%d)'%degree if weight%2 == 1 else '\\mathrm{O}(%d)'%degree

def trace_moments(moments):
    for m in moments:
        if m[0] == 'a_1'or m[0] == 's_1':
            return m[1:10]
    return ''

def st0_pretty(st0_name):
    if re.fullmatch(r'SO\(1\)\_\d+', st0_name):
        return r'\\mathrm{SO}(1)_{%s}' % st0_name.split('_')[1]
    if re.fullmatch(r'U\(1\)\_\d+', st0_name):
        return r'\mathrm{U}(1)_{%s}' % st0_name.split('_')[1]
    if re.fullmatch(r'SU\(2\)\_\d+', st0_name):
        return r'\mathrm{SU}(2)_{%s}' % st0_name.split('_')[1]
    return st0_dict.get(st0_name,st0_name)

def sg_pretty(sg_label):
    data = db.gps_groups.lookup(sg_label)
    if data and data.get('tex_name'):
        return data['tex_name']
    return sg_label

def st_pretty(st_name):
    if re.fullmatch(r'mu\([1-9][0-9]*\)', st_name):
        return "\\" + st_name
    if st_name in st0_dict:
        return st0_dict[st_name]
    st_name = st_name.replace("x",r"\times")
    st_name = st_name.replace("USp(",r"\mathrm{USp}(")
    st_name = st_name.replace("SU(",r"\mathrm{SU}(")
    st_name = st_name.replace("U(",r"\mathrm{U}(")
    return st_name

def st_link(label,name=None):
    if not name:
        name, label = st_name(label)
    return '<a href=%s>%s</a>' % (url_for('st.by_label', label=label), "$%s$"%name if (name and name != label) else label)

def st_link_by_name(weight,degree,name):
    return '<a href="%s">$%s$</a>' % (url_for('st.by_label', label="%s.%s.%s"%(weight,degree,name)), st_pretty(name))

def st_anchor(label):
    if label in st_latex_dict:
        return r"$%s$"%st_latex_dict[label]
    elif re.match(MU_LABEL_RE, label):
        return r"$\mu(%s)$"%label.split('.')[2]
    elif re.match(NU1_MU_LABEL_RE, label):
        return r"$N(\mathrm{U}(1))$" if label.split('.')[3] == 'd1' else r"$\mathrm{U}(1)[D_{%s}]$"%label.split('.')[3][1:]
    elif re.match(SU2_MU_LABEL_RE, label):
        return r"$\mathrm{SU}(2)$" if label.split('.')[3] == 'c1' else r"$\mathrm{SU}(2)[C_{%s}]$"%label.split('.')[3][1:]
    else:
        return label

def st_lookup(label):
    """wrapper to gps_st table, handles dynamically generated groups not stored in the database"""
    if re.match(MU_LABEL_RE, label):
        return mu_data(ZZ(label.split('.')[2])), False
    elif re.match(NU1_MU_LABEL_RE, label):
        w = ZZ(label.split('.')[0])
        n = ZZ(label.split('.')[3][1:])
        return nu1_mu_data(w,n), False
    elif re.match(SU2_MU_LABEL_RE, label):
        w = ZZ(label.split('.')[0])
        n = ZZ(label.split('.')[3][1:])
        return su2_mu_data(w,n), False
    else:
        return db.gps_st.lookup(label), True

def st_knowl(label):
    try:
        data,_ = st_lookup(label)
        if not data:
            raise ValueError
    except ValueError:
        return "Unable to locate data for Sato-Tate group with label %s" % label
    label = data['label'] # label might have been converted
    row_wrap = lambda cap, val: "<tr><td>%s: </td><td>%s</td></tr>\n" % (cap, val)
    math_mode = lambda s: '$%s$'%s
    info = '<table>\n'
    info += row_wrap('Sato-Tate group <b>%s</b>'%label, math_mode(data['pretty']))
    info += "<tr><td></td><td></td></tr>\n"
    info += row_wrap(display_knowl('st_group.weight','Weight'), math_mode(data['weight']))
    info += row_wrap(display_knowl('st_group.degree','Degree'), math_mode(data['degree']))
    info += row_wrap(display_knowl('st_group.real_dimension',r'$\mathbb R$-dimension'), math_mode(data['real_dimension']))
    info += row_wrap(display_knowl('st_group.ambient','Ambient group'), math_mode(st_ambient(data['weight'], data['degree'])))
    info += row_wrap(display_knowl('st_group.identity_component','Identity component'), math_mode(st0_dict[data['identity_component']]))
    info += row_wrap(display_knowl('st_group.component_group','Component group'), abstract_group_display_knowl(data['component_group'], data['component_group'], pretty=True))
    info += row_wrap(display_knowl('st_group.rational','Rational'), 'yes' if data['rational'] else 'no')
    info += row_wrap(display_knowl('st_group.trace_zero_density','Trace zero density'), math_mode(data['trace_zero_density']))
    info += row_wrap(display_knowl('st_group.moments','Trace moments'), math_mode(data['moments'][0][1:]))
    if data.get('character_diagonal'):
        info += row_wrap(display_knowl('st_group.moment_matrix','Character diagonal'), math_mode(data['character_diagonal']))
    info += "</table>\n"
    info += '<br><div style="float:right;">Sato-Tate group %s home page</div>'%st_link(label,name=label)
    return info

def st_display_knowl(label):
    return display_knowl('st_group.data',title=st_anchor(label),kwargs={'label':label})

# We want to support aliases like S3.  The following table is an analogue of the list of aliases in lmfdb/galois_groups/transitive_group.py, but with GAP ids as output.
aliases = {'C1': '1.1',
           'C2': '2.1',
           'C3': '3.1',
           'C4': '4.1',
           'C2^2': '4.2',
           'C2XC2': '4.2',
           'S3': '6.1',
           'C6': '6.2',
           'C2XC4': '8.2',
           'D4': '8.3',
           'C2^3': '8.5',
           'C2XC2XC2': '8.5',
           'A4': '12.3',
           'D6': '12.4',
           'C2XC6': '12.5',
           'C2XD4': '16.11',
           'S4': '24.12',
           'A4XC2': '24.13',
           'C2^2XS3': '24.14',
           'C2XC2XS3': '24.14',
           'C2XS4': '48.48'}
cyclics = {'1.1': 1,
           '2.1': 2,
           '3.1': 3,
           '4.1': 4,
           '6.2': 6}
cyclicre = r'C(\d+)'

@search_parser(clean_info=True, default_field="component_group", default_qfield="component_group", default_name="Component group")
def parse_component_group(inp, query, qfield):
    codes = inp.upper()
    ans = []
    # some commas separate groups, and others are internal to group names
    # like PSL(2,7) and gap id [6,1]
    # after upper casing, we can replace commas we want to keep with "z"
    commaid = r'\[(\d+),(\d+)\]'
    labelre = r'(\d+)\.(\d+)'
    codes = re.sub(commaid, r'\1.\2', codes)
    codes = re.sub(r'\((\d+),(\d+)\)', r'(\1z\2)', codes)
    codelist = codes.split(",")
    codelist = [code.replace("z", ",") for code in codelist]
    for code in codelist:
        # Turn zs back into commas and sort direct products
        code = "X".join(sorted(code.replace("z", ",").split("X")))
        if code in aliases:
            code = aliases[code]
        elif re.match(cyclicre, code):
            # We leave other cyclic groups intact for use in checking irrational ST groups
            # These won't match anything in the database
            pass
        elif not re.match(labelre, code):
            raise ValueError("%s is not the component group of a Sato-Tate group in the database" % code)
        ans.append(code)
    if len(ans) == 1:
        query[qfield] = ans[0]
    else:
        query[qfield] = {"$in": ans}

@app.context_processor
def ctx_sato_tate_group_data():
    return {'sato_tate_group_data': st_knowl}

###############################################################################
# Learnmore display functions
###############################################################################

def learnmore_list():
    return [('Source and acknowledgments', url_for('.source_page')),
            ('Completeness of the data', url_for('.completeness_page')),
            ('Reliability of the data', url_for('.reliability_page')),
            ('Sato-Tate group labels', url_for('.labels_page'))]


def learnmore_list_remove(matchstring):
    """
    Return the learnmore list with the matchstring entry removed.
    """
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]

def get_bread(tail=[]):
    base = [('Sato-Tate groups', url_for('.index'))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

###############################################################################
# Pages
###############################################################################

@st_page.route('/')
def index():
    info = to_dict(request.args, search_array=STSearchArray(), stats=STStats())
    if request.args:
        return sato_tate_search(info)
    weight_list= [0, 1]
    degree_list = list(range(1, 7, 1))

    for key, val in [('weight_list', weight_list),
                     ('degree_list', degree_list),
                     ('st0_list', st0_list),
                     ('st0_dict', st0_dict)]:
        info[key] = val
    title = 'Sato-Tate groups'
    return render_template('st_browse.html', info=info, title=title, learnmore=learnmore_list(), bread=get_bread())

@st_page.route('/random')
@redirect_no_cache
def random():
    label = db.gps_st.random()
    return url_for('.by_label', label=label)

@st_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "st_group",
        db.gps_st,
        url_for_label=lambda label: url_for('.by_label', label=label),
        title=r"Some interesting Sato-Tate groups",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list()
    )

@st_page.route("/stats")
def statistics():
    title = "Sato-Tate groups: statistics"
    bread = get_bread("Statistics")
    return render_template("display_stats.html", info=STStats(), title=title, bread=bread, learnmore=learnmore_list())

@st_page.route('/<label>')
def by_label(label):
    clean_label = convert_label(clean_input(label))
    if clean_label != label:
        return redirect(url_for('.by_label', label=clean_label), 301)
    if label == '1.2.B.d1':
        return redirect(url_for('.by_label', label='1.2.B.2.1a'), 301)
    if label == '1.2.A.c1':
        return redirect(url_for('.by_label', label='1.2.A.1.1a'), 301)
    return search_by_label(label)

###############################################################################
# Searching
###############################################################################

def search_by_label(label):
    """ search for Sato-Tate group by label and render if found """

    if re.match(ST_LABEL_RE, label):
        return render_by_label(label)
    if re.match(ST_LABEL_SHORT_RE, label):
        return redirect(url_for('.by_label',label=label+'a'),301)
    if re.match(ST_OLD_LABEL_RE, label):
        return render_by_label(convert_label(label))
    if re.match(ST_OLD_LABEL_SHORT_RE, label):
        return redirect(url_for('.by_label',label=convert_label(label)+'a'),301)
    # check for labels of the form 0.1.n corresponding to mu(n)
    if re.match(MU_LABEL_RE, label):
        return render_by_label(label)
    # check for labels of the form w.2.B.dn corresponding to N(U(1)) x mu(n)
    if re.match(NU1_MU_LABEL_RE, label):
        return render_by_label(convert_label(label))
    # check for labels of the form w.2.A.cn corresponding to SU(2) x mu(n)
    if re.match(SU2_MU_LABEL_RE, label):
        return render_by_label(convert_label(label))
    # check for labels of the form 0.1.mu(n) (redirecto to 0.1.n)
    if re.match(MU_LABEL_NAME_RE, label):
        return redirect(url_for('.by_label',label='0.1.'+label.split('(')[1].split(')')[0]), 301)
    # check for general labels of the form w.d.name
    if re.match(ST_LABEL_NAME_RE,label):
        slabel = label.split('.')
        rlabel = db.gps_st.lucky({'weight':int(slabel[0]),'degree':int(slabel[1]),'name':slabel[2]}, "label")
        if not rlabel:
            flash_error("%s is not the label or name of a Sato-Tate group currently in the database", label)
            return redirect(url_for(".index"))
        return redirect(url_for('.by_label', label=rlabel), 301)
    # check for a straight up name
    rlabel = db.gps_st.lucky({'name':label}, "label")
    if not rlabel:
        flash_error("%s is not the label or name of a Sato-Tate group currently in the database", label)
        return redirect(url_for(".index"))
    return redirect(url_for('.by_label', label=rlabel), 301)

st_columns = SearchColumns([
    LinkCol("label", "st_group.label", "Label", lambda label: url_for('.by_label', label=label), default=True),
    MathCol("weight", "st_group.weight", "Wt", default=True, short_title="weight"),
    MathCol("degree", "st_group.degree", "Deg", default=True, short_title="degree"),
    MathCol("real_dimension", "st_group.real_dimension", r"$\mathrm{dim}_{\mathbb{R}}$", short_title="real dimension", default=True),
    ProcessedCol("identity_component", "st_group.identity_component", r"$\mathrm{G}^0$", st0_pretty, short_title="identity component", mathmode=True, default=True, align="center"),
    MathCol("pretty", "st_group.name", "Name", default=True),
    MathCol("components", "st_group.component_group", r"$\mathrm{G}/\mathrm{G}^0$", short_title="components", default=True),
    MathCol("trace_zero_density", "st_group.trace_zero_density", r"$\mathrm{Pr}[t\!=\!0]$", short_title="Pr[t=0]", default=True),
    MathCol("second_trace_moment", "st_group.second_trace_moment", r"$\mathrm{E}[a_1^2]$", short_title="E[a_1^2]", default=True, align="right"),
    MathCol("fourth_trace_moment", "st_group.fourth_trace_moment", r"$\mathrm{E}[a_1^4]$", short_title="E[a_1^4]", default=True, align="right"),
    ProcessedCol("sixth_trace_moment", "st_group.moments", r"$\mathrm{E}[a_1^6]$", lambda v: (r"$%s$"%v[0][7]) if v[0][0] == "a_1" and len(v[0]) > 7 else "", short_title="E[a_1^6]", align="right", orig="moments"),
    ProcessedCol("eigth_trace_moment", "st_group.moments", r"$\mathrm{E}[a_1^8]$", lambda v: (r"$%s$"%v[0][9]) if v[0][0] == "a_1" and len(v[0]) > 9 else "", short_title="E[a_1^8]", align="right", orig="moments"),
    ProcessedCol("tenth_trace_moment", "st_group.moments", r"$\mathrm{E}[a_1^{10}]$", lambda v: (r"$%s$"%v[0][11]) if v[0][0] == "a_1" and len(v[0]) > 11 else "", short_title="E[a_1^{10}]", align="right", orig="moments"),
    ProcessedCol("twelfth_trace_moment", "st_group.moments", r"$\mathrm{E}[a_1^{12}]$", lambda v: (r"$%s$"%v[0][11]) if v[0][0] == "a_1" and len(v[0]) > 13 else "", short_title="E[a_1^{12}]", align="right", orig="moments"),
    MathCol("first_a2_moment", "st_group.first_a2_moment", r"$\mathrm{E}[a_2]$", short_title="E[a_2]", default=True),
    ProcessedCol("second_a2_moment", "st_group.moments", r"$\mathrm{E}[a_2^2]$", lambda v: (r"$%s$"%v[1][3]) if len(v) > 1 and v[1][0] == "a_2" and len(v[1]) > 3 else "", short_title="E[a_2^2]", align="right", orig="moments"),
    ProcessedCol("third_a2_moment", "st_group.moments", r"$\mathrm{E}[a_2^3]$", lambda v: (r"$%s$"%v[1][4]) if len(v) > 1 and v[1][0] == "a_2" and len(v[1]) > 4 else "", short_title="E[a_2^3]", align="right", orig="moments"),
    ProcessedCol("fourth_a2_moment", "st_group.moments", r"$\mathrm{E}[a_2^4]$", lambda v: (r"$%s$"%v[1][5]) if len(v) > 1 and v[1][0] == "a_2" and len(v[1]) > 5 else "", short_title="E[a_2^4]", align="right", orig="moments"),
    ProcessedCol("fifth_a2_moment", "st_group.moments", r"$\mathrm{E}[a_2^5]$", lambda v: (r"$%s$"%v[1][6]) if len(v) > 1 and v[1][0] == "a_2" and len(v[1]) > 6 else "", short_title="E[a_2^5]", align="right", orig="moments"),
    ProcessedCol("sixth_a2_moment", "st_group.moments", r"$\mathrm{E}[a_2^6]$", lambda v: (r"$%s$"%v[1][7]) if len(v) > 1 and v[1][0] == "a_2" and len(v[1]) > 7 else "", short_title="E[a_2^6]", align="right", orig="moments"),
    ProcessedCol("second_a3_moment", "st_group.moments", r"$\mathrm{E}[a_3^2]$", lambda v: (r"$%s$"%v[2][3]) if len(v) > 2 and v[2][0] == "a_3" and len(v[2]) > 3 else "", short_title="E[a_3^2]", align="right", orig="moments"),
    ProcessedCol("fourth_a3_moment", "st_group.moments", r"$\mathrm{E}[a_3^4]$", lambda v: (r"$%s$"%v[2][5]) if len(v) > 2 and v[2][0] == "a_3" and len(v[2]) > 5 else "", short_title="E[a_3^4]", align="right", orig="moments"),
    ProcessedCol("sixth_a3_moment", "st_group.moments", r"$\mathrm{E}[a_3^6]$", lambda v: (r"$%s$"%v[2][7]) if len(v) > 2 and v[2][0] == "a_3" and len(v[2]) > 7 else "", short_title="E[a_3^6]", align="right", orig="moments"),
    CheckCol("maximal", "st_group.supgroups", "Maximal"),
    CheckCol("rational", "st_group.rational", "Rational"),
    MathCol("character_diagonal", "st_group.moment_matrix", r"Diagonal", align="left"),

])
st_columns.dummy_download = True

@search_wrap(
    table=db.gps_st,
    title="Sato-Tate group search results",
    err_title="Sato-Tate group search input error",
    shortcuts={"jump": lambda v: search_by_label(v['jump'])},
    columns=st_columns,
    bread=lambda: get_bread("Search results"),
    learnmore=learnmore_list,
    url_for_label=lambda label: url_for(".by_label", label=label),
)
def sato_tate_search(info, query):
    parse_ints(info, query, 'weight', 'weight')
    parse_ints(info, query, 'degree', 'degree')
    if info.get('include_irrational') != 'yes':
        query['rational'] = True
    if info.get('identity_component'):
        query['identity_component'] = info['identity_component']
    parse_bool(info, query, "maximal", "is maximal")
    parse_rational(info, query, "trace_zero_density", "trace zero density")
    parse_ints(info, query, "second_trace_moment")
    parse_ints(info, query, "fourth_trace_moment")
    parse_ints(info, query, "first_a2_moment")
    parse_ints(info, query, 'components', 'components')
    parse_component_group(info, query)

def parse_sort(info):
    sorts = info['search_array'].sorts
    for name, display, S in sorts:
        if name == info.get('sort_order', ''):
            sop = info.get('sort_dir', '')
            if sop == 'op':
                return [(col, -1) if isinstance(col, str) else (col[0], -col[1]) for col in S]
            return S

###############################################################################
# Rendering
###############################################################################

def mu_data(n):
    """ data for ST group mu(n); for n > 2 these groups are irrational and not stored in the database """
    assert n > 0
    n = ZZ(n)
    rec = {}
    rec['label'] = "0.1.%d"%n
    rec['label_components'] = [int(0),int(1),int(0),int(n)]
    rec['weight'] = 0
    rec['degree'] = 1
    rec['rational'] = bool(n <= 2)
    rec['name'] = 'mu(%d)'%n
    rec['pretty'] = r'\mu(%d)'%n
    rec['real_dimension'] = 0
    rec['components'] = int(n)
    rec['component_group'] = db.gps_special_names.lucky({'family':'C','parameters':{'n':n}},projection='label')
    if rec['component_group'] is None:
        rec['component_group'] = 'ab/%s'%n
    else:
        rec['component_group_number'] = int(rec['component_group'].split('.')[1])
    rec['st0_label'] = '0.1.A'
    rec['identity_component'] = 'SO(1)'
    rec['trace_zero_density']='0'
    rec['gens'] = [[[r"\zeta_{%d}"%n]]]
    rec['subgroups'] = ["0.1.%d"%(n/p) for p in n.prime_factors()]
    rec['subgroup_multiplicities'] = [1 for p in n.prime_factors()]
    # only list supgroups with the same ambient (i.e.if mu(n) lies in O(1) don't list supgroups that are not)
    if n == 1:
        rec['supgroups'] = ["0.1.2"]
        rec['maximal'] = False
    elif n == 2:
        rec['supgroups'] = []
        rec['maximal'] = True
    elif n > 2:
        if n <= 200000:
            rec['supgroups'] = ["0.1.%d"%(p*n) for p in [2,3,5]]
        rec['maximal'] = False
    rec['moments'] = [['a_1'] + [1 if m % n == 0 else 0 for m in range(13)]]
    rec['second_trace_moment'] = 1 if 2 % n == 0 else 0
    rec['fourth_trace_moment'] = 1 if 4 % n == 0 else 0
    rec['counts'] = [['a_1', [[t,1] for t in ([1] if n%2 else [1,-1])]]]
    rec['zvector'] = []
    return rec

def mu_portrait(n):
    """ returns an encoded scatter plot of the nth roots of unity in the complex plane """
    if n <= 120:
        plot =  list_plot([(cos(2*pi*m/n),sin(2*pi*m/n)) for m in range(n)],pointsize=30+60/n,axes=False)
    else:
        plot = circle((0,0),1,thickness=3)
    plot.xmin(-1)
    plot.xmax(1)
    plot.ymin(-1)
    plot.ymax(1)
    plot.set_aspect_ratio(4.0 / 3.0)
    plot.axes(False)
    return encode_plot(plot)

def su2_mu_data(w, n):
    """ data for ST group SU(2) x mu(n) (of any wt > 0); these groups are not stored in the database """
    assert w > 0 and n > 0
    if w == 1 and n == 1:
        return db.gps_st.lookup('1.2.A.1.1a')
    rec = {}
    rec['label'] = "%d.2.3.c%d"%(w,n)
    rec['weight'] = w
    rec['degree'] = 2
    rec['rational'] = bool(n <= 2)
    rec['name'] = 'SU(2)[C%d]'%n if n > 1 else 'SU(2)'
    rec['pretty'] = r'\mathrm{SU}(2)[C_{%d}]'%n if n > 1 else r'\mathrm{SU}(2)'
    rec['real_dimension'] = 3
    rec['components'] = int(n)
    rec['component_group'] = db.gps_special_names.lucky({'family':'C','parameters':{'n':n}},projection='label')
    if rec['component_group'] is None:
        rec['component_group'] = 'ab/%s'%n
    else:
        rec['component_group_number'] = int(rec['component_group'].split('.')[1])
    rec['st0_label'] = '%d.2.A'%w
    rec['identity_component'] = 'SU(2)'
    rec['trace_zero_density']='0'
    rec['gens'] = [[['1','0'],['0',r'\zeta_{%d}'%n]]]
    rec['subgroups'] = ["%d.2.A.c%d"%(w,n/p) for p in n.prime_factors()]
    rec['subgroup_multiplicities'] = [1 for p in n.prime_factors()]
    if n == 1:
        rec['supgroups'] = []
        rec['maximal'] = True
    else:
        rec['supgroups'] = ["%d.2.A.c%d"%(w,p*n) for p in [2,3,5]]
        rec['maximal'] = False
    su2_moments = [1, 0, 1, 0, 2, 0, 5, 0, 14, 0, 42, 0, 132]
    rec['moments'] = [['a_1'] + [su2_moments[m] if m%n == 0 else 0 for m in range(13)]]
    rec['second_trace_moment'] = 1 if 2 % n == 0 else 0
    rec['fourth_trace_moment'] = 2 if 4 % n == 0 else 0
    rec['counts'] = []
    rec['zvector'] = []
    return rec

def su2_mu_portrait(n):
    """ returns an encoded line plot of SU(2) x mu(n) in the complex plane """
    if n == 1:
        return db.gps_st.lookup('1.2.A.1.1a').get('trace_histogram')
    if n <= 120:
        plot =  sum([line2d([(-2*cos(2*pi*m/n),-2*sin(2*pi*m/n)),(2*cos(2*pi*m/n),2*sin(2*pi*m/n))],thickness=3) for m in range(n)])
    else:
        plot = circle((0, 0), 2, fill=True)
    plot.xmin(-2)
    plot.xmax(2)
    plot.ymin(-2)
    plot.ymax(2)
    plot.set_aspect_ratio(4.0 / 3.0)
    plot.axes(False)
    return encode_plot(plot)

def nu1_mu_data(w,n):
    """ data for ST group N(U(1)) x mu(n) (of any wt > 0); these groups are not stored in the database """
    assert w > 0 and n > 0
    if w == 1 and n == 1:
        return db.gps_st.lookup('1.2.B.2.1a')
    rec = {}
    rec['label'] = "%d.2.1.d%d"%(w,n)
    rec['weight'] = w
    rec['degree'] = 2
    rec['rational'] = bool(n <= 2)
    rec['name'] = 'U(1)[C%d]'%n if n > 1 else 'N(U(1))'
    rec['pretty'] = r'\mathrm{U}(1)[D_{%d}]'%n if n > 1 else r'N(\mathrm{U}(1))'
    rec['real_dimension'] = 1
    rec['components'] = int(2*n)
    rec['component_group'] = '4.2' if n == 2 else db.gps_special_names.lucky({'family':'D','parameters':{'n':n}},projection='label')
    if rec['component_group'] is None:
        return None
    rec['component_group_number'] = int(rec['component_group'].split('.')[1])
    rec['st0_label'] = '%d.2.B'%w
    rec['identity_component'] = 'U(1)'
    rec['trace_zero_density']='1/2'
    rec['gens'] = [[['0','1'],['-1','0']],[['1','0'],['0',r'\zeta_{%d}'%n]]]
    rec['subgroups'] = ["%d.2.B.D%d"%(w,n/p) for p in n.prime_factors()]
    rec['subgroup_multiplicities'] = [1 for p in n.prime_factors()]
    if n == 1:
        rec['supgroups'] = []
        rec['maximal'] = True
    else:
        rec['supgroups'] = ["%d.2.B.D%d"%(w,p*n) for p in [2,3,5]]
        rec['maximal'] = False
    nu1_moments = [1, 0, 1, 0, 3, 0, 10, 0, 35, 0, 126, 0, 462]
    rec['moments'] = [['a_1'] + [nu1_moments[m] if m%n == 0 else 0 for m in range(13)]]
    rec['second_trace_moment'] = 1 if 2 % n == 0 else 0
    rec['fourth_trace_moment'] = 3 if 4 % n == 0 else 0
    rec['counts'] = [['a_1', [[0,n]]]]
    rec['zvector'] = [int(n)]
    return rec

def nu1_mu_portrait(n):
    """ returns an encoded scatter plot of the nth roots of unity in the complex plane """
    if n == 1:
        return db.gps_st.lookup('1.2.B.2.1a').get('trace_histogram')
    if n <= 120:
        plot =  sum([line2d([(-2*cos(2*pi*m/n),-2*sin(2*pi*m/n)),(2*cos(2*pi*m/n),2*sin(2*pi*m/n))],thickness=3) for m in range(n)]) + circle((0,0),0.1,rgbcolor=(0,0,0),fill=True)
    else:
        plot = circle((0, 0), 2, fill=True)
    plot.xmin(-2)
    plot.xmax(2)
    plot.ymin(-2)
    plot.ymax(2)
    plot.set_aspect_ratio(4.0 / 3.0)
    plot.axes(False)
    return encode_plot(plot)

def st_portrait(label):
    if re.match(MU_LABEL_RE, label):
        return mu_portrait(ZZ(label.split('.')[2]))
    elif re.match(NU1_MU_LABEL_RE, label):
        return nu1_mu_portrait(ZZ(label.split('.')[3][1:]))
    elif re.match(SU2_MU_LABEL_RE, label):
        return su2_mu_portrait(ZZ(label.split('.')[3][1:]))
    return None

def render_by_label(label):
    """ render html page for Sato-Tate group specified by label """
    data, in_database = st_lookup(label)
    info = {}
    if data is None:
        flash_error ("%s is not the label of a Sato-Tate group currently in the database.", label)
        return redirect(url_for(".index"))
    for attr in ['label','weight','degree','name','pretty','real_dimension','components']:
        info[attr] = data[attr]
    info['ambient'] = st_ambient(info['weight'],info['degree'])
    info['connected']=boolean_name(info['components'] == 1)
    info['rational']=boolean_name(info.get('rational',True))
    st0 = db.gps_st0.lucky({'name':data['identity_component']})
    if not st0:
        flash_error ("%s is not the label of a Sato-Tate identity component currently in the database.", data['identity_component'])
        return redirect(url_for(".index"))
    info['symplectic_form'] = st0.get('symplectic_form')
    info['hodge_circle'] = st0.get('hodge_circle')
    info['st0_name']=st0['name']
    info['identity_component']=st0['pretty']
    info['st0_description']=st0['description']
    if data['component_group'][:2] == "ab":
        info['component_group'] = r"C_{%s}"%info['components']
        info['cyclic']=boolean_name(True)
        info['abelian']=boolean_name(True)
        info['solvable']=boolean_name(True)
    else:
        G = db.gps_groups.lookup(data['component_group'])
        if not G:
            flash_error ("%s is not the label of a Sato-Tate component group currently in the database.", data['component_group'])
            return redirect(url_for(".index"))
        info['component_group']=G['tex_name']
        info['cyclic']=boolean_name(G['cyclic'])
        info['abelian']=boolean_name(G['abelian'])
        info['solvable']=boolean_name(G['solvable'])
    if data.get('gens'):
        info['gens'] = comma_separated_list([string_matrix(m) for m in data['gens']]) if type(data['gens']) == list else data['gens']
        info['numgens'] = len(info['gens'])
    else:
        info['numgens'] = 0
    if data.get('subgroups'):
        if data.get('subgroup_multiplicities') and len(data["subgroup_multiplicities"]) == len(data['subgroups']):
            mults = ["${}^{\\times %d}$"%m if m >1 else "" for m in data['subgroup_multiplicities']]
        else:
            mults = ["" for s in data['subgroups']]
        info['subgroups'] = comma_separated_list([st_link(data['subgroups'][i]) + mults[i] for i in range(len(mults))])
    if data.get('supgroups'):
        if data.get('supgroup_multiplicities') and len(data["supgroup_multiplicities"]) == len(data['supgroups']):
            mults = ["${}^{\\times %d}$"%m if m >1 else "" for m in data['supgroup_multiplicities']]
        else:
            mults = ["" for s in data['supgroups']]
        info['supgroups'] = comma_separated_list([st_link(data['supgroups'][i]) + mults[i] for i in range(len(mults))])
    if not data['rational']:
        if info.get("supgroups"):
            info['supgroups'] += ", $\\cdots$"
        else:
            info['supgroups'] = "$\\cdots$"
    if data.get('moments'):
        info['moments'] = [['x'] + [ '\\mathrm{E}[x^{%d}]'%m for m in range(len(data['moments'][0])-1)]]
        info['moments'] += data['moments']
    if data.get('simplex'):
        if data['degree'] == 4:
            s = data['simplex']
            if len(s)>= 27:
                info['simplex'] = [s[0:2],s[2:5],s[5:9],s[9:14],s[14:20],s[20:27]]
            elif len(s) >= 20:
                info['simplex'] = [s[0:2],s[2:5],s[5:9],s[9:14],s[14:20]]
            elif len(s) >= 14:
                info['simplex'] = [s[0:2],s[2:5],s[5:9],s[9:14],s[14:20]]
            info['simplex_header'] = [r"\left(\mathrm{E}\left[a_1^{e_1}a_2^{e_2}\right]:\sum ie_i=%d\right)\colon"%(2*d+2) for d in range(len(info['simplex']))]
        elif data['degree'] == 6:
            s = data['simplex']
            if len(s) >= 56:
                info['simplex'] = [s[0:2],s[2:6],s[6:13],s[13:23],s[23:37],s[37:51],s[51:56]]
            elif len(s) >= 37:
                info['simplex'] = [s[0:2],s[2:6],s[6:13],s[13:23],s[23:37]]
            elif len(s) >= 23:
                info['simplex'] = [s[0:2],s[2:6],s[6:13],s[13:23]]
            info['simplex_header'] = [r"\left(\mathrm{E}\left[a_1^{e_1}a_2^{e_2}a_3^{e_3}\right]:\sum ie_i=%d\right)\colon"%(2*d+2) for d in range(len(info['simplex']))]
            if len(s) >= 56:
                info['simplex_header'][-1] = ""
    if data.get('character_matrix'):
        A = data['character_matrix']
        info["character_matrix"] = r"\mathrm{E}\left[\chi_i\chi_j\right] = " + string_matrix(A)
    if data.get("character_diagonal"):
        d = data["character_diagonal"]
        info["character_diagonal"] = r"\ \ \ \mathrm{E}\left[\chi_i^2\right] = " + string_matrix([[d[i] for i in range(len(d))]])
    n = QQ(data['components'])
    if data.get('zvector'):
        z = data['zvector']
        if data['degree'] == 4:
            if sum(z) == 0:
                s = r"<p>$\mathrm{Pr}[a_i=n]=0$ for $i=1,2$ and $n\in\mathbb{Z}$.</p>"
            else:
                s = "<table>"
                s += '<tr><th></th><th>$-$</th><th>$a_2\\in\\mathbb{Z}$</th><th>' + '</th><th>'.join(["$a_2=%s$" % (i) for i in range(-2,3)]) + '</th></tr>'
                s += '<tr><th>$-$</th><td align="center">$1$</td><td align="center">$%s$</td><td align="center">' % (sum(z[1:6])/n)
                s += '</td><td align="center">'.join(["$%s$" % (z[1+i]/n) for i in range(5)]) + '</td></tr>'
                s += '<tr><th>$a_1=0$</td><td align="center">$%s$</td><td align="center">$%s$</td><td align="center">' % (z[0]/n,sum(z[6:11])/n)
                s += '</td><td align="center">'.join(["$%s$" % (z[6+i]/n) for i in range(5)]) + "</td></tr>"
                s += "</table>"
            info['probabilities'] = s
        elif data['degree'] == 6:
            if sum(z) == 0:
                s = r"<p>$\mathrm{Pr}[a_i=n]=0$ for $i=1,2,3$ and $n\in\mathbb{Z}$.</p>"
            else:
                s = "<table>"
                s += '<tr><th></th><th>$-$</th><th>$a_2\\in\\mathbb{Z}$</th><th>' + '</th><th>'.join(["$a_2=%s$" % (i) for i in range(-1,4)]) + '</th></tr>'
                s += '<tr><th>$-$</th><td align="center">$1$</td><td align="center">$%s$</td><td align="center">' % (sum(z[1:6])/n)
                s += '</td><td align="center">'.join(["$%s$" % (z[1+i]/n) for i in range(5)]) + '</td></tr>'
                s += '<tr><th>$a_1=0$</td><td align="center">$%s$</td><td align="center">$%s$</td><td align="center">' % (z[0]/n,sum(z[7:12])/n)
                s += '</td><td align="center">'.join(["$%s$" % (z[7+i]/n) for i in range(5)]) + '</td></tr>'
                s += '<tr><th>$a_3=0$</td><td align="center">$%s$</td><td align="center">$%s$</td><td align="center">' % (z[6]/n,sum(z[13:18])/n)
                s += '</td><td align="center">'.join(["$%s$" % (z[13+i]/n) for i in range(5)]) + '</td></tr>'
                s += '<tr><th>$a_1=a_3=0$</td><td align="center">$%s$</td><td align="center">$%s$</td><td align="center">' % (z[12]/n,sum(z[18:23])/n)
                s += '</td><td align="center">'.join(["$%s$" % (z[18+i]/n) for i in range(5)]) + '</td></tr>'
                s += "</table>"
            info['probabilities'] = s
    elif data.get('counts'):
        c=data['counts']
        T = [['$\\mathrm{Pr}[%s=%s]=%s$'%(c[i][0],c[i][1][j][0],c[i][1][j][1]/n) for j in range(len(c[i][1]))] for i in range(len(c))]
        info['probabilities'] = "<table><tr>" + "<tr></tr>".join(["<td>" + "<td></td".join(r) + "</td>" for r in T]) + "</tr></table>"
    return render_st_group(info, portrait=data.get('trace_histogram'), in_database=in_database)

def render_st_group(info, portrait=None, in_database=False):
    """ render html page for Sato-Tate group described by info """
    prop = [('Label', '%s'%info['label'])]
    if portrait is None:
        portrait = st_portrait(info['label'])
    if portrait:
        prop += [(None, '&nbsp;&nbsp;<img src="%s" width="216" height="126"/>' % portrait)]
    prop += [
        ('Name', r'\(%s\)'%info['pretty']),
        ('Weight', prop_int_pretty(info['weight'])),
        ('Degree', prop_int_pretty(info['degree'])),
        ('Real dimension', prop_int_pretty(info['real_dimension'])),
        ('Components', prop_int_pretty(info['components'])),
        ('Contained in',r'\(%s\)'%info['ambient']),
        ('Identity component', r'\(%s\)'%info['identity_component']),
        ('Component group', r'\(%s\)'%info['component_group']),
    ]
    downloads = [("Underlying data", url_for(".st_data", label=info['label']))] if in_database else []
    bread = get_bread([
        ('Weight %d'% info['weight'], url_for('.index')+'?weight='+str(info['weight'])),
        ('Degree %d'% info['degree'], url_for('.index')+'?weight='+str(info['weight'])+'&degree='+str(info['degree'])),
        (info['name'], '')
    ])
    title = r'Sato-Tate group \(' + info['pretty'] + r'\) of weight %d'% info['weight'] + ' and degree %d'% info['degree']
    return render_template('st_display.html',
                           properties=prop,
                           downloads=downloads,
                           info=info,
                           bread=bread,
                           learnmore=learnmore_list(),
                           title=title,
                           KNOWL_ID='st_group.%s'%(info['label']))

@st_page.route("/data/<label>")
def st_data(label):
    data = db.gps_st.lookup(label)
    if data is None:
        return abort(404, f"Invalid label {label}")
    bread = get_bread([(label, url_for('.by_label', label=label)), ("Data", "")])
    title = f"Sato-Tate group data - {label}"
    return datapage([label, data["identity_component"], data["component_group"]], ["gps_st", "gps_st0", "gps_groups"], bread=bread, title=title, label_cols=["label", "name", "label"])

@st_page.route('/Source')
def source_page():
    t = 'Source and acknowledgments for Sato-Tate group data'
    bread = get_bread("Source")
    return render_template('multi.html', kids=['rcs.source.st_group',
                                               'rcs.ack.st_group',
                                               'rcs.cite.st_group'],
                           title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@st_page.route('/Completeness')
def completeness_page():
    t = 'Completeness of Sato-Tate group data'
    bread = get_bread("Completeness")
    return render_template('single.html', kid='rcs.cande.st_group',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@st_page.route('/Reliability')
def reliability_page():
    t = 'Reliability of Sato-Tate group data'
    bread = get_bread("Reliability")
    return render_template('single.html', kid='rcs.rigor.st_group',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@st_page.route('/Labels')
def labels_page():
    t = 'Labels for Sato-Tate groups'
    bread = get_bread("Labels")
    return render_template('single.html', kid='st_group.label',
                           title=t, bread=bread, learnmore=learnmore_list_remove('labels'))

class STSearchArray(SearchArray):
    noun = "group"
    plural_noun = "groups"
    sorts = [("", "weight", ["weight", "degree", "st0_label", "components", "component_group_number", "label"]),
             ("degree", "degree", ["degree", "weight", "st0_label", "components", "component_group_number", "label"]),
             ("real_dimension", "real dimension", ["real_dimension", "weight", "degree", "st0_label", "components", "component_group_number", "label"]),
             #("st0", "identity component", ["st0_label", "weight", "degree", "components", "component_group_number", "label"]),
             ("components", "component group", ["components", "component_group_number", "st0_label", "weight", "degree", "label"]),
             ("trace_zero_density", "trace zero density", ["trace_zero_density", "weight", "degree", "st0_label", "components", "component_group_number", "label"]),
             ("character_diagonal", "character diagonal", ["character_diagonal", "weight", "degree", "st0_label", "components", "component_group_number", "label"])]
    jump_example = "1.4.USp(4)"
    jump_egspan = "e.g. 0.1.3 or 0.1.mu(3), or 1.2.B.2.1a or N(U(1)), or 1.4.A.1.1a or 1.4.USp(4)"
    jump_knowl = "st_group.search_input"
    jump_prompt = "Label or name"
    null_column_explanations = { # No need to display warnings for these
        'trace_histogram': False,
        'first_a2_moment': False,
        'simplex': False,
        'character_matrix': False,
        'old_label': False,
        'character_diagonal': False,
        'supgroup_multiplicities': False,
        'component_group_number': False,
    }
    def __init__(self):
        weight = TextBox(
            name="weight",
            label="Weight",
            knowl="st_group.weight",
            example="1",
            example_span="1 or 0-3")
        degree = TextBox(
            name="degree",
            label="Degree",
            knowl="st_group.degree",
            example="4",
            example_span="4 or 1-6")
        include_irrational = SelectBox(
            name="include_irrational",
            label="Include irrational",
            knowl="st_group.rational",
            example_col=True,
            options=[("", "no"),
                     ("yes", "yes")])
        identity_component = SelectBox(
            name="identity_component",
            label="Identity component",
            short_label=r"$\mathrm{ST}^0$",
            knowl="st_group.identity_component",
            example_span="U(1) or USp(4)",
            options=[("", "")] + [(r, r) for r in st0_list])
        components = TextBox(
            name="components",
            label="Components",
            knowl="st_group.components",
            example="1",
            example_span="1 (connected) or 4-12")
        trace_zero_density = TextBox(
            name="trace_zero_density",
            label="Trace zero density",
            knowl="st_group.trace_zero_density",
            short_label=r"$\mathrm{Pr}[a_1=0]$",
            example="1/2",
            example_span="0, 1/2, or 3/8")
        second_trace_moment = TextBox(
            name="second_trace_moment",
            label="Second trace moment",
            knowl="st_group.second_trace_moment",
            example="8")
        fourth_trace_moment = TextBox(
            name="fourth_trace_moment",
            label="Fourth trace moment",
            knowl="st_group.fourth_trace_moment",
            example="96")
        first_a2_moment = TextBox(
            name="first_a2_moment",
            label="First $a_2$ moment",
            knowl="st_group.first_a2_moment",
            example="4")
        maximal = YesNoBox(
            name="maximal",
            label="Maximal",
            knowl="st_group.supgroups",
            example_col=True)
        component_group = TextBox(
            name="component_group",
            label="Component group",
            knowl="st_group.component_group",
            example="[48,48]",
            example_span="list of %s, e.g. [8,3], or %s, e.g. S4." % (display_knowl("group.small_group_label", "GAP ids"), display_knowl("nf.galois_group.name", "group labels")))
        count = CountBox()

        self.browse_array = [
            [weight, trace_zero_density],
            [degree, second_trace_moment],
            [include_irrational, fourth_trace_moment],
            [identity_component, first_a2_moment],
            [maximal, components],
            [count, component_group]]

        self.refine_array = [[weight, degree, include_irrational, identity_component, maximal], [components, component_group, trace_zero_density, second_trace_moment, fourth_trace_moment], [first_a2_moment]]

@cached_function
def compcache():
    return abstract_group_namecache(db.gps_st.distinct("component_group"))
gapidre = re.compile(r"(\d+)\.(\d+)")
def compdata(comp):
    return [int(x) for x in gapidre.findall(comp)[0]]
def compformatter(comp):
    n, k = compdata(comp)
    return abstract_group_display_knowl(f"{n}.{k}", cache=compcache())
def compunformatter(comp):
    n, k = compdata(comp)
    return "%d.%d" % (n, k)
def idformatter(grp):
    return "$%s$" % (r"\operatorname{" + grp.replace("x", r"\times\operatorname{").replace("(", "}("))
def idunformatter(grp):
    return grp.replace("$", "").replace(r"\operatorname", "").replace(r"\times", "x").replace("{", "").replace("}", "")

class STStats(StatsDisplay):
    table = db.gps_st
    baseurl_func = ".index"

    stat_list = [
        {"cols": ["component_group", "identity_component"],
         "constraint": {"rational": True},
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["identity_component"],
         "constraint": {"maximal": True, "rational": True},
         "top_title": [("maximal subgroups", "st_group.supgroups"),
                       ("per", None),
                       ("identity component", "st_group.identity_component")],
        },
        {"cols": ["trace_zero_density", "identity_component"],
         "constraint": {"rational": True},
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["second_trace_moment", "identity_component"],
         "constraint": {"rational": True},
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["fourth_trace_moment", "identity_component"],
         "constraint": {"rational": True},
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["first_a2_moment", "identity_component"],
         "constraint": {"rational": True},
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
    ]

    formatters = {"component_group": compformatter,
                  "identity_component": idformatter}
    sort_keys = {"component_group": compdata,
                 "trace_zero_density": QQ}
    query_formatters = {"component_group": (lambda comp: "component_group=%s" % compunformatter(comp)),
                        "identity_component": (lambda grp: "identity_component=%s" % (idunformatter(grp)))}
    top_titles = {"trace_zero_density": "trace zero densities",
                  "first_a2_moment": "first $a_2$ moment"}
    knowls = {"identity_component": "st_group.identity_component",
              "component_group": "st_group.component_group",
              "trace_zero_density": "st_group.trace_zero_density",
              "second_trace_moment": "st_group.moments",
              "fourth_trace_moment": "st_group.moments",
              "first_a2_moment": "st_group.moments"}

    def __init__(self):
        self.ngroups = db.gps_st.count()

    @property
    def summary(self):
        return r"The database currently contains %s %s.  The statistics below omit the infinite family $\mu(n)$ with trivial %s since they are generated dynamically in search results." % (
            self.ngroups,
            display_knowl('st_group.definition', 'Sato-Tate groups'),
            display_knowl('st_group.identity_component', 'identity component'))

    @property
    def short_summary(self):
        return r'The database currently contains all %s %s of %s 1 and %s up to 6, as well as all Sato-Tate groups of weight 0 and degree 1 with %s of order at most $10^{20}$.  Here are some <a href="%s">further statistics</a>.' % (
            display_knowl('st_group.rational', 'rational'),
            display_knowl('st_group.definition', 'Sato-Tate groups'),
            display_knowl('st_group.weight', 'weight'),
            display_knowl('st_group.degree', 'degree'),
            display_knowl('st_group.component_group', 'component group'),
            url_for('.statistics'))
