import re
import string

from lmfdb import db

from sage.all import factor, lazy_attribute

#currently uses gps_small db to pretty print groups
def group_names_pretty(label):
    pretty = db.gps_small.lookup(label, 'pretty')
    if pretty:
        return pretty
    else:
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
        self.subgroups = {subdata['counter']: WebAbstractSubgroup(self, subdata['label'], subdata) for subdata in db.gps_subgroups.search({'ambient':label})} # Should join with gps_groups to get pretty names for subgroup and quotient
        self.conjugacy_classes = {ccdata['counter']: WebAbstractConjClass(self, ccdata['label'], ccdata) for ccdata in db.gps_groups_cc.search({'group':label})}
        self.characters = {chardata['counter']: WebAbstractCharacter(self, chardata['label'], chardata) for chardata in db.gps_char.search({'group':label})} # Should join with creps once we have images and join queries
        self.maximal_subgroup_of = [WebAbstractSupergroup(self, 'sub', supdata['label'], supdata) for supdata in db.gps_subgroups.search({'subgroup':label, 'maximal':True})]
        self.maximal_quotient_of = [WebAbstractSupergroup(self, 'quo', supdata['label'], supdata) for supdata in db.gps_subgroups.search({'quotient':label, 'minimal_normal':True})]
        self.direct_products = [sub for sub in self.subgroups.values() if sub.normal and sub.direct and sub.subgroup_order != 1 and sub.quotient_order != 1]
        self.semidirect_products = [sub for sub in self.subgroups.values() if sub.normal and sub.split and not sub.direct]
        self.nonsplit_products = [sub for sub in self.subgroups.values() if sub.normal and not sub.split]

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

    def p_sylow(self, p):
        for sub in self.subgroups.values():
            if sub.sylow == p:
                return sub.subgroup_tex

    def is_null(self):
        return self._data is None


    def order(self):
        return int(self._data['order'])

    #TODO if prime factors get large, use factors in database
    def order_factor(self):
        return factor(int(self._data['order']))

    def name_label(self):
        return group_names_pretty(self._data['label'])

    ###automorphism group
    #WHAT IF NULL??
    def show_aut_group(self):
        return group_names_pretty(self.aut_group)

    #TODO if prime factors get large, use factors in database
    def aut_order_factor(self):
        return factor(int(self._data['aut_order']))

    #WHAT IF NULL??
    def show_outer_group(self):
        return group_names_pretty(self.outer_group)


    def out_order(self):
        return int(self._data['outer_order'])

    #TODO if prime factors get large, use factors in database
    def out_order_factor(self):
        return factor(int(self._data['outer_order']))

    ###special subgroups

    def show_center_label(self):
        return group_names_pretty(self.center_label)

    def show_central_quotient(self):
        return group_names_pretty(self.central_quotient)

    def show_commutator_label(self):
        return group_names_pretty(self.commutator_label)

    def show_abelian_quotient(self):
        return group_names_pretty(self.abelian_quotient)

    def show_frattini_label(self):
        return group_names_pretty(self.frattini_label)

    def show_frattini_quotient(self):
        return group_names_pretty(self.frattini_quotient)

class WebAbstractSubgroup(WebObj):
    table = db.gps_subgroups
    def __init__(self, ambient_gp, label, data=None):
        self.ambient_gp = ambient_gp
        WebObj.__init__(self, label, data)
        self.subgroup_tex = group_names_pretty(self.subgroup) # temporary
        if 'quotient' in self._data:
            self.quotient_tex = group_names_pretty(self.quotient) # temporary

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
        self.ambient_tex = group_names_pretty(self.ambient) # temporary
