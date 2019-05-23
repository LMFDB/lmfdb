import re
import string

from lmfdb import db

from sage.all import factor, lazy_attribute

#currently uses gps_small db to pretty print groups
def group_names_pretty(label):
    data = db.gps_small.lookup(label)
    if data and 'pretty' in data:
        return data['pretty']
    return label

class WebObj(object):
    def __init__(self, label, data=None):
        self.label = label
        if data is None:
            self._data = self._get_dbdata()
        else:
            self._data = data
        for key, val in self._data.items():
            setattr(self, key, val)

    @classmethod
    def from_data(cls, data):
        return cls(data['label'], data)

    def _get_dbdata(self):
        return self.table.lookup(self.label)

#Abstract Group object
class WebAbstractGroup(WebObj):
    table = db.gps_groups
    def __init__(self, label, data=None):
        WebObj.__init__(self, label, data)
        self.tex_name = group_names_pretty(label) # remove once in database

    @lazy_attribute
    def subgroups(self):
        # Should join with gps_groups to get pretty names for subgroup and quotient
        return {subdata['counter']: WebAbstractSubgroup(self, subdata['label'], subdata) for subdata in db.gps_subgroups.search({'ambient': self.label})}

    @lazy_attribute
    def conjugacy_classes(self):
        return {ccdata['counter']: WebAbstractConjClass(self, ccdata['label'], ccdata) for ccdata in db.gps_groups_cc.search({'group': self.label})}

    @lazy_attribute
    def characters(self):
        # Should join with creps once we have images and join queries
        return {chardata['counter']: WebAbstractCharacter(self, chardata['label'], chardata) for chardata in db.gps_char.search({'group': self.label})}

    @lazy_attribute
    def maximal_subgroup_of(self):
        # Could show up multiple times as non-conjugate maximal subgroups in the same ambient group
        # So we should elimintate duplicates from the following list
        return [WebAbstractSupergroup(self, 'sub', supdata['label'], supdata) for supdata in db.gps_subgroups.search({'subgroup': self.label, 'maximal':True}, sort=['ambient_order','ambient'], limit=10)]

    @lazy_attribute
    def maximal_quotient_of(self):
        # Could show up multiple times as a quotient of different normal subgroups in the same ambient group
        # So we should elimintate duplicates from the following list
        return [WebAbstractSupergroup(self, 'quo', supdata['label'], supdata) for supdata in db.gps_subgroups.search({'quotient': self.label, 'minimal_normal':True}, sort=['ambient_order', 'ambient'])]

    @lazy_attribute
    def direct_products(self):
        # Need to pick an ordering
        return [sub for sub in self.subgroups.values() if sub.normal and sub.direct and sub.subgroup_order != 1 and sub.quotient_order != 1]

    @lazy_attribute
    def semidirect_products(self):
        # Need to pick an ordering
        return [sub for sub in self.subgroups.values() if sub.normal and sub.split and not sub.direct]

    @lazy_attribute
    def nonsplit_products(self):
        # Need to pick an ordering
        return [sub for sub in self.subgroups.values() if sub.normal and not sub.split]

    @lazy_attribute
    def subgroup_layers(self):
        # Need to update to account for possibility of not having all inclusions
        subs = self.subgroups
        top = max(sub.counter for sub in subs.values())
        layers = [[subs[top]]]
        seen = set([top])
        added_something = True # prevent data error from causing infinite loop
        print "starting while"
        while len(seen) < len(subs) and added_something:
            layers.append([])
            added_something = False
            for H in layers[-2]:
                print H.counter
                print "contains", H.contains
                for new in H.contains:
                    if new not in seen:
                        seen.add(new)
                        added_something = True
                        layers[-1].append(subs[new])
        print [[gp.subgroup for gp in layer] for layer in layers]
        return layers

    def sylow_subgroups(self):
        """
        Returns a list of pairs (p, P) where P is a WebAbstractSubgroup representing a p-Sylow subgroup.
        """
        syl_dict = {}
        for sub in self.subgroups.values():
            if sub.sylow > 0:
                syl_dict[sub.sylow] = sub
        syl_list = []
        for p, e in self.factored_order:
            if p in syl_dict:
                syl_list.append((p, syl_dict[p]))
        return syl_list

    def series(self):
        return [('group.%s'%name,
                 name.replace('_',' ').capitalize(),
                 [self.subgroups[i] for i in getattr(self, name)],
                 "-".join(map(str, getattr(self, name))))
                for name in ['derived_series', 'chief_series', 'lower_central_series', 'upper_central_series']]

    def is_null(self):
        return self._data is None


    def order(self):
        return int(self._data['order'])

    #TODO if prime factors get large, use factors in database
    def order_factor(self):
        return factor(int(self._data['order']))

    def name_label(self):
        return group_names_pretty(self._data['label'])

<<<<<<< HEAD

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
=======
    ###automorphism group
    #WHAT IF NULL??
    def show_aut_group(self):
        return group_names_pretty(self.aut_group)
>>>>>>> Removing access functions from web_group, some other backend group changes

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
        return self._data['frattini_quotient']

class WebAbstractSubgroup(WebObj):
    table = db.gps_subgroups
    def __init__(self, ambient_gp, label, data=None):
        self.ambient_gp = ambient_gp
        WebObj.__init__(self, label, data)
        self.subgroup_tex = db.gps_small.lookup(self.subgroup, 'pretty') # temporary
        if 'quotient' in self._data:
            self.quotient_tex = db.gps_small.lookup(self.quotient, 'pretty') # temporary

    def spanclass(self):
        s = "subgp"
        if self.characteristic:
            s += " chargp"
        elif self.normal:
            s += " normgp"
        return s

class WebAbstractConjClass(WebObj):
    table = db.gps_groups_cc
    def __init__(self, ambient_gp, label, data=None):
        self.ambient_gp = ambient_gp
        WebObj.__init__(self, label, data)

class WebAbstractCharacter(WebObj):
    table = db.gps_char
    def __init__(self, ambient_gp, label, data=None):
        self.ambient_gp = ambient_gp
        WebObj.__init__(self, label, data)

class WebAbstractSupergroup(WebObj):
    table = db.gps_subgroups
    def __init__(self, sub_or_quo, typ, label, data=None):
        self.sub_or_quo_gp = sub_or_quo
        self.typ = typ
        WebObj.__init__(self, label, data)
        self.ambient_tex = db.gps_small.lookup(self.ambient, 'pretty') # temporary
