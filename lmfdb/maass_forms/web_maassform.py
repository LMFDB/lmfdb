from lmfdb import db
from lmfdb.utils import (
    display_knowl,
    Downloader,
    prop_int_pretty,
    raw_typeset,
    web_latex_factored_integer,
)
from psycodict.encoding import Json
from flask import url_for, abort
from sage.all import RR, ZZ, factor, sign, prod


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


def sgn_to_tex(sgn):
    if sgn == 1:
        return "+"
    elif sgn == -1:
        return "-"
    else:
        return r"\pm"


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


def coeff_is_finite_rational(n, primes):
    """
    In the case when n is divisible only the primes 2 and 5, and 2 or 5
    divides the level, and if n is a square, and the level is squarefree --- then a(n)
    is actually rational.
    """
    f = factor(n)
    for p, e in f:
        if p not in primes:
            return False
        if e % 2 != 0:
            return False
    return True


def rational_coeff_error_notation(factored_n):
    res = 1
    if not factored_n:  # n = 1
        return "1"
    for p, e in factored_n:
        res *= p**(e//2)
    res = 1./res
    res = str(res).rstrip('0')
    return res


def coeff_error_notation(coeff, error, pm=False):
    r"""Web coefficient and error display, with truncation"""
    if error == -1:
        return r"\mathrm{unknown}"
    if pm:
        coeffpart = r"\pm%.8f" % coeff
    else:
        coeffpart = "%+.8f" % coeff
    if error == 0:
        errorpart = ""
    else:
        base, negexponent = mantissa_and_exponent(error)
        if negexponent > 8:
            negexponent = 8
            base = 1
        errorpart = r" \pm " + exponential_form(base, negexponent, digits_to_show=3)
    return coeffpart + errorpart


def mantissa_and_exponent(number):
    """
    Returns (mantissa, exponent) where number = mantissa * 10^(-exponent).

    The input should be a RealLiteral.
    """
    if number > 1:
        return (number, 0)
    exponent = -number.log10().floor()
    return (number * 10**exponent, exponent)


def exponential_form(mantissa, negative_exponent, digits_to_show=9):
    """
    Format the number `mantissa * 10^(-negative_exponent)` nicely.
    """
    mantissa = str(mantissa)
    if negative_exponent == 0:
        return mantissa[:digits_to_show]
    return mantissa[:digits_to_show] + r" \cdot 10^{-" + str(negative_exponent) + "}"


def parity_text(val):
    return 'odd' if val == -1 else 'even'


def short_label(label):
    # We shorten some labels from 5 components to 2 for simplicity (all of the
    # Maass forms in the initial draft of the database had the same values for
    # the second, third and fifth part of the label)
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
        self.portrait = db.maass_rigor_portraits.lookup(self.label, projection="portrait")

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
    def web_spectral_line(self):
        if len(str(self.spectral_parameter)) < 35:
            return rf"\({self.spectral_parameter} \pm {self.web_spectral_error}\)"
        else:
            short_spectral = str(self.spectral_parameter)[:35]
            return raw_typeset(
                str(self.spectral_parameter) + " +- " + str(self.spectral_error),
                rf"\( {short_spectral}\ldots \pm {self.web_spectral_error} \)",
                extra="(toggle for full precision)"
            )

    @property
    def title(self):
        digits_to_show = 10
        return (rf"Maass form {short_label(self.label)} on \(\Gamma_0({self.level})\) "
                rf"with \(R={str(self.spectral_parameter)[:digits_to_show]}\)")

    @property
    def properties(self):
        props = [
          (None, '<img src="{0}" width="200" height="200" style="margin:10px;"/>'.format(self.portrait))
        ] if self.portrait is not None else []
        props += [('Label', short_label(self.label)),
                  ('Level', prop_int_pretty(self.level)),
                  ('Weight', prop_int_pretty(self.weight)),
                  ('Character', self.character_label),
                  ('Symmetry', self.symmetry_pretty),
                  (r"\(R\)", str(self.spectral_parameter)[:8]),
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

    def coefficient_table(self, rows=20, cols=3, row_opts=[20,60,334]):
        # This logic applies to squarefree level.
        has_finite_rational_coeffs = False
        level_primes = ZZ(self.level).prime_divisors()
        level_10_primes = [p for p in level_primes if p in [2,5]]
        has_finite_rational_coeffs = bool(level_10_primes)

        n = len(self.coefficients)
        row_opts = sorted(row_opts)
        overage = [r for r in row_opts if r * cols >= n]
        if len(overage) > 1:
            row_opts = row_opts[:1 - len(overage)]
        if rows not in row_opts:
            rows = row_opts[0]
        assert rows > 0 and cols > 0
        default_rows = rows
        rows = row_opts[-1]
        table = ['<table class="ntdata"><thead><tr><th></th></tr></thead><tbody>']
        if (rows - 1) * cols >= n:
            rows = (n // cols) + (1 if (n % cols) else 0)
        for i in range(rows):
            maassrow = "maassrow " + " ".join(f"maassrow{m}" for m in row_opts if i < m)
            display = "" if i < default_rows else ' style="display: none;"'
            table.append(f'<tr class="{maassrow}"{display}>')
            for j in range(cols):
                if i * cols + j >= n:
                    break
                m = i * cols + j + 1
                if m == 1:
                    table.append(
                        td_wrapl(rf"\(a_{{{m}}}= +1 \)")
                    )
                    continue
                f = factor(m)
                if has_finite_rational_coeffs:
                    level_part = prod(p**e for p, e in f if p in level_10_primes)
                    other_part = prod(p**e for p, e in f if p not in level_10_primes)
                    m_is_finite_rational = (other_part == 1 and all(e % 2 == 0 for p, e in f))
                    if m_is_finite_rational:
                        # determine sign
                        sgn = sign(self.coefficients[m - 1])  # if fricke_unknown, this is 0
                        sign_str = sgn_to_tex(sgn)
                        table.append(
                            td_wrapl(rf"\(a_{{{m}}}= {sign_str}{rational_coeff_error_notation(f)} \)")
                        )
                        continue
                coeff = self.coefficients[i * cols + j]
                error = self.coefficient_errors[i * cols + j]
                pm = False
                if self.fricke_eigenvalue == 0:
                    # Work out the coefficient from one that's prime to the level
                    level_part = prod(p**e for p, e in f if p in level_primes)
                    other_part = prod(p**e for p, e in f if p not in level_primes)
                    if level_part > 1:
                        coeff = abs(self.coefficients[other_part - 1] / RR(level_part).sqrt())
                        pm = True
                        if other_part == 1:
                            error = RR(1e-8)
                        else:
                            error = max(RR(1e-8),self.coefficient_errors[other_part - 1] / RR(level_part.sqrt()))
                # otherwise: m is not special, and print as normal
                table.append(
                    td_wrapl(r"\(a_{%d}= %s \)"
                             % (i * cols + j + 1,
                                coeff_error_notation(
                                    coeff,
                                    error,
                                    pm=pm
                                ))))
            table.append('</tr>')
        table.append('</tbody></table>')
        buttons = " ".join(f'<a onclick="return maass_switch({r});" href="#">{min(n, r*cols)}</a>' for r in row_opts)
        table.append(f'<p>Displaying $a_n$ with $n$ up to: {buttons}</p>')
        return '\n'.join(table)


class MaassFormDownloader(Downloader):
    table = db.maass_rigor
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
