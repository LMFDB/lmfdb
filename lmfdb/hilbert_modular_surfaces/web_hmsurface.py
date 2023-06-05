# -*- coding: utf-8 -*-

from flask import url_for

from sage.all import (
    lazy_attribute,
    ZZ,
    latex,
)  # , prod, euler_phi, ZZ, QQ, latex, PolynomialRing, lcm, NumberField, FractionField
from lmfdb.utils import (
    WebObj,
)  # , integer_prime_divisors, teXify_pol, web_latex, pluralize
from lmfdb import db
from lmfdb.number_fields.web_number_field import WebNumberField


def get_bread(tail=[]):
    base = [
        ("Hilbert modular surfaces", url_for(".index")),
        (r"$\Q$", url_for(".index_Q")),
    ]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail


def hmsurface_link(label):
    return '<a href="%s">%s</a>' % (url_for(".by_label", label=label), label)


def hmsurface_format_cusp(cusp, w):
    [xa, ya] = cusp["coordinates"][0]
    [xc, yc] = cusp["coordinates"][1]
    a = latex(ZZ(xa) + ZZ(ya) * w)
    c = latex(ZZ(xc) + ZZ(yc) * w)
    res = (
        cusp["M_label"],
        a,
        c,
        cusp["self_intersections_minimal"],
        cusp["repetition"],
    )
    return res


def hmsurface_format_ideal_generators(gens, w):
    L = []
    for g in gens:
        [x, y] = g
        a = latex(ZZ(x) + ZZ(y) * w)
        L.append(a)
    return "(" + ", ".join(L) + ")"


def hmsurface_format_elliptic_pt(pt):
    [n, a, b] = pt["rotation_type"]
    return ("[{};{},{}]".format(n, a, b), pt["nb"])


class WebHMSurface(WebObj):
    table = db.hmsurfaces_invs

    @lazy_attribute
    def properties(self):
        props = [
            ("Label", self.label),
            ("Field discriminant", str(self.field_discr)),
            ("Level norm", str(self.level_norm)),
            ("Group type", "${{" + str(self.formatted_subgroup_type) + "}}$"),
        ]
        if self.image is not None:
            props.append((None, self.image))
        if self.kodaira_is_known:
            props.append(("Kodaira dimension", str(self.kodaira_dims[0])))
        props.append(("Cusps", str(self.nb_cusps)))
        props.append(("Elliptic points", str(self.nb_elliptic_pts)))
        return props

    @lazy_attribute
    def image(self):
        return (
            f"""<table>
        <tr> <td></td><td>
          </td><td align="center"> $1$ </td><td></td><td></td></tr>
        <tr> <td></td>
            <td align="center"> $0$ </td><td></td><td align="center"> $0$ </td><td></td></tr>
        <tr> <td align="center">
            ${self.h20}$
        </td><td></td>
            <td align="center">
            ${self.h11}$
        </td>
            <td></td><td align="center">
            ${self.h20}$
            </td></tr>
        <tr> <td></td>
            <td align="center"> $0$ </td><td></td><td align="center"> $0$ </td><td></td></tr>
        <tr> <td></td><td></td><td align="center"> $1$ </td><td></td><td></td></tr>
    </table>"""
        )

    @lazy_attribute
    def friends(self):
        friends = []
        # Other components
        if self.narrow_class_nb > 1:
            for r in self.table.search(
                {
                    "field_label": self.field_label,
                    "level_label": self.level_label,
                    "gamma_type": self.gamma_type,
                    "group_type": self.group_type,
                },
                ["label"],
            ):
                if r["label"] != self.label:
                    friends.append(
                        (
                            "Other component " + r["label"],
                            url_for("hmsurface.by_label", label=r["label"]),
                        )
                    )
        # Level one
        friendlabel = (
            self.field_label
            + "-1.1-"
            + self.component_label
            + "-"
            + self.group_type
            + "-"
            + self.gamma_type
        )
        friends.append(
            (
                "Level one surface " + friendlabel,
                url_for("hmsurface.by_label", label=friendlabel),
            )
        )
        # SL/GL
        friendlabel = (
            self.field_label
            + "-"
            + self.level_label
            + "-"
            + self.component_label
            + "-"
            + ("gl" if self.group_type == "sl" else "sl")
            + "-"
            + self.gamma_type
        )
        friends.append(
            (
                "Hilbert surface " + friendlabel,
                url_for("hmsurface.by_label", label=friendlabel),
            )
        )
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
        return (
            self.level_label
            + " = "
            + hmsurface_format_ideal_generators(self.level_gens, self.field.K().gen())
        )

    @lazy_attribute
    def formatted_component(self):
        return (
            self.component_label
            + " = "
            + hmsurface_format_ideal_generators(self.comp_gens, self.field.K().gen())
        )

    @lazy_attribute
    def level_norm(self):
        return ZZ(self.level_label.split(".")[0])

    @lazy_attribute
    def field(self):
        return WebNumberField(self.field_label)

    @lazy_attribute
    def formatted_cusps(self):
        cusps = list(
            db.hmsurfaces_cusps.search(
                {"label": self.label},
                ["M_label", "coordinates", "self_intersections_minimal", "repetition"],
            )
        )
        return [hmsurface_format_cusp(s, self.field.K().gen()) for s in cusps]

    @lazy_attribute
    def formatted_elliptic_pts(self):
        ellpts = list(
            db.hmsurfaces_elliptic_pts.search(
                {"label": self.label}, ["nb", "rotation_type"]
            )
        )
        ptlist = [hmsurface_format_elliptic_pt(pt) for pt in ellpts]
        ptlist.sort()
        return ptlist

    @lazy_attribute
    def nb_elliptic_pts(self):
        return sum([pt[1] for pt in self.formatted_elliptic_pts])

    @lazy_attribute
    def kodaira_dims(self):
        return self.kodaira_dims

    @lazy_attribute
    def kodaira_is_known(self):
        return len(self.kodaira_dims) == 1

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
                "Underlying data",
                url_for(".hmsurface_data", label=self.label),
            ),
        ]
        return self.downloads
