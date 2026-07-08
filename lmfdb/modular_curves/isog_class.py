from flask import url_for
from lmfdb.utils import prop_int_pretty
from lmfdb.modular_curves.web_curve import modcurve_link, ISO_CLASS_RE, WebModCurve
from lmfdb import db

from sage.databases.cremona import class_to_int, cremona_letter_code

class ModCurveIsog_class():
    """
    Class for a Gassmann class of modular curves over Q
    """
    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        self.__dict__.update(dbdata)
        self.web_curve = WebModCurve(self.label)
        self.make_class()

    @staticmethod
    def by_label(label):
        """
        Searches for a specific modular curve Gassmann class in the
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
                # !!! Do we have other labels for which the label remembers the Gassmann class?
            except AttributeError:
                return "Invalid label" # caller must catch this and raise an error

        if data:
            return ModCurveIsog_class(data)
        return "Class not found" # caller must catch this and raise an error

    def make_class(self):
        # Extract the size of the Gassmann class from the database
        # !!! Do we want to add a table for the Gassmann classes?
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
            query.update({number_key : i+1})
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
                           ('Level', prop_int_pretty(self.coarse_level)),
                           ('Index', prop_int_pretty(self.coarse_index)),
                           ('Genus', prop_int_pretty(self.genus)),
                           ('Cusps', prop_int_pretty(self.cusps))
                           ]

        if self.conductor is not None:
            self.properties.append(('Conductor', '$' + self.web_curve.factored_conductor + '$'))
        if self.rank is not None:
            self.properties.append(('Analytic rank', prop_int_pretty(self.rank)))

        self.friends = self.web_curve.friends[1:]

        self.title = "Gassmann class with LMFDB label " + self.coarse_class
        base_query = url_for("modcurve.index")
        level_query = '?level=%s' % self.coarse_level
        index_query = level_query + '&index=%s' % self.coarse_index
        genus_query = index_query + '&genus=%s' % self.genus

        self_query = genus_query + '&coarse_class_num=%s' % self.coarse_class_num
        curves_query = self_query + '&contains_negative_one=yes'

        self.downloads = [
            (
                "Code to magma",
                url_for(".modcurve_Gassmann_magma_download") + curves_query
            ),
            (
                "Code to sage",
                url_for(".modcurve_Gassmann_sage_download") + curves_query
            ),
            (
                "All data to text",
                url_for(".modcurve_Gassmann_text_download") + curves_query
            ),
            (
                'Underlying data',
                url_for(".modcurve_data", label=self.coarse_class),
            )
        ]

        self.bread = [('Modular curves', base_query),
                      (r'$\Q$', base_query),
                      ('%s' % self.coarse_level, base_query + level_query),
                      ('%s' % self.coarse_index, base_query + index_query),
                      ('%s' % self.genus, base_query + genus_query),
                      ('%s' % cremona_letter_code(self.coarse_class_num-1), base_query + self_query)]
