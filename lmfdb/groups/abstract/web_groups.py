import re
import string

from lmfdb import db

from sage.all import factor


#currently uses gps_small db to pretty print groups
def group_names_pretty(label):
    data = db.gps_small.lookup(label)
    if data and 'pretty' in data:
        return data['pretty']
    return label



#Abstract Group object
class WebAbstractGroup:
    def __init__(self, label, data=None):
        self.label = label
        if data is None:
            self._data = self._get_dbdata()
        else:
            self._data = data


    @classmethod
    def from_data(cls, data):
        return cls(data['label'], data)

    def _get_dbdata(self):
        return db.gps_groups.lookup(self.label)

    def is_null(self):
        return self._data is None

            
    def order(self):
        return int(self._data['order'])

    #TODO if prime factors get large, use factors in database
    def order_factor(self):
        return factor(int(self._data['order']))

    def exponent(self):
        return self._data['exponent']

    def name_label(self):
        return group_names_pretty(self._data['label'])


### properties
#also create properties list to go along with this

    def is_abelian(self):
        return self._data['abelian']

    def is_cyclic(self):
        return self._data['cyclic']

    def is_solvable(self):
        return self._data['solvable']
    
    def is_super_solvable(self):
        return self._data['supersolvable']

    def is_nilpotent(self):
        return self._data['nilpotent']

    def is_metacyclic(self):
        return self._data['metacyclic']

    def is_metabelian(self):
        return self._data['metabelian']

    def is_simple(self):
        return self._data['simple']
    
    def is_almost_simple(self):
        return self._data['almost_simple']

    def is_quasisimple(self):
        return self._data['quasisimple']

    def is_perfect(self):
        return self._data['perfect']

    def is_monomial(self):
        return self._data['monomial']

    def is_rational(self):
        return self._data['rational']
    
    def is_Zgroup(self):
        return self._data['Zgroup']

    def is_Agroup(self):
        return self._data['Agroup']

   

###automorphism group
#WHAT IF NULL??
    def aut_group(self):
        return group_names_pretty(self._data['aut_group'])

    def aut_order(self):
        return int(self._data['aut_order'])

    #TODO if prime factors get large, use factors in database
    def aut_order_factor(self):
        return factor(int(self._data['aut_order']))

#WHAT IF NULL??
    def out_group(self):
        return group_names_pretty(self._data['outer_group'])


    def out_order(self):
        return int(self._data['outer_order'])

    #TODO if prime factors get large, use factors in database
    def out_order_factor(self):
        return factor(int(self._data['outer_order']))
    

###special subgroups
    def center(self):
        return self._data['center']

    def center_label(self):
        return group_names_pretty(self._data['center_label'])

    def central_quot(self):
        return group_names_pretty(self._data['central_quotient'])
    

    def commutator(self):
        return self._data['commutator']

    def commutator_label(self):
        return group_names_pretty(self._data['commutator_label'])

    def abelian_quot(self):
        return group_names_pretty(self._data['abelian_quotient'])

    def frattini(self):
        return self._data['frattini']

    def frattini_label(self):
        return group_names_pretty(self._data['frattini_label'])

    def frattini_quot(self):
        return group_names_pretty(self._data['frattini_quotient'])  
    
    
