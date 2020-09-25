import re
#import string

from lmfdb import db

from sage.all import factor, lazy_attribute, Permutations, SymmetricGroup, ZZ
from sage.libs.gap.libgap import libgap

fix_exponent_re = re.compile(r"\^(-\d+|\d\d+)")

#currently uses gps_small db to pretty print groups
def group_names_pretty(label):
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
        return max(len(self.direct_products), len(self.semidirect_products), len(self.nonsplit_products))

    @lazy_attribute
    def direct_products(self):
        # Need to pick an ordering
        return [sub for sub in self.subgroups.values() if sub.normal and sub.direct and sub.subgroup_order != 1 and sub.quotient_order != 1]

    @lazy_attribute
    def semidirect_products(self):
        # Need to pick an ordering
        #return [sub for sub in self.subgroups.values() if sub.normal and sub.split and not sub.direct]
        subs = self.subgroups.values()
        semis = []
        for sub in subs:
            if sub.normal and sub.split and not sub.direct:
                new = True
                for el in semis:
                    if sub.subgroup == el.subgroup:
                        new = False
                if new:
                    semis.append(sub)
        return semis

    @lazy_attribute
    def nonsplit_products(self):
        # Need to pick an ordering
        return [sub for sub in self.subgroups.values() if sub.normal and not sub.split]

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
            FP = self.G.FamilyPcgs().IsomorphismFpGroupByPcgs("f").Image()
            F = FP.FreeGroupOfFpGroup()
            Fgens = FP.FreeGeneratorsOfFpGroup()
            used = self.gens_used
            print("USED", used)
            relator_lifts = FP.RelatorsOfFpGroup()
            pure_powers = {}
            rel_powers = {}
            power_exp = {}
            power_rhs = {}
            conj = {}
            for rel in relator_lifts:
                m = rel.NumberSyllables()
                a = ZZ(rel.GeneratorSyllable(1))
                e = ZZ(rel.ExponentSyllable(1))
                if m == 1:
                    # pure power relation
                    if a in power_exp:
                        raise ValueError("Invalid internal pc presentation: two values for f%s^p" % g)
                    power_exp[a] = e
                    power_rhs[a] = F.One()
                elif (m >= 4 and
                      e == rel.ExponentSyllable(2) == -1 and
                      rel.ExponentSyllable(3) == 1 and
                      rel.GeneratorSyllable(3) == a):
                    b = ZZ(rel.GeneratorSyllable(2))
                    if not (m == 4 and rel.GeneratorSyllable(4) == b and rel.ExponentSyllable(4) == 1):
                        # We omit pure commutator relations and explain below the presentation
                        rhs = rel.SubSyllables(4, m)
                        # started with a^-1 b^-1 a b X = 1, transformed to b^a = b X =: rhs
                        if (b,a) in conj:
                            raise ValueError("Invalid internal pc presentation: two values for f%s^f%s" % (b, a))
                        conj[b,a] = rhs
                else:
                    # relative power relation
                    if a in power_exp:
                        raise ValueError("Invalid internal pc presentation: two values for f%s^p" % a)
                    power_exp[a] = e
                    power_rhs[a] = rel.SubSyllables(2,m)**-1
                    if a+1 not in used and power_rhs[a] != Fgens[a]:
                        raise ValueError("Invalid internal pc presentation: f%s^%s != f%s" % (a, e, a+1))
            print("power_exp", power_exp)
            print("power_rhs", power_rhs)
            print("conj", conj)
            rewrite = []
            curpow = 1
            curgen = 1
            genenum = 0
            genpow_rhs = []
            genpow_exp = []
            for i in sorted(power_exp):
                # check that the values are contiguous
                if not (i == 1 or i-1 in power_exp):
                    raise ValueError("Invalid internal pc presentation: no value given for %s^p" % chr(96+i))
                rewrite.append(Fgens[genenum]**curpow)
                curpow *= power_exp[i]
                if i == len(power_exp) or i+1 in used:
                    genpow_rhs.append(power_rhs[i])
                    genpow_exp.append(curpow)
                    curgen = i+1
                    genenum += 1
                    curpow = 1
            M = len(genpow_exp)
            #if len(genpow_exp) != self.ngens:
            #    raise ValueError("Invalid internal pc presentation: number of generators %s vs %s" % (len(genpow_exp), self.ngens))
            hom = F.GroupHomomorphismByImagesNC(F, rewrite)
            for i, (rhs, e) in enumerate(zip(genpow_rhs, genpow_exp)):
                if rhs == F.One():
                    pure_powers[i] = "%s^%s" % (chr(97+i), e)
                else:
                    rel_powers[i] = "%s^%s=%s" % (chr(97+i), e, hom.Image(rhs))
            gens = ', '.join(chr(97+i) for i in range(M))
            relators = []
            if pure_powers:
                relators.append("=".join(pure_powers[g] for g in sorted(pure_powers)) + "=1")
            for g in sorted(rel_powers):
                relators.append(rel_powers[g])
            for a,b in sorted(conj):
                if a in used and b in used:
                    relators.append("%s^%s=%s" % (chr(97+used.index(a)), chr(97+used.index(b)), hom.Image(conj[a,b])))
            relators = ', '.join(relators)
            for i in reversed(range(M)):
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
        self.subgroup_tex = group_names_pretty(self.subgroup) # temporary
        if 'quotient' in self._data:
            self.quotient_tex = group_names_pretty(self.quotient) # temporary

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
