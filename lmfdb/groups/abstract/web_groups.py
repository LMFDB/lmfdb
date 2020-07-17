import re
#import string

from lmfdb import db

from sage.all import factor, lazy_attribute, Permutations, SymmetricGroup
from sage.libs.gap.libgap import libgap

fix_exponent_re = re.compile(r"\^(-\d+|\d\d+)")

#currently uses gps_small db to pretty print groups
def group_names_pretty(label):
    data = db.gps_small.lookup(label)
    if data and 'pretty' in data:
        return data['pretty']
    return label

def group_pretty_image(label):
    pretty = group_names_pretty(label)
    img = db.gps_images.lookup(pretty, 'image')
    if img:
        return str(img)
    else: # we don't have it, not sure what to do
        return None

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
        return {subdata['counter']: WebAbstractSubgroup(subdata['label'], subdata) for subdata in db.gps_subgroups.search({'ambient': self.label})}

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

    def most_product_expressions(self):
        return max(len(self.direct_products), len(self.semidirect_products), len(self.nonsplit_products))

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
        #print "starting while"
        while len(seen) < len(subs) and added_something:
            layers.append([])
            added_something = False
            for H in layers[-2]:
                #print H.counter
                #print "contains", H.contains
                for new in H.contains:
                    if new not in seen:
                        seen.add(new)
                        added_something = True
                        layers[-1].append(subs[new])
        edges = []
        for g in subs:
            for h in subs[g].contains:
                edges.append([h, g])
        #print [[gp.subgroup for gp in layer] for layer in layers]
        return [layers, edges]

    # May not use anymore
    @lazy_attribute
    def subgroup_layer_by_order(self):
        # Need to update to account for possibility of not having all inclusions
        subs = self.subgroups
        orders = list(set(sub.subgroup_order for sub in subs.values()))
        layers = {j:[] for j in orders}
        edges = []
        for sub in subs.values():
            layers[sub.subgroup_order].append(sub)
            for k in sub.contained_in:
                edges.append([k, sub.counter])
        llayers = [layers[k] for k in sorted(layers.keys())]
        llayers = [[[gp.counter, str(gp.subgroup_tex), str(gp.subgroup), gp.count] for gp in ll] for ll in llayers]
        return [llayers, edges]

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
        data = [['group.%s'%name,
                 name.replace('_',' ').capitalize(),
                 [self.subgroups[i] for i in getattr(self, name)],
                 "-".join(map(str, getattr(self, name))),
                 r'\rhd']
                for name in ['derived_series', 'chief_series', 'lower_central_series', 'upper_central_series']]
        data[3][4] = r'\lhd'
        data[3][2].reverse()
        return data

    @lazy_attribute
    def G(self):
        # Reconstruct the group from the data stored above
        if self.order == 1: # trvial
            return libgap.TrivialGroup()
        elif self.elt_rep_type == 0: # PcGroup
            return libgap.PcGroupCode(self.pc_code, self.order)
        elif self.elt_rep_type < 0: # Permutation group
            gens = [self.decode(g) for g in self.perm_gens]
            return libgap.Group(gens)
        else:
            # TODO: Matrix groups
            raise NotImplementedError

    @lazy_attribute
    def pcgs(self):
        return self.G.Pcgs()
    def decode_as_pcgs(self, code):
        # Decode an element
        vec = []
        if code < 0 or code >= self.order:
            raise ValueError
        for m in reversed(self.pcgs_relative_orders):
            c = code % m
            vec.insert(0, c)
            code = code // m
        return self.pcgs.PcElementByExponents(vec)
    def decode_as_perm(self, code):
        # code should be an integer with 0 <= m < factorial(n)
        n = -self.elt_rep_type
        return SymmetricGroup(n)(Permutations(n).unrank(code))

    #@lazy_attribute
    #def fp_isom(self):
    #    G = self.G
    #    P = self.pcgs
    #    def position(x):
    #        # Return the unique generator
    #        vec = P.ExponentsOfPcElement(x)
    #        if sum(vec) == 1:
    #            for i in range(len(vec)):
    #                if vec[i]:
    #                    return i
    #    gens = G.GeneratorsOfGroup()
    #    # We would like to remove extraneous generators, but can't figure out how to do so
    #    rords = P.RelativeOrders()
    #    for i, (g, r) in enumerate(zip(gens, rords)):
    #        j = position(g**r)
    #        if j is None:
    #            # g^r is not another generator

    def write_element(self, elt):
        # Given an uncoded element, return a latex form for printing on the webpage.
        if self.elt_rep_type == 0:
            s = str(elt)
            for i in range(self.ngens):
                s = s.replace("f%s"%(i+1), chr(97+i))
            return s

    def presentation(self):
        if self.elt_rep_type == 0:
            relators = self.G.FamilyPcgs().IsomorphismFpGroupByPcgs("f").Image().RelatorsOfFpGroup()
            gens = ', '.join(chr(97+i) for i in range(self.ngens))
            relators = ', '.join(map(str, relators))
            for i in range(self.ngens):
                relators = relators.replace("f%s"%(i+1), chr(97+i))
            relators = fix_exponent_re.sub(r"^{\1}", relators)
            relators = relators.replace("*","")
            return r"\langle %s \mid %s \rangle" % (gens, relators)
        elif self.elt_rep_type < 0:
            return r"\langle %s \rangle" % (", ".join(map(self.decode_as_perm, self.perm_gens)))
        else:
            raise NotImplementedError

    def is_null(self):
        return self._data is None


    def order(self):
        return int(self._data['order'])

    #TODO if prime factors get large, use factors in database
    def order_factor(self):
        return factor(int(self._data['order']))

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
    def show_aut_group(self):
        return group_names_pretty(self.aut_group)
        try:
            return group_names_pretty(self.aut_group)
        except:
            return r'\textrm{Not computed}'

    #TODO if prime factors get large, use factors in database
    def aut_order_factor(self):
        return factor(int(self._data['aut_order']))

    #WHAT IF NULL??
    def show_outer_group(self):
        try:
            return group_names_pretty(self.outer_group)
        except:
            return r'\textrm{Not computed}'


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
    def __init__(self, label, data=None):
        WebObj.__init__(self, label, data)
        self.ambient_gp = self.ambient # in case we still need it
        self.subgroup_tex = group_names_pretty(self.subgroup) # temporary
        if 'quotient' in self._data:
            self.quotient_tex = db.gps_small.lookup(self.quotient, 'pretty') # temporary

    @classmethod
    def from_label(cls, label):
        ambientlabel = re.sub(r'^(\d+\.[a-z0-9]+)\.\d+$', r'\1', label)
        ambient = WebAbstractGroup(ambientlabel)
        return cls(ambient, label)
        
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
