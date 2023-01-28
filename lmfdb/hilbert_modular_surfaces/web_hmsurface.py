# -*- coding: utf-8 -*-

from collections import Counter
from flask import url_for

from sage.all import lazy_attribute, ZZ #, prod, euler_phi, ZZ, QQ, latex, PolynomialRing, lcm, NumberField, FractionField
from lmfdb.utils import WebObj #, integer_prime_divisors, teXify_pol, web_latex, pluralize
from lmfdb import db
from lmfdb.number_fields.number_field import url_for_label as url_for_NF_label
from string import ascii_lowercase

def get_bread(tail=[]):
    base = [("Hilbert modular surfaces", url_for(".index")), (r"$\Q$", url_for(".index_Q"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

def hmsurface_link(label):
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

    @lazy_attribute
    def field_label(self):
        field, level, comp, _, _ = self.label.split("-")
        return field

    @lazy_attribute
    def level_label(self):        
        field, level, comp, _, _ = self.label.split("-")
        return level
    
    @lazy_attribute
    def component_label(self):        
        field, level, comp, _, _ = self.label.split("-")
        return comp

    @lazy_attribute
    def formatted_field(self):
        field_degree = ZZ(self.field_label.split(".")[0])
        field_discr_str = self.field_label.split(".")[2]
        link_str = f'<a href="{url_for_NF_label(self.field_label)}">{self.field_label}</a>'
        if field_degree == 2:
            return r'$\Q(\sqrt{' + field_discr_str + '})$  (' + link_str + ')'
        else:
            return link_str

    @lazy_attribute
    def formatted_subgroup_type(self):
        _, _, _, ambient, gammatype = self.label.split("-")
        if ambient == "sl":
            G = r"\Gamma^1"
        elif ambient == "gl":
            G = r"\Gamma"
        else:
            raise ValueError("Ambient type not recognized: " + ambient)
        if gammatype == "0":
            sub = "_0"
        elif gammatype == "1":
            sub = "_1"
        elif gammatype == "f":
            sub = ""
        else:
            raise ValueError("Gamma type not recognized: " + gammatype)
        return G + sub + r"(\mathfrak{N})_{\mathfrak{b}}"

    @lazy_attribute
    def formatted_level(self):
        return self.level_label

    @lazy_attribute
    def formatted_component(self):
        return self.component_label

    @lazy_attribute
    def level_norm(self):
        return ZZ(self.level_label.split(".")[0])    
            
    #Cusp display

    @lazy_attribute
    def downloads(self):
        self.downloads = [
            (
                "Code to Magma",
                url_for(".hmsurface_magma_download", label=self.label),
            ),
            (
                "Code to SageMath",
                url_for(".hmsurface_sage_download", label=self.label),
            ),
            (
                "All data to text",
                url_for(".hmsurface_text_download", label=self.label),
            ),
            (
                'Underlying data',
                url_for(".hmsurface_data", label=self.label),
            )

        ]
        return self.downloads
