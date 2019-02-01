# -*- coding: utf-8 -*-

# Class created to aid in uploading HMF data from the Magma output data files.
# Incomplete, and currently not used for real work.
#
# In particular this code assumes that all the data for one HMF is in
# a single collection, which is no longer the case.

from sage.all import QQ, polygen

from lmfdb.db_backend import db
from lmfdb.hilbert_modular_forms.hilbert_field import HilbertNumberField
from lmfdb.utils import make_logger

logger = make_logger("hmf")

def construct_full_label(field_label, weight, level_label, label_suffix):
    if all([w==2 for w in weight]):           # Parellel weight 2
        weight_label = ''
    elif all([w==weight[0] for w in weight]): # Parellel weight
        weight_label = str(weight[0]) + '-'
    else:                                     # non-parallel weight
        weight_label = str(weight) + '-'
    return ''.join([field_label, '-', weight_label, level_label, '-', label_suffix])


class WebHMF(object):
    """
    Class for an Hilbert Modular Newform
    """
    def __init__(self, dbdata=None, label_or_field=None, L=None):
        """Arguments:

            - dbdata: the data from the database

            - label_or_field: a field label OR a HilbertNumberFIeld

            - L: a string representing one newform from a raw data file

        If dbdata is not None then it is expected to be a database
        entry from which the class is initialised.  If dbdata is None,
        then a form is constructed from the field label or field and
        data string given.

        """
        if dbdata:
            logger.debug("Constructing an instance of WebHMF class from database")
            self.__dict__.update(dbdata)
            self.dbdata = dbdata
        else:
            self.create_from_data_string(label_or_field,L)
        # All other fields are handled here
        self.make_form()

    @staticmethod
    def by_label(label):
        """
        Searches for a specific Hilbert newform in the forms
        collection by its label.
        """
        data = db.hmf_forms.lookup(label)

        if data:
            return WebHMF(data)
        raise ValueError("Hilbert newform %s not found" % label)
        # caller must catch this and raise an error

    def create_from_data_string(self, label_or_field, L):
        """Takes an input line L from a raw data file and constructs the
        associated HMF object with given base field.

        String sample:
        <[31, 31, w + 12], "a", [-3, -2, 2, 4, -4, ...]>,
        """
        data = self.dbdata = {}
        if isinstance(label_or_field, str):
            label = label_or_field
            data['field_label'] = label
            F = HilbertNumberField(label)
            if not F:
                raise ValueError("No Hilbert number field with label %s is in the database" % label)
        elif label_or_field == None:
            raise ValueError("Must specify a valid field label")
        else: # we were passed a HilbertNumberField already
            F = label_or_field
            data['field_label'] = F.label
        #print("data['field_label'] = %s" % data['field_label'])

        # The level

        i = L.find('[')
        j = L.find(']')
        data['level_ideal'] = L[i:j+1]
        #print("data['level_ideal'] = %s" % data['level_ideal'])
        N, n, alpha = data['level_ideal'][1:-1].split(',')
        data['level_norm'] = int(N)
        #print("data['level_norm'] = %s" % data['level_norm'])
        level = F.ideal_from_str(data['level_ideal'])[2]
        #print("level = %s" % level)
        data['level_label'] = F.ideal_label(level)
        #print("data['level_label'] = %s" % data['level_label'])

        # The weight

        data['parallel_weight'] = int(2)
        data['weight'] = str([data['parallel_weight']] * F.degree())
        weight = [2] * F.degree()

        # The label

        i = L.find('"')
        j = L.find('"', i+1)
        data['label_suffix'] = L[i+1:j].replace(" ","")

        data['label'] = construct_full_label(data['field_label'],
                                             weight,
                                             data['level_label'],
                                             data['label_suffix'])
        data['short_label'] = '-'.join([data['level_label'], data['label_suffix']])
        #print("data['label'] = %s" % data['label'] )
        #print("data['short_label'] = %s" % data['short_label'] )

        # The hecke polynomial and degree

        if 'x' in L:
            # non-rational
            i = L.find("x")
            j = L.find(i+1,",")
            data['hecke_polynomial'] = pol = L[i:j]
            data['dimension'] = int(1)
            x = polygen(QQ)
            hpol = x.parent()(str(pol))
            data['dimension'] = int(hpol.degree())
        else:
            # rational
            data['hecke_polynomial'] = 'x'
            data['dimension'] = int(1)

        i = L.rfind("[")
        j = L.rfind("]")
        data['hecke_eigenvalues'] = L[i+1:j].replace(" ","").split(",")
        data['hecke_eigenvalues'] = [unicode(s) for s in data['hecke_eigenvalues']]
        #print("hecke_eigenvalues = %s..." % data['hecke_eigenvalues'][:20])

        # Find (some of the) AL-eigenvalues

        BP = level.prime_factors()
        BP_indices = [F.prime_index(P) for P in BP]
        print("BP_indices = %s" % BP_indices)
        BP_exponents = [level.valuation(P) for P in BP]
        #print("BP_exponents = %s" % BP_exponents)
        AL_eigs = [int(data['hecke_eigenvalues'][k]) for k in BP_indices]
        #print("AL_eigs      = %s" % AL_eigs)
        if not all([(e==1 and eig in [-1,1]) or (eig==0)
                    for e,eig in zip(BP_exponents,AL_eigs)]):
            print("Some bad AL-eigenvalues found")
        # NB the following will put 0 for the eigenvalue for primes
        # whose quare divides the level; this will need fixing later.
        data['AL_eigenvalues'] = [[F.primes[k],data['hecke_eigenvalues'][k]] for k in BP_indices]

        data['is_CM'] = '?'
        data['is_base_change'] = '?'


    def compare_with_db(self, field=None):
        lab = self.dbdata['label']
        f = WebHMF.by_label(lab)
        if f==None:
            print("No Hilbert newform in the database has label %s" % lab)
            return False
        if field==None:
            field = HilbertNumberField(self.dbdata['field_label'])
        agree = True
        for key in self.dbdata.keys():
            if key in ['is_base_change', 'is_CM']:
                continue
            if key=='hecke_eigenvalues':
                if self.dbdata[key]!=f.dbdata[key]:
                    agree = False
                    print("Inconsistent data for HMF %s in field %s" % (lab,key))
                    print("self has %s entries, \ndb   has %s entries" % (len(self.dbdata[key]),len(f.dbdata[key])))
                    print("Entries differ at indices %s" % [i for i in range(len(self.dbdata[key])) if self.dbdata[key][i]!=f.dbdata[key][i]])
            elif key=='level_ideal':
                if self.dbdata[key]!=f.dbdata[key]:
                    I = field.ideal_from_str(f.dbdata['level_ideal'])[2]
                    J = field.ideal_from_str(self.dbdata['level_ideal'])[2]
                    if I==J:
                        print("OK, these are the same ideal")
                    else:
                        agree = False
                        print("These are different ideals!")

            else:
                if self.dbdata[key]!=f.dbdata[key]:
                    agree = False
                    print("Inconsistent data for HMF %s in field %s" % (lab,key))
        return agree

    def make_form(self):
        # To start with the data fields of self are just those from
        # the database.  We need to reformat these and compute some
        # further (easy) data about it.
        #
        pass
