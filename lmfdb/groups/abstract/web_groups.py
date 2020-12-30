import re
#import string

from lmfdb import db

from sage.all import factor, lazy_attribute, Permutations, SymmetricGroup, ZZ, prod
from sage.libs.gap.libgap import libgap
from collections import Counter

fix_exponent_re = re.compile(r"\^(-\d+|\d\d+)")

#currently uses gps_small db to pretty print groups
def group_names_pretty(label):
    return db.gps_groups.lookup(label, 'tex_name')
    # Rest can be deleted if this now works
    pretty = db.gps_small.lookup(label, 'pretty')
    if pretty:
        return pretty
    else:
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
        return {subdata['label']: WebAbstractSubgroup(subdata['label'], subdata) for subdata in db.gps_subgroups.search({'ambient': self.label})}


    # special subgroups
    def special_search(self, sp):
        search_lab = '%s.%s' % (self.label, sp)
        subs = self.subgroups
        for lab in subs:
            sp_labels = (subs[lab]).special_labels
            if search_lab in sp_labels:
                return lab # is label what we want to return?
                #H = subs['lab']
                #return group_names_pretty(H.subgroup)

    @lazy_attribute
    def fitting(self):
        return self.special_search('F')

    @lazy_attribute
    def radical(self):
        return self.special_search('R')

    @lazy_attribute
    def socle(self):
        return self.special_search('S')

    # series

    def series_search(self, sp):
        ser_str = r"^%s.%s\d+" % (self.label, sp)
        ser_re = re.compile(ser_str)
        subs = self.subgroups
        ser = []
        for lab in subs:
            H = subs[lab]
            for spec_lab in H.special_labels:
                if ser_re.match(spec_lab):
                    #ser.append((H.subgroup, spec_lab)) # returning right thing?
                    ser.append((H.label, spec_lab))
        # sort
        def sort_ser(p, ch):
            return int(((p[1]).split(ch))[1])
        def sort_ser_sp(p):
            return sort_ser(p, sp)
        return [el[0] for el in sorted(ser, key = sort_ser_sp)]

    @lazy_attribute
    def chief_series(self):
        return self.series_search('C')

    @lazy_attribute
    def derived_series(self):
        return self.series_search('D')

    @lazy_attribute
    def lower_central_series(self):
        return self.series_search('L')

    @lazy_attribute
    def upper_central_series(self):
        return self.series_search('U')

    @lazy_attribute
    def diagram_ok(self):
        return self.number_subgroup_classes < 100

    @lazy_attribute
    def subgroup_profile(self):
        subs = db.gps_subgroups.search({'ambient': self.label})
        by_order= {}
        for s in subs:
            cntr = by_order.get(s['subgroup_order'], Counter())
            cntr.update({s['subgroup']:1})
            by_order[s['subgroup_order']] = cntr
        return by_order

    @lazy_attribute
    def conjugacy_classes(self):
        cl = [WebAbstractConjClass(self.label, ccdata['label'], ccdata) for ccdata in db.gps_groups_cc.search({'group': self.label})]
        return sorted(cl, key=lambda x:x.counter)

    #These are the power-conjugacy classes
    @lazy_attribute
    def conjugacy_class_divisions(self):
        cl = [WebAbstractConjClass(self.label, ccdata['label'], ccdata) for ccdata in db.gps_groups_cc.search({'group': self.label})]
        divs = {}
        for c in cl:
            divkey = re.sub(r'([^\d])-?\d+?$',r'\1', c.label)
            if divkey in divs:
                divs[divkey].append(c)
            else:
                divs[divkey]=[c]
        return divs

    @lazy_attribute
    def characters(self):
        # Should join with creps once we have images and join queries
        chrs = [WebAbstractCharacter(chardata['label'], chardata) for chardata in db.gps_char.search({'group': self.label})]
        return sorted(chrs, key=lambda x:x.counter)

    @lazy_attribute
    def rational_characters(self):
        # Should join with creps once we have images and join queries
        chrs = [WebAbstractRationalCharacter(chardata['label'], chardata) for chardata in db.gps_qchar.search({'group': self.label})]
        return sorted(chrs, key=lambda x:x.counter)

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
        return max(1, len(self.semidirect_products), len(self.nonsplit_products))

    @lazy_attribute
    def display_direct_product(self):
        # Need to pick an ordering
        #return [sub for sub in self.subgroups.values() if sub.normal and sub.direct and sub.subgroup_order != 1 and sub.quotient_order != 1]
        C = dict(self.direct_factorization)
        print(C)
        # We can use the list of subgroups to get the latex
        latex_lookup = {}
        for sub in self.subgroups.values():
            slab = sub.subgroup
            if slab in C:
                print(slab)
                latex_lookup[slab] = sub.subgroup_tex_parened
                if len(latex_lookup) == len(C):
                    break
        print(latex_lookup)
        s = r" \times ".join("%s%s" % (latex_lookup[label], "^%s" % e if e > 1 else "") for (label, e) in C.items())
        print(s)
        return s

    @lazy_attribute
    def semidirect_products(self):
        # Need to pick an ordering
        #return [sub for sub in self.subgroups.values() if sub.normal and sub.split and not sub.direct]
        subs = self.subgroups.values()
        semis = []
        pairs = []
        for sub in subs:
            if sub.normal and sub.split and not sub.direct:
                pair = [sub.subgroup, sub.quotient]
                # check if the subgroup and quotient have already appeared
                new = True
                for el in pairs:
                    if pair == el:
                        new = False
                if new:
                    semis.append(sub)
                    pairs.append(pair)
        return semis

    @lazy_attribute
    def nonsplit_products(self):
        # Need to pick an ordering
        #return list(set([sub for sub in self.subgroups.values() if sub.normal and not sub.split])) # eliminate redundancies
        subs = self.subgroups.values()
        nonsplit = []
        pairs = []
        for sub in subs:
            if sub.normal and not sub.split:
                pair = [sub.subgroup, sub.quotient]
                # check if the subgroup and quotient have already appeared
                new = True
                for el in pairs:
                    if pair == el:
                        new = False
                if new:
                    nonsplit.append(sub)
                    pairs.append(pair)
        return nonsplit


    @lazy_attribute
    def subgroup_layers(self):
        # Need to update to account for possibility of not having all inclusions
        subs = self.subgroups
        topord = max(sub.subgroup_order for sub in subs.values())
        top = [z.label for z in subs.values() if z.subgroup_order == topord][0]
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
        return [layers, edges]

    def sylow_subgroups(self):
        """
        Returns a list of pairs (p, P) where P is a WebAbstractSubgroup representing a p-Sylow subgroup.
        """
        syl_dict = {}
        for sub in self.subgroups.values():
            if sub.sylow > 0:
                syl_dict[sub.sylow] = sub
        syl_list = []
        for p, e in factor(self.order):
            if p in syl_dict:
                syl_list.append((p, syl_dict[p]))
        return syl_list

    def series(self):
        data = [['group.%s'%ser,
                 ser.replace('_',' ').capitalize(),
                 [self.subgroups[i] for i in getattr(self, ser)],
                 "-".join(map(str, getattr(self, ser))),
                 r'\rhd']
                for ser in ['derived_series', 'chief_series', 'lower_central_series', 'upper_central_series']]
        data[3][4] = r'\lhd'
        data[3][2].reverse()
        return data

    def schur_multiplier_text(self):
        return "trivial" if self.schur_multiplier == [] else self.schur_multiplier

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
        return str(SymmetricGroup(n)(Permutations(n).unrank(code)))

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
        # Given a decoded element or free group lift, return a latex form for printing on the webpage.
        if self.elt_rep_type == 0:
            s = str(elt)
            for i in reversed(range(self.ngens)): # reversed so that we don't replace f1 in f10.
                s = s.replace("f%s"%(i+1), chr(97+i))
            return s

    # TODO: is this the presentation we want?
    def presentation(self):
        # chr(97) = "a"
        if self.elt_rep_type == 0:
            # We use knowledge of the form of the presentation to construct it manually.
            gens = list(self.G.GeneratorsOfGroup())
            pcgs = self.G.FamilyPcgs()
            used = [u-1 for u in sorted(self.gens_used)] # gens_used is 1-indexed
            rel_ords = [ZZ(p) for p in self.G.FamilyPcgs().RelativeOrders()]
            pure_powers = []
            rel_powers = []
            comm = []
            relators = []
            def print_elt(vec):
                s = ""
                e = 0
                u = used[-1]
                i = len(used) - 1
                for j, (c, p) in reversed(list(enumerate(zip(vec, rel_ords)))):
                    e *= p
                    e += c
                    if j == u:
                        if e == 1:
                            s = chr(97+i) + s
                        elif e > 1:
                            s = "%s^{%s}" % (chr(97+i), e) + s
                        i -= 1
                        u = used[i]
                        e = 0
                return s

            ngens = len(used)
            for i in range(ngens):
                a = used[i]
                e = prod(rel_ords[a:] if i == ngens-1 else rel_ords[a: used[i+1]])
                ae = pcgs.ExponentsOfPcElement(gens[a]**e)
                if all(x == 0 for x in ae):
                    pure_powers.append("%s^{%s}" % (chr(97+i), e))
                else:
                    rel_powers.append("%s^{%s}=%s" % (chr(97+i), e, print_elt(ae)))
                for j in range(i+1, ngens):
                    b = used[j]
                    if all(x == 0 for x in pcgs.ExponentsOfCommutator(b+1, a+1)): # back to 1-indexed
                        if not self.abelian:
                            comm.append("[%s,%s]" % (chr(97+i), chr(97+j)))
                    else:
                        v = pcgs.ExponentsOfConjugate(b+1, a+1) # back to 1-indexed
                        relators.append("%s^{%s}=%s" % (chr(97+j), chr(97+i), print_elt(v)))
            show_gens = ', '.join(chr(97+i) for i in range(len(used)))
            if pure_powers or comm:
                rel_powers = ["=".join(pure_powers + comm) + "=1"] + rel_powers
            relators = ', '.join(rel_powers + relators)
            return r"\langle %s \mid %s \rangle" % (show_gens, relators)
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

    ###automorphism group
    #WHAT IF NULL??
    def show_aut_group(self):
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
    def cent(self):
        return self.special_search('Z')

    def cent_label(self):
        return group_names_pretty(self._data['center_label'])

    def central_quot(self):
        return group_names_pretty(self._data['central_quotient'])
    

    def comm(self):
        return self.special_search('D')

    def comm_label(self):
        return group_names_pretty(self._data['commutator_label'])

    def abelian_quot(self):
        return group_names_pretty(self._data['abelian_quotient'])

    def fratt(self):
        return self.special_search('Phi')

    def fratt_label(self):
        return group_names_pretty(self._data['frattini_label'])

    def frattini_quot(self):
        return group_names_pretty(self._data['frattini_quotient'])


class WebAbstractSubgroup(WebObj):
    table = db.gps_subgroups
    def __init__(self, label, data=None):
        WebObj.__init__(self, label, data)
        self.ambient_gp = self.ambient # in case we still need it
        self.subgroup_tex = s = group_names_pretty(self.subgroup) # temporary
        self.subgroup_tex_parened = s if self._is_atomic(s) else "(%s)" % s
        if 'quotient' in self._data:
            self.quotient_tex = s = group_names_pretty(self.quotient) # temporary
            self.quotient_tex_parened = s if self._is_atomic(s) else "(%s)" % s

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

    def make_span(self):
        return '<span class="{}" data-sgid="{}">${}$</span>'.format(
            self.spanclass(), self.label, self.subgroup_tex)

    @staticmethod
    def _is_atomic(s):
        return not any(sym in s for sym in [".", ":", r"\times", r"\rtimes", r"\wr"])

# Conjugacy class labels do not contain the group
class WebAbstractConjClass(WebObj):
    table = db.gps_groups_cc
    def __init__(self, ambient_gp, label, data=None):
        self.ambient_gp = ambient_gp
        data = db.gps_groups_cc.lucky({'group': ambient_gp, 'label':label})
        WebObj.__init__(self, label, data)

class WebAbstractCharacter(WebObj):
    table = db.gps_char
    def __init__(self, label, data=None):
        WebObj.__init__(self, label, data)

    def type(self):
        if self.indicator == 0:
            return "C"
        if self.indicator > 0:
            return "R"
        return "S"

class WebAbstractRationalCharacter(WebObj):
    table = db.gps_qchar
    def __init__(self, label, data=None):
        WebObj.__init__(self, label, data)

class WebAbstractSupergroup(WebObj):
    table = db.gps_subgroups
    def __init__(self, sub_or_quo, typ, label, data=None):
        self.sub_or_quo_gp = sub_or_quo
        self.typ = typ
        WebObj.__init__(self, label, data)
        self.ambient_tex = group_names_pretty(self.ambient) # temporary
