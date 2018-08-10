# -*- coding: utf-8 -*-
# This file provides the class Collection whose instances
# represent the respective collections of Siegel modular forms.
#
# Author: Nils Skoruppa <nils.skoruppa@gmail.com>

from sage.structure.sage_object import SageObject
from sage.misc.latex import Latex
from lmfdb.db_backend import db
import importlib, inspect
from sample import Samples

def get_smf_families():
    return [SiegelFamily(doc['name'], doc) for doc in db.smf_families.search({})]

def get_smf_family(name):
    try:
        return SiegelFamily(name)
    except ValueError:
        return None

class SiegelFamily (SageObject):
    """
    Represents a family of spaces of Siegel modular forms.
    """

    def __init__(self, name, doc=None):
        if doc is None:
            doc = db.smf_families.lucky({ 'name': name })
            if not doc:
                raise ValueError ('Siegel modular form family "%s" not found in database' % (name))
        self.name = name
        self.latex_name = doc.get('latex_name')
        if not self.latex_name:
            self.latex_name =  Latex(self.name)
        self.degree = doc.get('degree')
        self.dim_args_default = doc.get('dim_args_default')
        module = importlib.import_module('lmfdb.siegel_modular_forms.dimensions')
        self.__dimension = module.__dict__.get('dimension_'+name)
        if self.__dimension:
            self.__dimension_desc = { 'name': name,
                                      'args': inspect.getargspec(self.__dimension).args,
                                    }
            self.__dimension_glossary = self.__dimension.func_doc
        else:
            self.__dimension_desc = None
            self.__dimension_glossary = None
        self.__samples = None
        self.order = doc.get('order')
        
    def computes_dimensions(self):
        return True if self.__dimension else False
    
    def dimension(self, *args, **kwargs):
        return self.__dimension(*args, **kwargs) if self.__dimension else None

    def dimension_desc(self):
        return self.__dimension_desc

    def dimension_glossary(self):
        return self.__dimension_glossary

    def samples(self):
        if not self.__samples:
            self.__samples = Samples({'collection': {'$contains': [self.name]}})
        return self.__samples
