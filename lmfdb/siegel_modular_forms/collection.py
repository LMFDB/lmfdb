# -*- coding: utf-8 -*-
# This file provides the class Collection whose instances
# represent the respective collections of Siegel modular forms.
#
# Author: Nils Skoruppa <nils.skoruppa@gmail.com>

from sage.structure.sage_object import SageObject
from sage.misc.latex import Latex
from lmfdb.base import getDBConnection
import urllib, importlib, json, inspect
from sample import Samples

# For Release 1.0, all Collection objects are read from static
# The db collection siegel_modular_forms.collections does not yet exist

def smf_db_collections():
    return getDBConnection().siegel_modular_forms.collections

class Collection (SageObject):
    """
    Represents a collection of data items
    of the lmfdb Siegel modular forms module.
    """

    def __init__(self, name, location = None):

        if location:
            # we get the data describing the collection 'name' from a json file
            fip = urllib.urlopen(location + '/' + name + '.json')
            doc = json.load(fip)
        else:
            # otherwise we retrieve the data from the db (currently this will always return None)
            doc = smf_db_collections().find_one({ 'name': name })
        if not doc:
            raise ValueError ("Collection %s at %s not found" % (name, location))
        self.__name = name
        self.__latex_name = doc.get('latex_name')
        if not self.__latex_name:
            self.__latex_name =  Latex(self.name())
        self.__description = doc.get('description')
        self.__dimension = doc.get('dimension')
        if self.__dimension:
            a,b,c = self.__dimension.rpartition('.')
            module = importlib.import_module(a)
            self.__dimension = module.__dict__[c]
            self.__dimension_desc = { 'name': self.__name,
                                      'args': inspect.getargspec(self.__dimension).args,
                                    }
            self.__dimension_glossary = self.__dimension.func_doc
        else:
            self.__dimension_desc = None
            self.__dimension_glossary = None
        self.__members = None
        # a number for sorting the collections on the webpages iike
        # {% for col in COLN|sort(attribute = 'order') %}
        self.order = doc.get('order')
        self.dim_args_default = doc.get('dim_args_default')
        
    def name(self):
        return self.__name

    def latex_name(self):
        return self.__latex_name

    def description(self):
        return self.__description

    def computes_dimensions(self):
        return True if self.__dimension else False
    
    def dimension(self, *args, **kwargs):
        return self.__dimension(*args, **kwargs) if self.__dimension else None

    def dimension_desc(self):
        return self.__dimension_desc

    def dimension_glossary(self):
        return self.__dimension_glossary

    def members(self):
        """
        Return a list of members by name.
        """
        if not self.__members:
            self.__members = Samples({ 'collection': self.__name })
        return self.__members
