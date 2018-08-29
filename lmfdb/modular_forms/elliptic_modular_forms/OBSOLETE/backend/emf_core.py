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
"""
Core functions for generating the necessary data corresponding to GL(2):
 - spaces of cusp forms
 - indivdual cuspforms

By convention a 'core function' starting with get_  returns a string.

AUTHOR: Fredrik Stroemberg


"""

from sage.all import Gamma0, Gamma1, latex
import re

####
#### Core functions for spaces of cuspforms
####

def len_as_printed(s, format='latex'):
    r"""
    Returns the length of s, as it will appear after being math_jax'ed
    """
    lenq = 1
    lendig = 1
    lenpm = 1.5
    lenpar = 0.5
    lenexp = 0.75
    lensub = 0.75
    ## remove all html first since it is not displayed
    ss = re.sub("<[^>]*>", "", s)
    # logger.debug("ss=%s" % ss)
    ss = re.sub(" ", "", ss)    # remove white-space
    ss = re.sub("\*", "", ss)    # remove *
    num_exp = s.count("^")    # count number of exponents
    # exps = re.findall("\^{?(\d*)", s)  # a list of all exponents
    # sexps = "".join(exps)
    num_subs = s.count("_")    # count number of exponents
    # subs = re.findall("_{?(\d*)", s)  # a list of all  subscripts
    # ssubs = "".join(subs)
    ss = re.sub("\^{?(\d*)}?", "", ss)  # remove exponenents
    # logger.debug("".join([ss,ssubs,sexps]))
    tot_len = (ss.count(")") + ss.count("(")) * lenpar
    tot_len += ss.count("q") * lenq
    tot_len += len(re.findall("\d", s)) * lendig
    tot_len += len(re.findall("\w", s)) * lenq
    tot_len += (s.count("+") + s.count("-")) * lenpm
    tot_len += num_subs * lensub
    tot_len += num_exp * lenexp
    #
    # tot_len = len(ss)+ceil((len(ssubs)+len(sexps))*0.67)
    return tot_len


def get_geometric_data_Gamma0N(N):
    res = dict()
    G = Gamma0(N)
    res['index'] = G.index()
    res['genus'] = G.genus()
    res['cusps'] = G.cusps()
    res['nu2'] = G.nu2()
    res['nu3'] = G.nu3()
    return res


def get_geometric_data(N, group=0):
    res = dict()
    if group == 0:
        G = Gamma0(N)
    elif group == 1:
        G = Gamma1(N)
    else:
        return None
    res['index'] = G.index()
    res['genus'] = G.genus()
    res['cusps'] = G.cusps()
    res['nu2'] = G.nu2()
    res['nu3'] = G.nu3()
    return res


def print_geometric_data_Gamma0N(N):
    r""" Print data about Gamma0(N).
    """
    G = Gamma0(N)
    s = ""
    s = "<table>"
    s += "<tr><td>index:</td><td>%s</td></tr>" % G.index()
    s += "<tr><td>genus:</td><td>%s</td></tr>" % G.genus()
    s += "<tr><td>Cusps:</td><td>\(%s\)</td></tr>" % latex(G.cusps())
    s += "<tr><td colspan=\"2\">Number of elliptic fixed points</td></tr>"
    s += "<tr><td>order 2:</td><td>%s</td></tr>" % G.nu2()
    s += "<tr><td>order 3:</td><td>%s</td></tr>" % G.nu3()
    s += "</table>"
    return s


def pol_to_html(p):
    r"""
    Convert polynomial p to html
    """
    s = str(p)
    s = re.sub("\^(\d*)", "<sup>\\1</sup>", s)
    s = re.sub("\_(\d*)", "<sub>\\1</suB>", s)
    return s
