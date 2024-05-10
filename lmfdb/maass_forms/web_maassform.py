# -*- coding: utf-8 -*-
from lmfdb import db
from lmfdb.utils import display_knowl, Downloader, web_latex_factored_integer, prop_int_pretty
from psycodict.encoding import Json
from flask import url_for, abort
from sage.all import RR


def character_link(level, conrey_index):
    label = "%d.%d" % (level, conrey_index)
    return display_knowl('character.dirichlet.data', title=label, kwargs={'label': label})


def fricke_pretty(fricke_eigenvalue):
    if fricke_eigenvalue == 0:
        return "not computed rigorously"
    elif fricke_eigenvalue == 1:
        return "$+1$"
    else:
        return "$-1$"


def symmetry_pretty(symmetry):
    return "even" if symmetry == 0 else ("odd" if symmetry == 1 else "")


def th_wrap(kwl, title):
    return '    <th>%s</th>' % display_knowl(kwl, title=title)


def td_wrapl(val):
    return '    <td align="left">%s</td>' % val


def td_wrapc(val):
    return '    <td align="center">%s</td>' % val


def td_wrapr(val):
    return '    <td align="right">%s</td>' % val


def coeff_error_notation(coeff, error):
    r"""Web coefficient and error display, with trunctation"""
    if error == -1:
        return r"\mathrm{unknown}"
    coeffpart = "%+.8f" % coeff
    if error == 0:
        errorpart = ""
    else:
        base, negexponent = mantissa_and_exponent(error)
        negexponent = min(negexponent, 8)
        errorpart = r" \pm " + exponential_form(base, negexponent, digits_to_show=3)
    return coeffpart + errorpart


def mantissa_and_exponent(number):
    """
    Returns (mantissa, exponent) where number = mantissa * 10^(-exponent).

    The input should be a RealLiteral.
    """
    if number > 1:
        return (number, 0)
    snum = str(number)
    if '.' not in snum:
        return (number, 0)
    pre, post = snum.split('.')
    # determine the exponent
    idx = 0
    for idx, c in enumerate(post):
        if c != '0':
            break
    negative_exponent = idx + 1
    mantissa = post[idx] + "." + post[idx+1:]
    return (mantissa, negative_exponent)


def exponential_form(mantissa, negative_exponent, digits_to_show=9):
    """
    Format the number `mantissa * 10^(-negative_exponent)` nicely.
    """
    if negative_exponent == 0:
        return mantissa[:digits_to_show]
    return mantissa[:digits_to_show] + r" \cdot 10^{-" + str(negative_exponent) + "}"


def parity_text(val):
    return 'odd' if val == -1 else 'even'


def short_label(label):
    # We shorten some labels from 5 components to 2 for simplicity (all of the Maass forms in the initial draft of the database had the same values for the second, third and fifth part of the label)
    pieces = label.split(".")
    if len(pieces) == 5 and pieces[1] == '0' and pieces[2] == '1' and pieces[4] == '1':
        return f"{pieces[0]}.{pieces[3]}"
    return label


def long_label(label):
    # Undo the transformation from short_label
    pieces = label.split(".")
    if len(pieces) == 2:
        return f"{pieces[0]}.0.1.{pieces[1]}.1"
    return label


class WebMaassForm():
    def __init__(self, data):
        self.__dict__.update(data)
        self._data = data
        # TODO figure out how to handle portraits appropriately
        #self.portrait = db.maass_portraits.lookup(self.label, projection="portrait")

    @staticmethod
    def by_label(label):
        data = db.maass_rigor.lookup(label)
        if data is None:
            raise KeyError("Maass newform %s not found in database." % (label))
        return WebMaassForm(data)

    @property
    def label(self):
        return self.maass_label

    @property
    def coeffs(self):
        return [RR(c) for c in self.coefficients]

    @property
    def spectral_index(self):
        return self.nspec

    @property
    def web_spectral_error(self):
        str_error = "%E" % self.spectral_error
        base, _, exponent = str_error.partition("E")
        base, rest = base.split(".")
        base = str(int(base) + 1)
        exponent = str(int(exponent))
        return rf"{base} \cdot 10^{{{exponent}}}"

    @property
    def title(self):
        digits_to_show = 10
        return (rf"Maass form {short_label(self.label)} on \(\Gamma_0({self.level})\) "
                rf"with \(R={str(self.spectral_parameter)[:digits_to_show]}\)")

    @property
    def properties(self):
        # props = [
        #   (None, '<img src="{0}" width="200" height="150" style="margin:10px;"/>'.format(self.portrait))
        # ] if self.portrait is not None else []
        props = []
        props += [('Label', short_label(self.label)),
                  ('Level', prop_int_pretty(self.level)),
                  ('Weight', prop_int_pretty(self.weight)),
                  ('Character', self.character_label),
                  ('Symmetry', self.symmetry_pretty),
                  ]
        if self.conrey_index == 1:
            props.append(('Fricke sign', self.fricke_pretty))
        return props

    @property
    def factored_level(self):
        return web_latex_factored_integer(self.level, equals=True)

    @property
    def character_label(self):
        return "%d.%d" % (self.level, self.conrey_index)

    @property
    def character_link(self):
        return character_link(self.level, self.conrey_index)

    @property
    def symmetry_pretty(self):
        return symmetry_pretty(self.symmetry)

    @property
    def fricke_pretty(self):
        return fricke_pretty(self.fricke_eigenvalue)

    @property
    def bread(self):
        return [('Modular forms', url_for('modular_forms')),
                ('Maass', url_for(".index")),
                ("Level %d" % (self.level), url_for(".by_level", level=self.level)),
                ("Weight %d" % (self.weight), url_for(".by_level_weight", level=self.level, weight=self.weight)),
                ("Character %s" % (self.character_label), url_for(".by_level_weight_character", weight=self.weight, level=self.level, conrey_index=self.conrey_index)),
                ]

    @property
    def downloads(self):
        return [("Coefficients to text", url_for(".download_coefficients", label=self.label)),
                ("All stored data to text", url_for(".download", label=self.label)),
                ("Underlying data", url_for(".maass_data", label=self.label)),
                ]

    @property
    def friends(self):
        friendlist = []
        if self.nspec > 1:
            prevlabel = f"{self.level}.{self.weight}.{self.conrey_index}.{self.nspec - 1}.1"
            friendlist += [("Previous Maass form", url_for(".by_label", label=prevlabel))]
        if self.nspec < db.maass_rigor.count(query={'level':self.level}):
            nextlabel = f"{self.level}.{self.weight}.{self.conrey_index}.{self.nspec + 1}.1"
            friendlist += [("Next Maass form", url_for(".by_label", label=nextlabel))]
        friendlist += [("L-function not computed", '')]
        return friendlist

    def coefficient_table(self, rows=20, cols=3):
        n = len(self.coefficients)
        assert rows > 0 and cols > 0
        table = ['<table class="ntdata"><thead><tr><th></th></tr></thead><tbody>']
        if (rows - 1) * cols >= n:
            rows = (n // cols) + (1 if (n % cols) else 0)
        for i in range(rows):
            table.append('<tr>')
            for j in range(cols):
                if i * cols + j >= n:
                    break
                table.append(
                    td_wrapl(r"\(a_{%d}= %s \)"
                             % (i * cols + j + 1,
                                coeff_error_notation(
                                    self.coefficients[i * cols + j],
                                    self.coefficient_errors[i * cols + j]
                                ))))
            table.append('</tr>')
        table.append('</tbody></table>')
        if rows * cols < n:
            table.append('<p>Showing %d of %d available coefficients</p>' % (rows * cols, n))
        else:
            table.append('<p>Showing all %d available coefficients</p>' % n)
        return '\n'.join(table)


class MaassFormDownloader(Downloader):
    title = 'Maass forms'

    def download(self, label, lang='text'):
        table = db.maass_rigor
        data = table.lookup(label)
        if data is None:
            return abort(404, "Maass form %s not found in the database" % label)
        for col in table.col_type:
            if table.col_type[col] == "numeric" and data.get(col):
                data[col] = str(data[col])
            if table.col_type[col] == "numeric[]" and data.get(col):
                data[col] = [str(data[col][n]) for n in range(len(data[col]))]
        return self._wrap(Json.dumps(data),
                          "maass." + label,
                          lang=lang,
                          title='All stored data for Maass form %s,' % (label))

    def download_coefficients(self, label, lang='text'):
        table = db.maass_rigor
        data = table.lookup(label, projection=["coefficients", "coefficient_errors"])
        if data is None:
            return abort(404, "Coefficient data for Maass form %s not found in the database" % label)
        coeffs = data["coefficients"]
        errors = data["coefficient_errors"]
        retdata = [str(coeffs[n]) + " +- " + str(errors[n]) for n in range(len(coeffs))]
        return self._wrap(Json.dumps(retdata).replace('"', ''),
                          "maass." + label + '.coefficients',
                          lang=lang,
                          title='Coefficients for Maass form %s,' % (label))
