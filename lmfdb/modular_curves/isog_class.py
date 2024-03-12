# -*- coding: utf-8 -*-
from flask import url_for
from lmfdb.utils import encode_plot, prop_int_pretty, raw_typeset, integer_squarefree_part
from lmfdb.modular_curves import modcurve_logger
from lmfdb.modular_curves.web_curve import modcurve_link, ISO_CLASS_RE, WebModCurve
from lmfdb.number_fields.web_number_field import field_pretty
from lmfdb import db

from sage.databases.cremona import cremona_letter_code, class_to_int

from sage.all import latex, PowerSeriesRing, QQ, ZZ, RealField, lazy_attribute, lcm

class ModCurveIsog_class():
    """
    Class for an isogeny class of modular curves over Q
    """
    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        modcurve_logger.debug("Constructing an instance of ModCurveIsog_class")
        self.__dict__.update(dbdata)
        self.web_curve = WebModCurve(self.label)
        self.make_class()
        
    @staticmethod
    def by_label(label):
        """
        Searches for a specific modular curve isogeny class in the
        curves collection by its label, which can be either a curve
        label (e.g. "11.12.1.a.1") or a class label (e.g. "11.12.1.a") in
        LMFDB format.
        """
        try:
            # !!! Right now only handling coarse labels, add support for fine labels
            if not ISO_CLASS_RE.fullmatch(label):
                return "Invalid label"
            
            N, i, g, iso = label.split(".")
            iso_num = class_to_int(iso)+1
            data = db.gps_gl2zhat_fine.lucky({"coarse_level" : N,
                                              "coarse_index" : i,
                                              "genus" : g,
                                              "coarse_class_num" : iso_num})
            if data is None:
                return "Class not found"
            data['label_type'] = 'LMFDB'
            
        except AttributeError:
            try:
                if not ISO_CLASS_RE.fullmatch(label):
                    return "Invalid label"
                # !!! Do we have other labels for which the label remembers the isogeny class?
            except AttributeError:
                return "Invalid label" # caller must catch this and raise an error

        if data:
            return ModCurveIsog_class(data)
        return "Class not found" # caller must catch this and raise an error

    def make_class(self):
        # Extract the size of the isogeny class from the database
        # !!! Do we want to add a table for the isogeny classes?
        # classdata = db.ec_classdata.lucky({'lmfdb_iso': self.lmfdb_iso})
        # self.class_size = ncurves = classdata['class_size']

        query = {'coarse_level' : self.coarse_level,
                 'coarse_index' : self.coarse_index,
                 'genus' : self.genus,
                 'coarse_class_num' : self.coarse_class_num,
                 'contains_negative_one' : True}
        
        self.class_size = ncurves = db.gps_gl2zhat_fine.count(query)
        
        # Create a list of the curves in the class from the database
        number_key = 'coarse_num'
        self.curves = []
        for i in range(ncurves):
            query.update({'coarse_num' : i+1})
            self.curves.append(db.gps_gl2zhat_fine.lucky(query))
            
        for c in self.curves:
            c['web_curve'] = WebModCurve(c['label'])
            c['curve_url_lmfdb'] = modcurve_link(c['label'])
            c['curve_label'] = c['label']
            if c['CPlabel'] is not None:
                self.CPlabel = True
            if c['RSZBlabel'] is not None:
                self.RSZBlabel = True
            if c['RZBlabel'] is not None:
                self.RZBlabel = True
            if c['SZlabel'] is not None:
                self.SZlabel = True
            if c['Slabel'] is not None:
                self.Slabel = True
            if c['name'] is not None:
                self.name = True

        self.properties = [('Label', self.coarse_class),
                           ('Number of curves', prop_int_pretty(ncurves)),
                           ('Level',  prop_int_pretty(self.coarse_level)),
                           ('Index',  prop_int_pretty(self.coarse_index)),
                           ('Genus',  prop_int_pretty(self.genus)),
                           ('Cusps',  prop_int_pretty(self.cusps))
                           ]
        
        self.friends = self.web_curve.friends

        self.title = "Isogney class of modular curves with LMFDB label " + self.coarse_label

        self.downloads = [
            (
                "Code to Magma",
                url_for(".modcurve_magma_download", label=self.label),
            ),
            (
                "Code to SageMath",
                url_for(".modcurve_sage_download", label=self.label),
            ),
            (
                "All data to text",
                url_for(".modcurve_text_download", label=self.label),
            ),
            (
                'Underlying data',
                url_for(".modcurve_data", label=self.label),
            )

        ]

        self.bread = [('Modular curves', url_for("modcurve.index")),
                      ('%s' % self.coarse_label, ' ')]
