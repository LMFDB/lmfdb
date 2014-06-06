# -*- coding: utf-8 -*-
#*****************************************************************************
#  Copyright (C) 2010 Fredrik Strömberg <fredrik314@gmail.com>,
#  Stephan Ehlen <>
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
r""" Class for newforms in format which can be presented on the web easily


AUTHORS:

 - Fredrik Stroemberg
 - Stephan Ehlen


NOTE: We are now working completely with the Conrey naming scheme.
 
TODO:
Fix complex characters. I.e. embedddings and galois conjugates in a consistent way.

"""
from flask import url_for
from sage.all import dumps,loads
from lmfdb.modular_forms.elliptic_modular_forms import emf_logger,emf_version
from sage.rings.number_field.number_field_base import NumberField as NumberField_class
from sage.all import copy
from lmfdb.utils import url_character

from lmfdb.modular_forms.elliptic_modular_forms.backend import connect_to_modularforms_db,get_files_from_gridfs
try:
    from dirichlet_conrey import *
except:
    emf_logger.critical("Could not import dirichlet_conrey!")

class WebChar(object):
    r"""
    Temporary class which should be replaced with 
    WebDirichletCharcter once this is ok.
    
    """
    def __init__(self,modulus=0,number=0,get_from_db=True,compute=True):
        r"""
        Init self as character of given number and modulus.
        """
        if modulus <= 0 or number <=0:
            raise ValueError,"Modulus {0} and umber {1} does not correspond to a character".format(modulus,number)
        d = {
            '_modulus' : modulus,
            '_number' : number,
            '_character': None,
            '_order': None,
            '_is_trivial': None,            
            '_conductor': None,
            '_latex_name': None,
            '_name': None,
            '_sage_character': None,
            '_url': None,
            '_values_float': None,
            '_values_algebraic': None }
        self.__dict__.update(d)
        emf_logger.debug('In WebChar, self.__dict__ = {0}'.format(self.__dict__))
        if get_from_db:
            data = self.get_from_db()
        if isinstance(data, dict) and len(data.values()) > 0:
            self.__dict__.update(data)
        if data == {} and  compute:
            self.conductor()
            self.order()
            self.latex_name()
            self.sage_character()
            for i in range(self.modulus()):
                self.value(i,value_format='float')
                self.value(i,value_format='algebraic')
            self.insert_into_db()
        emf_logger.debug('In WebChar, self.__dict__ = {0}'.format(self.__dict__))

        
    def get_from_db(self):
        r"""
        Fetch self from database.
        """
        db = connect_to_modularforms_db('WebChar.files')
        s = {'modulus':self._modulus,'number':self._number,'version':emf_version}
        emf_logger.debug("Looking in DB for WebChar rec={0}".format(s))
        f = db.find_one(s)
        emf_logger.debug("Found rec={0}".format(f))
        if f<>None:
            id = f.get('_id')
            fs = get_files_from_gridfs('WebChar')
            f = fs.get(id)
            emf_logger.debug("Getting rec={0}".format(f))
            d = loads(f.read())
            return d
        return {}
        
    def insert_into_db(self):
        r"""
        Insert a dictionary of data for self into the collection WebModularforms.files
        """
        emf_logger.debug("inserting self into db! name={0}".format(self._name))
        db = connect_to_modularforms_db('WebChar.files')
        fs = get_files_from_gridfs('WebChar')
        s = {'name':self._name,'version':emf_version}
        rec = db.find_one(s)
        if rec:
            id = rec.get('_id')
        else:
            id = None
        if id<>None:
            emf_logger.debug("Removing self from db with id={0}".format(id))
            fs.delete(id)
            
        fname = "webchar-{0:0>4}-{1:0>3}".format(self._modulus,self._number) 
        d = copy(self.__dict__)
        d.pop('_url') ## This should be recomputed
        id = fs.put(dumps(d),filename=fname,n=int(self._modulus),k=int(self._number))
        emf_logger.debug("inserted :{0}".format(id))
    
        
    def modulus(self):
        r"""
        Return the modulus of self.
        """
        return self._modulus
        
    def number(self):
        r"""
        Return the number of self.
        """
        return self._number
    def character(self):
        r"""
        Return self as a DirichletCharacter_conrey
        """
        if self._character is None:
            self._character = DirichletCharacter_conrey(DirichletGroup_conrey(self._modulus),self._number)
        return self._character

    def conductor(self):
        r"""
        Return the conductor of self.
        """
        if self._conductor is None:
            self._conductor = self.character().conductor()
        return self._conductor

    def order(self):
        r"""
        Return the conductor of self.
        """
        if self._order is None:
            self._order = self.character().multiplicative_order()
        return self._order

    def sage_character(self):
        r"""
        Return self as a sage character (e.g. so that we can get algebraic values)

        """
        ## Is cached in Conrey character
        if self._sage_character is None:
            self._sage_character = self.character().sage_character()
        return self._sage_character

    def is_trivial(self):
        r"""
        Check if self is trivial.
        """
        if self._is_trivial is None:
            self._is_trivial = self.character().is_trivial()
        return self._is_trivial
            
    def latex_name(self):
        r"""
        Return the latex representation of the character of self.
        """
        if self._latex_name is None:
            self._latex_name = "\chi_{" + str(self.modulus()) + "}(" + str(self.number()) + ",\cdot)"
        return self._latex_name
    def __repr__(self):
        r"""
        Return the string representation of the character of self.
        """
        return self.name()
    
    def name(self):
        r"""
        Return the string representation of the character of self.
        """    
        if self._name is None:
            self._name = "Character nr. {0} of modulus {1}".format(self.number(),self.modulus())
        return self._name

            
    def value(self, x, value_format='algebraic'):
        r"""
        Return the value of self as an algebraic integer or float.
        """
        x = int(x)
        if value_format =='algebraic':
            if self._values_algebraic is None:
                self._values_algebraic = {}
            y = self._values_algebraic.get(x)
            if y is None:
                y = self._values_algebraic[x]=self.sage_character()(x)
            else:
                self._values_algebraic[x]=y
            return self._values_algebraic[x]
        elif value_format=='float':  ## floating point
            if self._values_float is None:
                self._values_float = {}
            y = self._values_float.get(x)
            if y is None:
                y = self._values_float[x]=self.character()(x)
            else:
                self._values_float[x]=y
            return self._values_float[x]
        else:
            raise ValueError,"Format {0} is not known!".format(value_format)
        
    def url(self):
        r"""
        Return the url of self.
        """
        if hasattr(self, '_url') and self._url is None:
            self._url = url_character(type='Dirichlet',modulus=self.modulus(), number=self.number())
        return self._url
    
   
