# -*- coding: utf-8 -*-

from pymongo import ASCENDING
from ast import literal_eval
from lmfdb.base import getDBConnection
from lmfdb.utils import web_latex, encode_plot
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.WebNumberField import nf_display_knowl, WebNumberField
from lmfdb.transitive_group import group_display_knowl
from sage.all import latex, ZZ, QQ, CC, NumberField, PolynomialRing, factor, implicit_plot, point, real, sqrt, var, expand, nth_prime
from sage.plot.text import text
from flask import url_for


###############################################################################
# Database connection -- all access to mongo db should happen here
###############################################################################

def belyi_db_galmaps():
    return getDBConnection().belyi.galmaps

def belyi_db_passports():
    return getDBConnection().belyi.passports


###############################################################################
# Pretty print functions
###############################################################################



###############################################################################
# Belyi map class definitions
###############################################################################

class WebBelyiGalmap(object):
    """
    Class for a Belyi map.  Attributes include:
        data -- information about the map to be displayed
        plot -- currently empty
        properties -- information to be displayed in the properties box (including link plot if present)
        friends -- labels of related objects
        code -- code snippets for relevant attributes in data
        bread -- bread crumbs for home page
        title -- title to display on home page
    """
    def __init__(self, galmap):
        self.make_galmap_object(galmap)

    @staticmethod
    def by_label(label):
        """
        Searches for a specific Belyi map in the galmaps collection by its label.
        If label is for a passport, constructs an object for an arbitrarily chosen galmap in the passport
        Constructs the WebBelyiGalmap object if found, raises an error otherwise
        """
        try:
            slabel = label.split("-")
            if len(slabel) == 6:
                galmap = belyi_db_galmaps().find_one({"plabel" : label})
            elif len(slabel) == 7:
                galmap = belyi_db_galmaps().find_one({"label" : label})
            else:
                raise ValueError("Invalid Belyi map label %s." % label)
        except AttributeError:
            raise ValueError("Invalid Belyi map label %s." % label)
        if not galmap:
            if len(slabel) == 6:
                raise KeyError("Belyi map passport label %s not found in the database." % label)
            else:
                raise KeyError("Belyi map %s not found in database." % label)
        return WebBelyiGalmap(galmap)

    def make_galmap_object(self, galmap):
        from lmfdb.belyi.main import url_for_belyi_galmap_label
        from lmfdb.belyi.main import url_for_belyi_passport_label

        # all information about the map goes in the data dictionary
        # most of the data from the database gets polished/formatted before we put it in the data dictionary
        data = self.data = {}

        data['label'] = galmap['label']
        slabel = data['label'].split("-")
        data['plabel'] = galmap['plabel']

        data['triples'] = galmap['triples']
        F = WebNumberField.from_coeffs(galmap['base_field'])
        F.latex_poly = web_latex(F.poly())
#        data['base_field'] = galmap['base_field']
        data['base_field'] = F
        data['embeddings'] = galmap['embeddings']
        X = web_latex(galmap['curve'])
        data['curve'] = X
#        data['curve'] = galmap['curve']
        data['map'] = galmap['map']
        data['orbit_size'] = galmap['orbit_size']

        # Properties
        self.properties = properties = [('Label', data['label'])]
        properties += [
            ]

        # Friends
        self.friends = friends = [('Passport', url_for_belyi_passport_label(galmap['plabel']))]

        # Breadcrumbs
        self.bread = bread = [
             ('Belyi Maps', url_for(".index")),
#              ('%s' % slabel[0], url_for(".by_group", group=slabel[0])),
#              ('%s' % slabel[1], url_for(".by_abc", group=slabel[0], abc=slabel[1])),
#              ('%s' % slabel[2], url_for(".by_sigma0", group=slabel[0], abc=slabel[1], sigma0=slabel[2])),
#              ('%s' % slabel[3], url_for(".by_sigma1", group=slabel[0], abc=slabel[1], sigma0=slabel[2], sigma1=slabel[3])),
#              ('%s' % slabel[4], url_for(".by_sigmaoo", group=slabel[0], abc=slabel[1], sigma0=slabel[2], sigma1=slabel[3], sigmaoo=slabel[4])),
#              ('%s' % slabel[5], url_for(".by_url_belyi_passport_label", group=slabel[0], abc=slabel[1], sigma0=slabel[2], sigma1=slabel[3], sigmaoo=slabel[4], g=slabel[5])),
#              ('%s' % slabel[6], url_for(".by_url_belyi_galmap_label", group=slabel[0], abc=slabel[1], sigma0=slabel[2], sigma1=slabel[3], sigmaoo=slabel[4], g=slabel[5], letnum=slabel[6]))
             ]

        # Title
        self.title = "Belyi map " + data['label']

        # Code snippets (only for curves)
        self.code = code = {}
        return

class WebBelyiPassport(object):
    """
    Class for a Belyi passport.  Attributes include:
        data -- information about the map to be displayed
        plot -- currently empty
        properties -- information to be displayed in the properties box (including link plot if present)
        friends -- labels of related objects
        code -- code snippets for relevant attributes in data, currently empty
        bread -- bread crumbs for home page
        title -- title to display on home page
    """
    def __init__(self, passport):
        self.make_passport_object(passport)

    @staticmethod
    def by_label(label):
        """
        Searches for a specific passport in the passports collection by its label.
        Constructs the WebBelyiPassport object if found, raises an error otherwise
        """
        try:
            slabel = label.split("-")
            if len(slabel) == 6:
                passport = belyi_db_passports().find_one({"plabel" : label})
            else:
                raise ValueError("Invalid Belyi passport label %s." % label)
        except AttributeError:
            raise ValueError("Invalid passport label %s." % label)
        if not passport:
            raise KeyError("Passport %s not found in database." % label)
        return WebBelyiPassport(passport)

    def make_passport_object(self, passport):
        # all information about the map goes in the data dictionary
        # most of the data from the database gets polished/formatted before we put it in the data dictionary
        data = self.data = {}

        data['plabel'] = passport['plabel']
        slabel = data['plabel'].split("-")

        data['deg'] = passport['deg']
        data['group'] = passport['group']
        data['aut_group'] = passport['aut_group']
        data['geomtype'] = passport['geomtype']
        data['abc'] = passport['abc']
        data['lambdas'] = passport['lambdas']
        data['g'] = passport['g']
        data['maxdegbf'] = passport['maxdegbf']
        data['pass_size'] = passport['pass_size']
        data['num_orbits'] = passport['num_orbits']

        # Properties
        self.properties = properties = [('Label', data['plabel'])]
        properties += [
            ]

        # Friends
        self.friends = friends = []

        # Breadcrumbs
        self.bread = bread = [
             ('Belyi Maps', url_for(".index")),
#              ('%s' % slabel[0], url_for(".by_group", group=slabel[0])),
#              ('%s' % slabel[1], url_for(".by_abc", group=slabel[0], abc=slabel[1])),
#              ('%s' % slabel[2], url_for(".by_sigma0", group=slabel[0], abc=slabel[1], sigma0=slabel[2])),
#              ('%s' % slabel[3], url_for(".by_sigma1", group=slabel[0], abc=slabel[1], sigma0=slabel[2], sigma1=slabel[3])),
#              ('%s' % slabel[4], url_for(".by_sigmaoo", group=slabel[0], abc=slabel[1], sigma0=slabel[2], sigma1=slabel[3], sigmaoo=slabel[4])),
#              ('%s' % slabel[5], url_for(".by_url_belyi_passport_label", group=slabel[0], abc=slabel[1], sigma0=slabel[2], sigma1=slabel[3], sigmaoo=slabel[4], g=slabel[5])),
#              ('%s' % slabel[6], url_for(".by_url_belyi_galmap_label", group=slabel[0], abc=slabel[1], sigma0=slabel[2], sigma1=slabel[3], sigmaoo=slabel[4], g=slabel[5], letnum=slabel[6]))
             ]

        # Title
        self.title = "Passport " + data['plabel']

        # Code snippets (only for curves)
        self.code = code = {}
        return
