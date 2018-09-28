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
from lmfdb.classical_modular_forms import cmf_logger
logger = cmf_logger
from sage.all import cached_method

def newform_label(level, weight, character, label, embedding=None, make_cache_label=False):
    r"""
    Uses the label format {level}.{weight}.{character number}.{orbit label}.{embedding}
    """
    l = ''
    if make_cache_label:
        l = 'cmf.'
    if embedding is None:
        l += "{0}.{1}.{2}.{3}".format(level, weight, character, label)
    else:
        l += "{0}.{1}.{2}.{3}.{4}".format(level, weight, character, label, embedding)
    return l

def parse_newform_label(label):
    r"""
    Essentially the inverse of the above with addition that we also parse the previous label format 
    (without dot between character and label.
    
    Given "N.k.i.x" or "N.k.ix" it returns N,k,i,x
    or given "N.k.i.x.d" or "N.k.ix.d" return N,k,i,x,d

    """
    if not isinstance(label,basestring):
        raise ValueError,"Need label in string format"
    l = label.split(".")
    ## l[0] = label, l[1] = weight, l[2]="{character}{label}" or {character}
    ## l[3] = {label} or {embedding}, l[4] is either non-existing or {embedding}
    if len(l) not in [3,4,5]:
        raise ValueError,"{0} is not a valid newform label!".format(label)
    if not l[0].isdigit() or not l[1].isdigit():
        raise ValueError,"{0} is not a valid newform label!".format(label)
    level = int(l[0]); weight = int(l[1]); orbit_label = ""
    emb = None
    try:
        if len(l) >= 3 and not l[2].isdigit(): # we have N.k.ix or 
            character = "".join([x for x in l[2] if x.isdigit()])
            orbit_label = "".join([x for x in l[2] if x.isalpha()])
            if len(l)==4:
                emb = int(l[3])
        elif len(l) >= 4: # we have N.k.i.x or N.k.i.x.j 
            character = int(l[2])
            orbit_label = l[3]
            if len(l)==5:
                emb = int(l[4])
        if orbit_label == "" or not orbit_label.isalpha():
            raise ValueError
    except (ValueError,IndexError):
        raise ValueError,"{0} is not a valid newform label!".format(label)
    if not emb is None:
        return level,weight,int(character),orbit_label,emb
    else:
        return level,weight,int(character),orbit_label
        
def space_label(level, weight, character, make_cache_label=False):
    l = ''
    if make_cache_label:
        l = 'cmf.'
    return l+"{0}.{1}.{2}".format(level, weight, character)

def parse_space_label(label):
    if not isinstance(label,basestring):
        raise ValueError,"Need label in string format"    
    l = label.split(".")
    try:
        if len(l) ==3:
            level = int(l[0]); weight = int(l[1]); character = int(l[2])
            return level,weight,character
        else:
            raise ValueError
    except ValueError:
        raise ValueError,"{0} is not a valid space label!".format(label)

@cached_method
def is_newform_in_db(newform_label):
    return
    from .web_newform import WebNewform
    # first check that it is a valid label, otherwise raise ValueError
    t = parse_newform_label(newform_label)
    if len(t)==4:
       level,weight,character,label = t
    elif len(t)==5:
        level,weight,character,label,emb = t
    search = {'level':level,'weight':weight,'character':character,'label':label}
    return WebNewform._find_document_in_db_collection(search).count() > 0

