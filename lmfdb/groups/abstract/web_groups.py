import re
#import string

from lmfdb import db

from lmfdb.groups.abstract import abstract_logger
from sage.all import factor, lazy_attribute, Permutations, SymmetricGroup, ZZ, prod
from sage.libs.gap.libgap import libgap
from collections import Counter
from lmfdb.utils import to_ordinal, display_knowl, sparse_cyclotomic_to_latex

fix_exponent_re = re.compile(r"\^(-\d+|\d\d+)")

def group_names_pretty(label):
    if isinstance(label, str):
        pretty = db.gps_groups.lookup(label, 'tex_name')
    else:
        pretty = label.tex_name
    if pretty:
        return pretty
    else:
        return label

def group_pretty_image(label):
    pretty = group_names_pretty(label)
    img = db.gps_images.lookup(pretty, 'image')
    if img:
        return str(img)
    # fallback which should always be in the database
    img = db.gps_images.lookup('?', 'image')
    if img:
        return str(img)
    else: # we should not get here
        return None

def product_sort_key(sub):
    s = sub.subgroup_tex_parened + sub.quotient_tex_parened
    s = s.replace("{","").replace("}","").replace(" ","").replace(r"\rm","").replace(r"\times", "x")
    v = []
    for c in "SALwOQDC":
        # A rough preference order for groups S_n (and SL_n), A_n, GL_n, wreath products, OD_n, Q_n, D_n, and finally C_n
        v.append(-s.count(c))
    return len(s), v

class WebObj(object):
    def __init__(self, label, data=None):
        self.label = label
        if data is None:
            data = self._get_dbdata()
        self._data = data
        if data is not None:
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

    @lazy_attribute
    def subgroups(self):
        # Should join with gps_groups to get pretty names for subgroup and quotient
        abstract_logger.info("subgroups start")
        X = db.gps_subgroups.search({'ambient': self.label})
        abstract_logger.info("search done")
        D = {subdata['label']: WebAbstractSubgroup(subdata['label'], subdata) for subdata in X}
        abstract_logger.info("subgroups end")
        return D


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
        by_order= {}  # a dictionary of Counters
        for s in subs:
            cntr = by_order.get(s['subgroup_order'], Counter())
            cntr.update({s['subgroup']:1})
            by_order[s['subgroup_order']] = cntr
        return by_order

    @lazy_attribute
    def conjugacy_classes(self):
        cl = [WebAbstractConjClass(self.label, ccdata['label'], ccdata) for ccdata in db.gps_groups_cc.search({'group': self.label})]
        divs = {}
        for c in cl:
            divkey = re.sub(r'([^\d])-?\d+?$',r'\1', c.label)
            if divkey in divs:
                divs[divkey].append(c)
            else:
                divs[divkey] = [c]
        ccdivs = []
        for divkey, ccs in divs.items():
            div = WebAbstractDivision(self.label, divkey, ccs)
            for c in ccs:
                c.division = div
            ccdivs.append(div)
        ccdivs.sort(key=lambda x: x.classes[0].counter)
        self.conjugacy_class_divisions = ccdivs
        return sorted(cl, key=lambda x:x.counter)

    #These are the power-conjugacy classes
    @lazy_attribute
    def conjugacy_class_divisions(self):
        cl = self.conjugacy_classes # creates divisions
        return self.conjugacy_class_divisions

    @lazy_attribute
    def sorted_cc_divisions(self):
        ccdivs = [{'label': k, 'classes': v} for k, v in self.conjugacy_class_divisions.items()]
        ccdivs.sort(key=lambda x: x['classes'][0].counter)
        return ccdivs

    @lazy_attribute
    def cc_to_div(self):
        # Need to map cc's to their divisions
        ctor = {}
        for k, vs in self.conjugacy_class_divisions.items():
            for v in vs:
                ctor[v.label] = k
        return ctor

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
        # We can use the list of subgroups to get the latex
        latex_lookup = {}
        sort_key = {}
        for sub in self.subgroups.values():
            slab = sub.subgroup
            if slab in C:
                latex_lookup[slab] = sub.subgroup_tex_parened
                sort_key[slab] = (not sub.abelian, sub.subgroup_order.is_prime_power(get_data=True)[0] if sub.abelian else sub.subgroup_order, sub.subgroup_order)
                if len(latex_lookup) == len(C):
                    break
        df = sorted(self.direct_factorization, key=lambda x: sort_key[x[0]])
        s = r" \times ".join("%s%s" % (latex_lookup[label], "^%s" % e if e > 1 else "") for (label, e) in df)
        return s

    @lazy_attribute
    def semidirect_products(self):
        semis = []
        count = Counter()
        for sub in self.subgroups.values():
            if sub.normal and sub.split and not sub.direct:
                pair = (sub.subgroup, sub.quotient)
                if pair not in count:
                    semis.append(sub)
                count[pair] += 1
        semis.sort(key=product_sort_key)
        return [(sub, count[sub.subgroup, sub.quotient]) for sub in semis]

    @lazy_attribute
    def nonsplit_products(self):
        nonsplit = []
        count = Counter()
        for sub in self.subgroups.values():
            if sub.normal and not sub.split:
                pair = (sub.subgroup, sub.quotient)
                if pair not in count:
                    nonsplit.append(sub)
                count[pair] += 1
        nonsplit.sort(key=product_sort_key)
        return [(sub, count[sub.subgroup, sub.quotient]) for sub in nonsplit]


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
        sm_list = self.schur_multiplier 
        elements_count = {}
        entries = []
        if len(sm_list)==0:
    	    entries.append("C_1")
        for element in sm_list:
            if element in elements_count:
                elements_count[element] += 1
            else:
                elements_count[element] = 1
        for key, value in elements_count.items():
            entry = ""
            if key != 1:
                entry = entry + "C_{" + str(key) + "}"
                if value != 1:
                    entry = entry + "^{" + str(value) + "}" 
            entries.append(entry)
        prod = "\\times ".join(entries)
        return prod
        #return "trivial" if self.schur_multiplier == [] else self.schur_multiplier
    def schur_multiplier_label(self):
        sm_list = self.schur_multiplier
        str1 = '.'.join(str(e) for e in sm_list)
        return str1
        #return ".".join(map(str, sm_list))


    @lazy_attribute
    def irrep_stats(self):
        return sorted(Counter([rep.dim for rep in self.characters]).items())

        

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

    ###automorphism group
    def show_aut_group(self):
        if self.aut_group is None:
            return r'\textrm{Not computed}'
        else:
            return group_names_pretty(self.aut_group)

    #TODO if prime factors get large, use factors in database
    def aut_order_factor(self):
        return factor(int(self._data['aut_order']))

    ###outer automorphism group
    def show_outer_group(self):
        if self.outer_group is None:
            return r'\textrm{Not computed}'
        else:
            return group_names_pretty(self.outer_group)

    def out_order(self):
        return int(self._data['outer_order'])

    #TODO if prime factors get large, use factors in database
    def out_order_factor(self):
        return factor(int(self._data['outer_order']))

    ###special subgroups
    def cent(self):
        return self.special_search('Z')

    def cent_label(self):
        return self.subgroups[self.cent()].subgroup_tex

    def central_quot(self):
        return self.subgroups[self.cent()].quotient_tex

    def cent_order_factor(self):
        return (self.order // ZZ(self.comm().split('.')[2])).factor()

    def comm(self):
        return self.special_search('D')

    def comm_label(self):
        return self.subgroups[self.comm()].subgroup_tex

    def abelian_quot(self):
        return self.subgroups[self.comm()].quotient_tex

    def Gab_order_factor(self):
        return ZZ(self._data['abelian_quotient'].split('.')[0]).factor()

    def fratt(self):
        return self.special_search('Phi')

    def fratt_label(self):
        return self.subgroups[self.fratt()].subgroup_tex

    def frattini_quot(self):
        return self.subgroups[self.fratt()].quotient_tex

    @lazy_attribute
    def max_sub_cnt(self):
        return db.gps_subgroups.count_distinct('ambient', {'subgroup': self.label, 'maximal': True})

    @lazy_attribute
    def max_quo_cnt(self):
        return db.gps_subgroups.count_distinct('ambient', {'quotient': self.label, 'minimal_normal': True})

    @staticmethod
    def sparse_cyclotomic_to_latex(n, dat):
        # The indirection is because we want to make this a staticmethod
        return sparse_cyclotomic_to_latex(n, dat)

class WebAbstractSubgroup(WebObj):
    table = db.gps_subgroups
    def __init__(self, label, data=None):
        WebObj.__init__(self, label, data)
        s = self.subgroup_tex
        self.subgroup_tex_parened = s if self._is_atomic(s) else "(%s)" % s
        if self._data.get('quotient'):
            q = self.quotient_tex
            self.quotient_tex_parened = q if self._is_atomic(q) else "(%s)" % q

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

    def show_special_labels(self):
        raw = [x.split('.')[-1] for x in self.special_labels]
        specials = []
        for x in raw:
            if x == 'Z':
                specials.append(display_knowl('group.center', 'center'))
            elif x == 'D':
                specials.append(display_knowl('group.commutator_subgroup', 'commutator subgroup'))
            elif x == 'F':
                specials.append(display_knowl('group.fitting_subgroup', 'Fitting subgroup'))
            elif x == 'Phi':
                specials.append(display_knowl('group.frattini_subgroup', 'Frattini subgroup'))
            elif x == 'R':
                specials.append(display_knowl('group.radical', 'radical'))
            elif x == 'S':
                specials.append(display_knowl('group.socle', 'socle'))
            else:
                n = to_ordinal(int(x[1:]) + 1)
                if x.startswith('U'):
                    specials.append('%s term in the %s' % (n, display_knowl('group.upper_central_series', 'upper central series')))
                elif x.startswith('L'):
                    specials.append('%s term in the %s' % (n, display_knowl('group.lower_central_series', 'lower central series')))
                elif x.startswith('D'):
                    specials.append('%s term in the %s' % (n, display_knowl('group.derived_series', 'derived series')))
                # Don't show chief series since it's not canonical
        if self.sylow:
            specials.append(display_knowl("group.sylow_subgroup", "%s-Sylow subgroup" % self.sylow))
        return ', '.join(specials)

    def _lookup(self, label, data, Wtype):
        for rec in data:
            if rec['label'] == label:
                return Wtype(label, rec)

    @lazy_attribute
    def _full(self):
        """
        Get information from gps_groups for each of the abstract groups included here (the subgroup, the ambient group and the quotient, if normal)
        """
        labels = [self.subgroup, self.ambient]
        if self.normal:
            labels.append(self.quotient)
        return list(db.gps_groups.search({'label': {'$in': labels}}))

    @lazy_attribute
    def sub(self):
        return self._lookup(self.subgroup, self._full, WebAbstractGroup)

    @lazy_attribute
    def amb(self):
        return self._lookup(self.ambient, self._full, WebAbstractGroup)

    @lazy_attribute
    def quo(self):
        return self._lookup(self.quotient, self._full, WebAbstractGroup)

    @lazy_attribute
    def _others(self):
        """
        Get information from gps_subgroups for each of the other subgroups referred to (centralizer, complements, contained_in, contains, core, normal_closure, normalizer)
        """
        labels = []
        for label in [self.centralizer, self.core, self.normal_closure, self.normalizer]:
            if label:
                labels.append(label)
        for llist in [self.complements, self.contained_in, self.contains]:
            if llist:
                labels.extend(llist)
        return list(db.gps_subgroups.search({'label': {'$in': labels}}))

    @lazy_attribute
    def centralizer_(self):
        return self._lookup(self.centralizer, self._others, WebAbstractSubgroup)

    @lazy_attribute
    def core_(self):
        return self._lookup(self.core, self._others, WebAbstractSubgroup)

    @lazy_attribute
    def normal_closure_(self):
        return self._lookup(self.normal_closure, self._others, WebAbstractSubgroup)

    @lazy_attribute
    def normalizer_(self):
        return self._lookup(self.normalizer, self._others, WebAbstractSubgroup)

    @lazy_attribute
    def complements_(self):
        if self.complements is None:
            return None
        return [self._lookup(H, self._others, WebAbstractSubgroup) for H in self.complements]

    @lazy_attribute
    def contained_in_(self):
        if self.contained_in is None:
            return None
        return [self._lookup(H, self._others, WebAbstractSubgroup) for H in self.contained_in]

    @lazy_attribute
    def contains_(self):
        if self.contains is None:
            return None
        return [self._lookup(H, self._others, WebAbstractSubgroup) for H in self.contains]

# Conjugacy class labels do not contain the group
class WebAbstractConjClass(WebObj):
    table = db.gps_groups_cc
    def __init__(self, ambient_gp, label, data=None):
        self.ambient_gp = ambient_gp
        if data is None:
            data = db.gps_groups_cc.lucky({'group': ambient_gp, 'label': label})
        WebObj.__init__(self, label, data)

    def display_knowl(self, name=None):
        if not name:
            name = self.label
        return '<a title = "{} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=cc_data&args={}%7C{}%7Ccomplex">{}</a>'.format(name, self.ambient_gp, self.label, name)

class WebAbstractDivision(object):
    def __init__(self, ambient_gp, label, classes):
        self.ambient_gp = ambient_gp
        self.label = label
        self.classes = classes

    def display_knowl(self, name=None):
        if not name:
            name = self.label
        return '<a title = "{} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=cc_data&args={}%7C{}%7Crational">{}</a>'.format(name, self.ambient_gp, self.label, name)

class WebAbstractCharacter(WebObj):
    table = db.gps_char
    def type(self):
        if self.indicator == 0:
            return "C"
        if self.indicator > 0:
            return "R"
        return "S"

    def display_knowl(self, name=None):
        label = self.label
        if not name:
            name = label
        return '<a title = "%s [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=cchar_data&args=%s">%s</a>' % (name, label, name)



class WebAbstractRationalCharacter(WebObj):
    table = db.gps_qchar
    def display_knowl(self, name=None):
        label = self.label
        imagelabel = self.image
        if not name:
            name = label
        return '<a title = "%s [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=rchar_data&args=%s">%s</a>' % (name, label, name)

class WebAbstractSupergroup(WebObj):
    table = db.gps_subgroups
    def __init__(self, sub_or_quo, typ, label, data=None):
        self.sub_or_quo_gp = sub_or_quo
        self.typ = typ
        WebObj.__init__(self, label, data)
