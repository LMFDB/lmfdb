import re
import time
import ast
import StringIO
from pymongo import ASCENDING, DESCENDING
import lmfdb.base
from lmfdb.base import app
from lmfdb.utils import to_dict, make_logger
from lmfdb.abvar.fq import abvarfq_page
from lmfdb.search_parsing import parse_ints, parse_list_start, parse_count, parse_start, parse_range, parse_nf_string
from lmfdb.abvar.fq.search_parsing import parse_newton_polygon, parse_abvar_decomp
from lmfdb.abvar.fq.isog_class import validate_label, AbvarFq_isoclass
from lmfdb.abvar.fq.stats import AbvarFqStats
from flask import flash, render_template, url_for, request, redirect, make_response, send_file
from markupsafe import Markup
from sage.misc.cachefunc import cached_function
from sage.rings.all import PolynomialRing, ZZ
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import extract_limits_as_tuple

#########################
#   Database connection
#########################

@cached_function
def db():
    return lmfdb.base.getDBConnection().abvar.fq_isog
        
def download_stuff(query):
    s = 'data = [ \\\n'
    res = db().find(ast.literal_eval(query))
    print 'queried!'
    for f in res:
        print A_counts_to_sage(f)
        num = A_counts_to_sage(f)
        s += str(num) + ',\\\n'
    s = s[:-3]
    s += ']\n'
    file = open('data_download.sage','w')
    print 'file created'
    file.write(s)
    print 'written'
    
    
def g_to_sage(f):
    pass

def A_counts_to_sage(f):
    return f['A_counts'][0]
