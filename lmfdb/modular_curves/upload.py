
import re
from flask import url_for
from sage.all import ZZ, QQ, lazy_attribute, NumberField
from lmfdb import db
from lmfdb.utils.uploader import UTextBox, UTextArea, UReferenceBox, USelectBox, UploadSection, Uploader
from lmfdb.number_fields.web_number_field import nf_display_knowl
from lmfdb.modular_curves import modcurve_page
from lmfdb.modular_curves.web_curve import get_bread, learnmore_list, COARSE_LABEL_RE, FINE_LABEL_RE, modcurve_link


class ModelTypeBox(USelectBox):
    def __init__(self, name, label):
        USelectBox.__init__(
            self, name, label, "upload.modcurve.model_type",
            [("", ""),
             ("0", "Canonical"),
             ("1", "P1"),
             ("2", "Plane"),
             ("5", "Weierstrass"),
             ("7", "Geometric Weierstrass"),
             ("8", "Embedded")],
            no_empty=True, integer=True)

jre = re.compile(r"\d+(/\d+)?(,\d+(/\d+)?)*")
jpat = jre.pattern
coordre = re.compile(fr"{jpat}(:{jpat})*(;{jpat}(:{jpat})*)")
class Points(UploadSection):
    name = "modcurve_points"
    title = "Upload rational points on modular curves"
    intro = "To upload a single rational point, fill in the following entries."
    inputs = [UReferenceBox("reference", "Reference", "upload.reference"),
              UTextBox("curve", "Modular curve", "upload.modcurve.name_or_label", name_or_label_for="gps_gl2zhat_fine", label_linker=modcurve_link),
              UTextBox("residue_field", "Residue field", "upload.modcurve.residue_field", label_for="nf_fields", label_linker=lambda label: nf_display_knowl(label, label)),
              UTextBox("jorig", "$j$-invariant", "upload.modcurve.jinv", remove_spaces=True, re=(jre, "comma separated rationals"), mathmode=True),
              UTextBox("coordinates", "Coordinates", "upload.modcurve.coordinates", remove_spaces=True, re=(coordre, "semicolon separated points, each point giving (weighted) projective coordinates sepatated by colons, with each coordinate specified as a comma separated list of rational numbers"), mathmode=True),
              ModelTypeBox("model_type", "Model type"),
              USelectBox("isolated", "Isolated", "upload.modcurve.isolated",
                         [("0", "Unknown"),
                          ("4", "Isolated"),
                          ("2", "P1-isolated, AV-parameterized"),
                          ("-2", "AV-isolated, P1-parameterized"),
                          ("-4", "P1-parameterized, AV-parameterized"),
                          ("3", "P1-isolated"),
                          ("1", "AV-isolated"),
                          ("-1", "AV-parameterized"),
                          ("-3", "P1-parameterized")], integer=True),
              ]

    def validate(self, rec):
        rec = super().validate(rec)
        # The box validators have run some initial checks.  We augment this as follows:
        # Check that jorig is the right degree
        n = ZZ(rec["residue_field"].split(".")[0])
        g = ZZ(rec["curve"].split(".")[2])
        if g == 0:
            raise ValueError("Adding points on genus zero curves not supported")
        if rec["jorig"].count(",") != n-1:
            raise ValueError(f"j-coordinate {rec['jorig']} has degree {rec['jorig'].count(',')+1} but residue field has degree {n}")

        # Check that each coordinate satisfies the equations for the model, and combine model_type and coordinates into the right format
        model_type = rec["model_type"]
        edata = db.modcurve_models.search({"modcurve":rec["curve"], "model_type":model_type}, ["number_variables", "equation"])
        if edata is None:
            box = [x for x in self.inputs if x.name == "model_type"][0]
            model_name = [name for (opt, name) in box.options if opt == str(model_type)][0]
            raise ValueError(f"There is no {model_name} model for {rec['curve']} stored in the database")
        d = edata["number_variables"]
        equation = edata["equation"]
        if model_type in [2, 5]:
            if d != 3:
                raise ValueError(f"Underlying data error: num vars {d} but it should be 3")
            vars = "xyz"
        elif model_type == 7:
            if d != 4:
                raise ValueError(f"Underlying data error: num vars {d} but it should be 4")
            vars = "xyzw"
        else:
            # Embedded or canonical
            vars = "xyzwtuvrsabcdefghiklmnopqj"[:d]
        S = QQ[list(vars)]
        try:
            equation = [S(g) for g in equation]
        except Exception:
            raise ValueError("Underlying data error: could not build polynomials from\n{equation}")
        if n != 1:
            R = ZZ['x']
            f = R(db.nf_fields.lookup(rec["residue_field"], "coeffs"))
            K = NumberField(f, "a")
        encoded = rec["coordinates"].split(";")
        for pt in encoded:
            coords = pt.split(":")
            if len(coords) != d:
                raise ValueError(f"Coordinates do not have the right size: there are {len(coords)} but should be {d}")
            for x in coords:
                if x.count(",") != n-1:
                    raise ValueError(f"Coordinate does not lie in field of correct degree: {x} does not have degree {n}")
            if n == 1:
                coords = [QQ(x) for x in coords]
            else:
                coords = [K([QQ(z) for z in x.split(",")]) for x in coords]
            for g in equation:
                if g.subs(dict(zip(vars, coords))) != 0:
                    raise ValueError(f"{pt} does not satisfy equation {str(g).replace(' ','')}=0")
        return rec

    @lazy_attribute
    def csv_template_url(self):
        return url_for(".points_csv")

@modcurve_page.route("/Q/upload/points.csv")
def points_csv():
    return Points().csv_template()

class PointCompleteness(UploadSection):
    name = "modcurve_completeness"
    title = "Rational point completeness"
    intro = "If the LMFDB's list of points for a modular curve is proven complete in some reference, enter it here."
    inputs = [UReferenceBox("reference", "Reference", "upload.reference"),
              UTextArea("curves", "Modular Curve(s)", "upload.modcurve.name_or_label", name_or_label_for="gps_gl2zhat_fine", label_linker=modcurve_link, cols=30, rows=3),
              ]
    offer_csv = False

    def parse_form(self, form):
        rec = super().parse_form(form)[0]
        # We split the text area into one upload per line
        return [{"reference": rec["reference"], "curves": x} for x in rec["curves"]]

class GonalityBounds(UploadSection):
    name = "modcurve_gonality"
    title = "Gonality bounds"
    intro = "To update gonality bounds for a single curve, enter it here; these bounds will be propogated to other modular curves."
    inputs = [UReferenceBox("reference", "Reference", "upload.reference"),
              UTextBox("curve", "Modular curve", "upload.modcurve.name_or_label", name_or_label_for="gps_gl2zhat_fine", label_linker=modcurve_link),
              UTextBox("q_gonality", r"$\mathbb{Q}$-gonality", "upload.modcurve.q_gonality", remove_spaces=True, natural_or_range=True),
              UTextBox("qbar_gonality", r"$\bar{\mathbb{Q}}$-gonality", "upload.modcurve.qbar_gonality", remove_spaces=True, natural_or_range=True),
              ]

    def validate(self, rec):
        rec = super().validate(rec)
        # We run some additional consistency checks on the claimed gonalities
        qgon = rec["q_gonality"]
        if "-" in qgon:
            q_low, q_high = map(ZZ, qgon.split("-"))
        else:
            q_low = q_high = ZZ(qgon)
        qbargon = rec["qbar_gonality"]
        if "-" in qbargon:
            qbar_low, qbar_high = map(ZZ, qbargon.split("-"))
        else:
            qbar_low = qbar_high = ZZ(qbargon)

        cur = db.gps_gl2zhat_fine.lookup(rec["curve"], ["q_gonality_bounds", "qbar_gonality_bounds"])
        if not (cur["q_gonality_bounds"][0] <= q_low <= q_high <= cur["q_gonality_bounds"][1]):
            raise ValueError(f"Q-gonality bounds for {rec['curve']} inconsistent with current bounds {cur['q_gonality_bounds']}")
        if not (cur["qbar_gonality_bounds"][0] <= qbar_low <= qbar_high <= cur["qbar_gonality_bounds"][1]):
            raise ValueError(f"Qbar-gonality bounds for {rec['curve']} inconsistent with current bounds {cur['qbar_gonality_bounds']}")
        return rec

    def verify(self, rec):
        pass

    @lazy_attribute
    def csv_template_url(self):
        return url_for(".gonality_csv")

@modcurve_page.route("/Q/upload/gonality.csv")
def gonality_csv():
    return GonalityBounds().csv_template()

class Models(UploadSection):
    name = "modcurve_models"
    title = "Models"
    intro = r"To add a model for a modular curve, enter it here.  Note that a map to or from another model is required (either giving a birational map to/from another model of the same curve, or giving the map to another modular curve induced by an inclusion of subgroups of $\GL(2, \hat{\mathbb{Z}})$.  Adding a model may also update the gonality of this and other curves."
    inputs = [UReferenceBox("reference", "Reference", "upload.reference"),
              ModelTypeBox("model_type", "Model type"),
              UTextBox("equation", "Equation(s)", "upload.modcurve.model_equation"),
              UTextBox("curve", "Modular curve", "upload.modcurve.name_or_label", name_or_label_for="gps_gl2zhat_fine", label_linker=modcurve_link),
              USelectBox("maps", "Maps", "upload.modcurve.map_direction",
                         [("to", "To"),
                          ("from", "From")]),
              UTextBox("other_curve", "Other curve", "upload.modcurve.name_or_label", name_or_label_for="gps_gl2zhat_fine", label_linker=modcurve_link),
              ModelTypeBox("other_model_type", "Other model type"),
              UTextBox("map_coordinates", "Map Definition", "upload.modcurve.map_coordinates", mathmode=True),
              ]

    def validate(self, rec):
        rec = super().validate(rec)
        # We only do some simple checks that the other modular curve is plausible
        if rec["curve"] != rec["other_curve"] and rec["maps"] == "from":
            raise ValueError("Defining map from another curve only allowed if birational")
        if rec["model_type"] == 1:
            raise ValueError("P1 models are not stored in the database")
        N, i, g, _ = rec["curve"].split(".", 3)
        N, i, g = ZZ(N), ZZ(i), ZZ(g)
        oN, oi, og, _ = rec["other_curve"].split(".", 3)
        oN, oi, og = ZZ(oN), ZZ(oi), ZZ(og)
        if g < og:
            raise ValueError("Genus of other curve larger; map not possible")
        if N % oN != 0:
            raise ValueError("Level of other curve not a divisor; map not possible")
        if i % oi != 0:
            raise ValueError("Index of other curve not a divisor; map not possible")
        # More extensive checks need to be done in Magma in a validation stage
        return rec

    @lazy_attribute
    def csv_template_url(self):
        return url_for(".models_csv")

@modcurve_page.route("/Q/upload/models.csv")
def models_csv():
    return Models().csv_template()

# TODO: Should we also have a section for generic reference?

def to_coarse_label(label):
    """
    INPUT:

    - ``label`` -- either a coarse or fine label for a modular curve

    OUTPUT:

    - ``coarse_label`` -- the label for corresponding coarse curve
    - ``g`` -- the genus
    """
    match = COARSE_LABEL_RE.fullmatch(label)
    if match:
        return label, int(match.group(3))
    match = FINE_LABEL_RE.fullmatch(label)
    if match:
        N, i, g, M, c, m, n = match.groups()
        j = int(i) // 2
        return f"{M}.{j}.{g}.{c}.{m}", int(g)
    raise ValueError(f"{label} does not fit format for modular curve label")

class UniversalEC(UploadSection):
    name = "modcurve_universal_ec"
    title = "Universal Elliptic Curve"
    intro = "To add a model for the universal elliptic curve on a modular curve, enter it here."
    inputs = [UReferenceBox("reference", "Reference", "upload.reference"),
              UTextBox("curve", "Modular curve", "upload.modcurve.name_or_label", name_or_label_for="gps_gl2zhat_fine", label_linker=modcurve_link),
              ModelTypeBox("model_type", "Model type"),
              UTextBox("universal_ec", "Universal Elliptic Curve Model", "upload.modcurve.universal_ec"),
              ]

    def validate(self, rec):
        rec = super().validate(rec)
        if rec["universal_ec"].count(",") not in [1,4]:
            raise ValueError("Equation must be given as a list of a-invariants of length either 2 or 5")
        coarse_label, g = to_coarse_label(rec["curve"])
        if g == 0:
            pointless = db.gps_gl2zhat_fine.lookup(coarse_label, "pointless")
            vars = "xyz" if pointless else "xy" # TODO: should we be using t as a coordinate here or xy?
        else:
            numvars = db.modcurve_models.lucky({"modcurve": rec["curve"], "model_type": rec["model_type"]}, "number_variables")
            vars = "xyzwtuvrsabcdefghiklmnopqj"[:numvars]
        S = QQ[list(vars)].fraction_field()
        for f in rec["universal_ec"].split(","):
            try:
                f = S(f)
            except Exception:
                raise ValueError(f"Invalid format (must be in Q({','.join(vars)})): {f}")
        return rec

    @lazy_attribute
    def csv_template_url(self):
        return url_for(".universal_ec_csv")

@modcurve_page.route("/Q/upload/universal_ec.csv")
def universal_ec_csv():
    return UniversalEC().csv_template()

class ModularCurveUploader(Uploader):
    title = "Upload modular curve data"

    def __init__(self):
        super().__init__([Points(), PointCompleteness(), GonalityBounds(), Models(), UniversalEC()])

    @property
    def bread(self):
        return get_bread("Upload")

    @property
    def learnmore(self):
        return learnmore_list()
