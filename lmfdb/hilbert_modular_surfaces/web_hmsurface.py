# -*- coding: utf-8 -*-

from collections import Counter
from flask import url_for

from sage.all import lazy_attribute #, prod, euler_phi, ZZ, QQ, latex, PolynomialRing, lcm, NumberField, FractionField
from lmfdb.utils import WebObj #, integer_prime_divisors, teXify_pol, web_latex, pluralize
from lmfdb import db
from lmfdb.number_fields.number_field import url_for_label as url_for_NF_label
from string import ascii_lowercase

def get_bread(tail=[]):
    base = [("Hilbert modular surfaces", url_for(".index")), (r"$\Q$", url_for(".index_Q"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

def modcurve_link(label):
    return '<a href="%s">%s</a>'%(url_for(".by_label",label=label),label)

class WebHMSurface(WebObj):
    table = db.hmsurfaces_invs

    @lazy_attribute
    def properties(self):
        props = [
            ("Label", self.label),
        ]
        return props

    @lazy_attribute
    def friends(self):
        friends = []
        return friends

    @lazy_attribute
    def bread(self):
        tail = []
        return get_bread(tail)

    @lazy_attribute
    def title(self):
        return f"Hilbert modular surface {self.label}"

    #Cusp display

    @lazy_attribute
    def downloads(self):
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
        return self.downloads
