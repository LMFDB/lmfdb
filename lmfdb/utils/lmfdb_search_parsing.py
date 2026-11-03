"""
Parsers for the search forms of the LMFDB that know about its objects and
their labels (number fields, Galois groups, p-adic fields, ...).

The general parsers are in lmfdb-utils (``lmfdb_utils.search_parsing``).
"""
import ast
import re

from sage.all import ZZ, QQ, QQbar, prod, PolynomialRing, pari

from lmfdb_utils.search_parsing import (
    QQ_LIST_RE,
    QQ_RE,
    SearchParsingError,
    collapse_ors,
    parse_bracketed_posints,
    search_parser,
    split_list,
)
from lmfdb_utils.utilities import coeff_to_poly, flash_info, integer_squarefree_part


# see SearchParser.__call__ for actual arguments when calling
@search_parser(clean_info=True, prep_plus=True)
def parse_group_label_or_order(inp, query, qfield, regex):
    inps = inp.split(",")
    inporders = [z for z in inps if re.fullmatch(r'\d+',z)]
    inporders = [{'$startswith': f'{z}.'} for z in inporders]
    inplabels = [z for z in inps if not re.fullmatch(r'\d+',z)]
    if all(regex.fullmatch(z) for z in inplabels):
        if len(inplabels) == 1:
            labelquery = inplabels[0]
        else:
            labelquery = {"$in": inplabels}
    else:
        raise SearchParsingError("Group label(s) do not match the required form")
    if inporders:
        if inplabels:
            query[qfield] = {"$or": inporders + [labelquery]}
        else:
            query[qfield] = {"$or": inporders}
    else:
        query[qfield] = labelquery


def parse_gap_id(info, query, field="group", name="Group", qfield="group"):
    parse_bracketed_posints(
        info,
        query,
        field,
        split=False,
        exactlength=2,
        keepbrackets=True,
        name=name,
        qfield=qfield,
    )

# see SearchParser.__call__ for actual arguments when calling
@search_parser(
    clean_info=True,
    default_field="galois_group",
    default_name="Galois group",
    default_qfield="galois",
    error_is_safe=True,
)
def parse_galgrp(inp, query, qfield, err_msg=None, list_ok=True):
    try:
        if list_ok:
            from lmfdb.galois_groups.transitive_group import complete_group_codes

            gcs, incomplete = complete_group_codes(inp)
        else:
            from lmfdb.galois_groups.transitive_group import complete_group_code

            gcs, incomplete = complete_group_code(inp)

        galfield, nfield = qfield
        if nfield and nfield not in query:
            if incomplete:
                # If the user specified an abstract group and did not specify a degree, then it can only be complete if we have ALL of the corresponding transitive groups in the database
                query["__complete__"] = False
            nvals = list({s[0] for s in gcs})
            if len(nvals) == 1:
                query[nfield] = nvals[0]
            else:
                query[nfield] = {"$in": nvals}
        # if nfield was already in the query, we could try to intersect it with nvals; note that this would have completeness implications
        cands = ["{}T{}".format(s[0], s[1]) for s in gcs]
        if len(cands) == 1:
            query[galfield] = cands[0]
        else:
            query[galfield] = {"$in": cands}
    except NameError:
        if re.match(r"^[ACDFMQS]\d+$", inp):
            raise SearchParsingError("The requested group is not in the database")
        if err_msg:
            raise SearchParsingError(err_msg)
        else:
            raise SearchParsingError("It needs to be a list made up of abstract group labels or GAP ids, such as 4.1, 2430.h, [4,1] or [12,5], transitive groups in nTj notation, such as 5T1, and <a title = 'Galois group labels' knowl='nf.galois_group.name'>group labels</a>")

# The queries for inertia (and wild inertia) subgroups are different
# than the ones for Galois groups.
# see SearchParser.__call__ for actual arguments when calling
@search_parser(
    clean_info=True,
    default_field="inertia_gap",
    default_name="Inertia group",
    default_qfield="inertia_gap",
    error_is_safe=True,
)
def parse_inertia(inp, query, qfield, err_msg=None):
    try:
        # For inertia groups, qfield=('inertia_gap', 'inertia')
        # For wild inertia, qfield=('wild_gap', 'wild_gap')

        # Need to convert it to GAP id
        from lmfdb.galois_groups.transitive_group import nt2abstract

        iner_gap, iner = qfield
        # Check for nTj
        rematch = re.match(r"^(\d+)[Tt](\d+)$", inp)
        if rematch:
            n = int(rematch.group(1))
            t = int(rematch.group(2))
            if iner != iner_gap:
                query[iner] = ["t", [n, t]]
            else:
                abstractid = nt2abstract(n, t)
                query[iner] = abstractid
        else:
            # Check for an alias, like D4
            import lmfdb.galois_groups.transitive_group

            aliases = lmfdb.galois_groups.transitive_group.get_aliases()
            inp2 = inp.upper()
            if inp2 in aliases:
                nt = aliases[inp2][0][0]
                query[iner_gap] = nt2abstract(nt[0], nt[1])
            else:
                # Check for Gap code using [a,b] or a.b notation
                rematch = re.fullmatch(r"\[(\d+),(\d+)\]", inp)
                if rematch:
                    query[iner_gap] = [int(rematch.group(1)), int(rematch.group(2))]
                else:
                    rematch = re.fullmatch(r"(\d+)\.(\d+)", inp)
                    if rematch:
                        query[iner_gap] = [int(rematch.group(1)), int(rematch.group(2))]
                    else:
                        raise NameError

    except NameError:
        if re.match(r"^[ACDFMQS]\d+$", inp):
            raise SearchParsingError("The requested group is not in the database")
        if err_msg:
            raise SearchParsingError(err_msg)
        else:
            raise SearchParsingError("It needs to be a small group id, such as [4,1] or 12.5, ia transitive group in nTj notation, such as 5T1, or a <a title = 'Group label' knowl='nf.galois_group.name'>group label</a>")

# see SearchParser.__call__ for actual arguments when calling
@search_parser(clean_info=True, error_is_safe=True)
def parse_padicfields(inp, query, qfield, flag_unramified=False):
    from lmfdb.local_fields.main import NEW_LF_RE, OLD_LF_RE
    labellist = inp.split(",")
    doflash = False
    for label in labellist:
        if not NEW_LF_RE.fullmatch(label) and not OLD_LF_RE.fullmatch(label):
            raise SearchParsingError('It needs to be a <a title = "$p$-adic field label" knowl="lf.field.label">$p$-adic field label</a> or a list of local field labels')
        splitlab = label.split('.')
        if (OLD_LF_RE.fullmatch(label) and splitlab[2] == '0'
            or NEW_LF_RE.fullmatch(label) and splitlab[3][0] == '0'):
            doflash = True
    if flag_unramified and doflash:
        flash_info("Search results may be incomplete.  Given $p$-adic completions contain an <a title='unramified' knowl='nf.unramified_prime'>unramified</a> field and completions are only searched for <a title='ramified' knowl='nf.ramified_primes'>ramified primes</a>.")
    query[qfield] = {"$contains": labellist}

@search_parser(clean_info=True)
def parse_padicsubfields(inp, query, qfield):
    from lmfdb.local_fields.main import NEW_LF_RE, OLD_LF_RE
    labellist = inp.split(",")
    fail = False
    for indx, label in enumerate(labellist):
        if OLD_LF_RE.fullmatch(label):
            pass
        elif NEW_LF_RE.fullmatch(label):
            from lmfdb import db
            oldlabel = db.lf_fields.lucky({'new_label':label})
            if oldlabel:
                oldlabel = oldlabel.get('old_label',None)
            if oldlabel:
                labellist[indx] = oldlabel
            else:
                fail = True
        else:
            fail = True
        if not fail:
            splitlab = labellist[indx].split('.')
            if splitlab[1] == '1':
                p = splitlab[0]
                raise SearchParsingError(r'$\Q_{%s}$ is not considered a proper intermediate field'%str(p))

    if fail:
        raise SearchParsingError('It needs to be a <a title = "$p$-adic field label" knowl="lf.field.label">$p$-adic field label</a> or a list of local field labels')
    else:
        query[qfield] = {"$contains": labellist}

def input_string_to_poly(FF):
    # Change unicode dash with minus sign
    FF = FF.replace("\u2212", "-")
    # remove non-ascii characters from F
    # we need to encode and decode for Python 3, as 'str' object has no attribute 'decode'
    # Remove non-ascii characters
    FF = re.sub(r"[^\x00-\x7f]", r"", FF)
    F = FF.lower()  # keep original if needed
    # check if a polynomial was entered
    try:
        return coeff_to_poly(F), F, FF
    except Exception:
        return None, F, FF


def _strip_matching_outer_parens(s):
    """Remove only parentheses that wrap the entire string, preserving inner grouping."""
    while len(s) >= 2 and s[0] == "(" and s[-1] == ")":
        depth = 0
        wraps_all = True
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if depth == 0 and i < len(s) - 1:
                wraps_all = False
                break
        if wraps_all and depth == 0:
            s = s[1:-1]
        else:
            break
    return s


def _nf_string_to_qqbar(s):
    """
    Converts a string into an algebraic element in QQbar.

    Supported syntax:
    - binary operators: +, -, *, /, ^ (exponentiation)
    - unary operators: +, -
    - functions: sqrt(...), root(...), cbrt(...)
    - zeta roots of unity: zeta(...), zeta_N, zetaN
    - imaginary unit: i
    - golden ratio constant: phi = (1 + sqrt(5))/2
    - shorthand radicals: sqrt5, root-3, cbrt7
    - nth-roots via exponentiation: base^(1/n), e.g., 2^(1/3), phi^(3/4)
    - nested parentheses and combinations of the above

    The expression is safely parsed with a restricted Python AST and then evaluated as a Sage object in QQbar.

    Examples: sqrt2, sqrt2 + cbrt3, zeta4 - 1/phi, sqrt(2 + 3*sqrt(2)), 2^(1/3), phi^(3/4)

    """

    s = s.lower().strip().replace(" ", "")
    if not s:
        raise SearchParsingError("The algebraic expression is empty.")

    def _normalize_radicals(t):
        # Convert shorthand like sqrt5, root-3, cbrt7 into function-call form: sqrt(5), root(-3), cbrt(7).
        t = re.sub(r"\b(sqrt|root|cbrt)([+-]?\d+)\b", r"\1(\2)", t)
        # Convert zeta shorthand like zeta5 or zeta_5 into zeta(5).
        t = re.sub(r"\bzeta_?(\d+)\b", r"zeta(\1)", t)
        # Convert ^ to ** for exponentiation (Python uses ** for exponentiation)
        t = t.replace("^", "**")
        return t

    s = _normalize_radicals(_strip_matching_outer_parens(s))

    try:
        node = ast.parse(s, mode="eval")
    except SyntaxError as err:
        raise SearchParsingError(f"Could not parse algebraic expression '{s}': {err.msg}")

    def _eval_ast(n):
        if isinstance(n, ast.Expression):
            return _eval_ast(n.body)
        if isinstance(n, ast.Constant):
            val = n.value
            if isinstance(val, int):
                return QQbar(QQ(val))
            raise SearchParsingError("Only numeric constants are supported in algebraic expressions.")
        if isinstance(n, ast.Name):
            if n.id == "i":
                return QQbar.zeta(4)
            if n.id == "phi":
                return (QQbar(1) + QQbar(5).sqrt()) / 2
            raise SearchParsingError(f"Unsupported symbol '{n.id}' in algebraic expressions.")
        if isinstance(n, ast.UnaryOp):
            v = _eval_ast(n.operand)
            if isinstance(n.op, ast.UAdd):
                return v
            if isinstance(n.op, ast.USub):
                return -v
            raise SearchParsingError("Unsupported unary operator in algebraic expression.")
        if isinstance(n, ast.BinOp):
            left = _eval_ast(n.left)
            right = _eval_ast(n.right)
            if isinstance(n.op, ast.Add):
                return left + right
            if isinstance(n.op, ast.Sub):
                return left - right
            if isinstance(n.op, ast.Mult):
                return left * right
            if isinstance(n.op, ast.Div):
                if right == 0:
                    raise SearchParsingError("Division by zero in algebraic expression.")
                return left / right
            if isinstance(n.op, ast.Pow):
                # Support for arbitrary nth-roots via exponentiation: base^(exponent)
                # The exponent should be a rational number for algebraic evaluation
                try:
                    exp_rational = QQ(right)
                except (TypeError, ValueError):
                    raise SearchParsingError(f"Exponent must be a rational number, got {right}.")
                # Use QQbar's power operator to handle rational exponents
                # This computes base^exp_rational in QQbar
                return left ** exp_rational
            raise SearchParsingError("Unsupported binary operator in algebraic expression.")
        if isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name):
                raise SearchParsingError("Invalid function call in algebraic expression.")
            fname = n.func.id
            if fname not in {"sqrt", "root", "cbrt", "zeta"}:
                raise SearchParsingError(f"Unsupported function '{fname}' in algebraic expression.")
            if len(n.args) != 1 or n.keywords:
                raise SearchParsingError(f"Function '{fname}' takes exactly one argument.")
            arg = _eval_ast(n.args[0])
            if fname in {"sqrt", "root"}:
                return arg.sqrt()
            if fname == "zeta":
                try:
                    n_q = QQ(arg)
                    n_int = ZZ(n_q)
                except (TypeError, ValueError):
                    raise SearchParsingError("zeta(...) requires a positive integer argument.")
                if n_q != n_int or n_int <= 0:
                    raise SearchParsingError("zeta(...) requires a positive integer argument.")
                return QQbar.zeta(n_int)
            return arg.nth_root(3)
        raise SearchParsingError("Unsupported syntax in algebraic expression.")

    try:
        return _eval_ast(node)
    except SearchParsingError:
        raise
    except Exception as err:
        raise SearchParsingError(f"Could not evaluate algebraic expression '{s}': {err}")


def nf_string_to_label(FF):
    """
    Converts a number field nickname, polynomial, or label to the corresponding LMFDB label (in the format "d.r.D.n").

    Supports custom nicknames of the form Q(s1, s2, ..., sk) where each si is a string representing an algebraic expression
    Uses _nf_string_to_qqbar to safely parse algebraic expressions into elements in QQbar.
    Uses number_field_elements_from_algebraics to compute the minimal number field containing the specified elements.

    Examples: Q, Qsqrt2, Qsqrt-4, Qzeta5, Q(sqrt2+sqrt3), Qcbrt2, Q(sqrt(2 + 3*sqrt2)), Q(sqrt2, cbrt3), Q(2^(1/5)), etc.
    """

    # Check if the rationals Q or Q(i)
    if FF in ["q", "Q"]:
        return "1.1.1.1"
    if FF.lower() in ["qi", "q(i)"]:
        return "2.0.4.1"

    # Check if input is a polynomial
    F1, F, FF = input_string_to_poly(FF)
    F = F.replace(" ", "")
    if len(F) == 0:
        raise SearchParsingError("Entry for the field was left blank.  You need to enter a field label, field name, or a polynomial.")
    if F1 and len(str(F1.parent().gen())) == 1: # we only support single-letter variable names
        from lmfdb.number_fields.number_field import poly_to_field_label

        F1 = poly_to_field_label(F1)
        if F1:
            return F1
        raise SearchParsingError("%s does not define a number field in the database." % F, trim_msg_error=True)

    if F[0] == "q":
        # Strip away outer parenthesis
        Fstrip = _strip_matching_outer_parens(F[1:])
        if len(Fstrip) == 0:
            return "1.1.1.1"

        # Case 1: Check if input is quadratic field (given in the form Qsqrt5 or Q(sqrt5))
        if re.match(r'^(sqrt|root)[+-]?\d+$', Fstrip):
            try:
                d = integer_squarefree_part(ZZ(str(Fstrip[4:])))
            except (TypeError, ValueError):
                d = 0
            if d == 0:
                raise SearchParsingError("After {0}, the remainder must be a nonzero integer.  Use {0}5 or {0}-11 for example.".format(Fstrip[:4]))
            if d == 1:
                return "1.1.1.1"
            if d % 4 in [2, 3]:
                D = 4 * d
            else:
                D = d
            absD = D.abs()
            s = 0 if D < 0 else 2
            return "2.%s.%s.1" % (s, str(absD))

        # Case 2: Check if cyclotomic field (or its maximal real subfield)
        if Fstrip[:4] == "zeta" and re.match(r"^qzeta\d+(\+|plus)?$", F.replace("_", "")):
            match_obj = re.match(r"^qzeta(\d+)(\+|plus)?$", F.replace("_", ""))
            if not match_obj:
                raise SearchParsingError("After {0}, the remainder must be a positive integer or a positive integer followed by '+'.  Use {0}5 or {0}19+, for example.".format(F[:5]))

            d = ZZ(str(match_obj.group(1)))
            if d % 4 == 2:
                d /= 2  # Q(zeta_6)=Q(zeta_3), etc)

            # Check if matches maximal real subfield of a cyclotomic field
            if match_obj.group(2):
                from lmfdb.number_fields.web_number_field import rcyclolookup

                if d in rcyclolookup:
                    return rcyclolookup[d]
                else:
                    raise SearchParsingError(f"{F} is not in the database.")

            # Check if matches cyclotomic field
            from lmfdb.number_fields.web_number_field import cyclolookup

            if d in cyclolookup:
                return cyclolookup[d]
            else:
                raise SearchParsingError(f"{F} is not in the database.")

        # Case 3: Use generic algebraic nickname parser for Q(...), Qsqrt..., Qcbrt..., etc.
        from lmfdb.number_fields.number_field import poly_to_field_label

        # Support comma-separated generators Q(s1, s2, ..., sk).
        pieces = [piece.strip() for piece in Fstrip.split(",")]
        if any(not piece for piece in pieces):
            raise SearchParsingError("Empty generator in comma-separated field nickname.")

        from sage.rings.qqbar import number_field_elements_from_algebraics
        alphas = [_nf_string_to_qqbar(piece) for piece in pieces]
        K, _, _ = number_field_elements_from_algebraics(alphas)
        pol = PolynomialRing(QQ, 'x')(K.defining_polynomial())
        if pol.degree() <= 1:
            return "1.1.1.1"
        label = poly_to_field_label(pol)
        if label:
            return label
        raise SearchParsingError("%s is not in the database." % FF)

    # Expand out factored labels, like 11.11.11e20.1
    from lmfdb.number_fields.number_field import FIELD_LABEL_RE

    if not FIELD_LABEL_RE.match(F):
        raise SearchParsingError("A number field label must be of the form d.r.D.n, such as 2.2.5.1.")
    parts = F.split(".")

    def raise_power(ab):
        if ab.count("e") == 0:
            return ZZ(ab)
        elif ab.count("e") == 1:
            a, b = ab.split("e")
            return ZZ(a) ** ZZ(b)
        else:
            raise SearchParsingError("Malformed absolute discriminant.  It must be a sequence of strings AeB for A and B integers, joined by _s.  For example, 2e7_3e5_11.")

    parts[2] = str(prod(raise_power(c) for c in parts[2].split("_")))
    return ".".join(parts)

# Similar to parsing a number field name, but with different output,
# here coefficients low to high separated by .,
# and different behavior if the entry is not in the database
def input_to_subfield(inp):
    def finish(result):
        return ".".join(str(z) for z in result)

    def notq():
        raise SearchParsingError(r"The rational numbers $\Q$ cannot be a proper intermediate field.")

    # Change unicode dash with minus sign
    inp = inp.replace("\u2212", "-")

    # remove non-ascii characters from inp
    # we need to encode and decode for Python 3, as 'str' object has no attribute 'decode'
    inp = re.sub(r"[^\x00-\x7f]", r"", inp)
    if len(inp) == 0:
        return None

    # Do we have a nf label
    from lmfdb.number_fields.number_field import FIELD_LABEL_RE

    if FIELD_LABEL_RE.match(inp):
        from lmfdb import db

        myfield = db.nf_fields.lookup(inp)
        if myfield:
            return finish(myfield["coeffs"])
        else:
            raise SearchParsingError("It is not the label for a subfield in the database.")

    F = inp.lower()  # keep original if needed
    # Is it a polynomial
    if "x" in F:
        F1 = F.replace("^", "**")
        R = PolynomialRing(ZZ, "x")
        if "," in F:
            raise SearchParsingError("You may only specify one subfield.")
        try:
            pol = PolynomialRing(QQ, "x")(str(F1))
        except Exception:
            raise SearchParsingError("Subfield not entered properly.")
        pol *= pol.denominator()
        if not pol.is_irreducible():
            raise SearchParsingError("It is not an irreducible polynomial.")
        coeffs = R(pari(pol).polredabs()).coefficients(sparse=False)
        if coeffs == [0, 1]:
            notq()
        return finish(coeffs)
    # Nicknames
    if F == "q":
        notq()
    if F in ["qi", "q(i)"]:
        return "1.0.1"
    if F[0] == "q":
        if "(" in F and ")" in F:
            F = F.replace("(", "").replace(")", "")
            inp = inp.replace("(", "").replace(")", "")
        if F[1:5] in ["sqrt", "root"]:
            try:
                d = integer_squarefree_part(ZZ(str(F[5:])))
            except (TypeError, ValueError):
                d = 0
            if d == 0 or d == 1:
                raise SearchParsingError("After {0}, the remainder must be a nonzero integer which is not a perfect square.  Use {0}5 or {0}-11 for example.".format(inp[:5]))
            # Recursion has it use polredabs to get the polynomial
            return input_to_subfield("x^2 - (%s)" % d)
        # Look for cyclotomic
        if F[0:5] == "qzeta":
            if "_" in F:
                F = F.replace("_", "")
            match_obj = re.match(r"^qzeta(\d+)(\+|plus)?$", F)
            if not match_obj:
                raise SearchParsingError("After {0}, the remainder must be a positive integer or a positive integer followed by '+'.  Use {0}5 or {0}19+, for example.".format(F[:5]))

            d = ZZ(str(match_obj.group(1)))
            if d % 4 == 2:
                d /= 2  # Q(zeta_6)=Q(zeta_3), etc)
            if d < 1:
                raise SearchParsingError("After {0}, the remainder must be a positive integer or a positive integer followed by '+'.  Use {0}5 or {0}19+, for example.".format(F[:5]))
            if d == 1:  # asking for Q
                notq()

            if match_obj.group(2):  # asking for the totally real field
                from lmfdb.number_fields.web_number_field import rcyclolookup

                if d < 5:  # again, asking for subfield Q
                    notq()
                if d in rcyclolookup:
                    return input_to_subfield(rcyclolookup[d])
                else:
                    raise SearchParsingError("Subfield %s is not available." % F)
                f = pari.polcyclo(d)
                return input_to_subfield(str(f))
                # Want polcyclo here
                raise SearchParsingError("%s is not in the database." % F)
            f = pari.polcyclo(d)
            return input_to_subfield(str(f))
    raise SearchParsingError("It is not a valid field nickname or label, or a defining polynomial.")

@search_parser  # see SearchParser.__call__ for actual arguments when calling
def parse_subfield(inp, query, qfield):
    sf = input_to_subfield(inp)
    if sf:  # Might return none
        query[qfield] = {"$contains": sf}

@search_parser  # see SearchParser.__call__ for actual arguments when calling
def parse_nf_string(inp, query, qfield):
    query[qfield] = nf_string_to_label(inp)

@search_parser
def parse_kerpol_string(inp, query, qfield):
    label = nf_string_to_label(inp)
    from lmfdb import db
    query[qfield] = db.nf_fields.lookup(label, projection='coeffs')

def pol_string_to_list(pol, deg=None, var=None):
    if var is None:
        from lmfdb.hilbert_modular_forms.hilbert_field import findvar

        var = findvar(pol)
        if not var:
            var = "a"
    try:
        pol = PolynomialRing(QQ, var)(str(pol))
    except TypeError:
        raise SearchParsingError("Input not recognized as a polynomial.")
    if deg is None:
        fill = 0
    else:
        fill = deg - pol.degree() - 1
    return [str(c) for c in pol.coefficients(sparse=False)] + ["0"] * fill

# see SearchParser.__call__ for actual arguments when calling
@search_parser(pass_name=True)
def parse_nf_elt(inp, query, name, qfield, field_label):
    if field_label is None:
        raise SearchParsingError("You must specify a field when searching by %s" % name)
    deg = int(field_label.split(".")[0])
    if "," in inp:
        collapse_ors(["$or", [{qfield: pol_string_to_list(f, deg=deg)} for f in inp.split(",")]], query)
    else:
        query[qfield] = pol_string_to_list(inp, deg=deg)

# see SearchParser.__call__ for actual arguments when calling
@search_parser(pass_name=True, clean_info=True)
def parse_nf_jinv(inp, query, name, qfield, field_label):
    if field_label is not None:
        field_label = field_label.strip()
    if field_label == "2.2.5.1":
        inp = inp.replace("phi", "a")
    elif field_label == "2.0.4.1":
        inp = inp.replace("i", "a")
    if "a" not in inp and field_label is None:
        if QQ_RE.match(inp):
            query[qfield] = {"$regex": "^%s(,0)*$" % QQ(inp)}
        elif QQ_LIST_RE.match(inp):
            opts = [{qfield: {"$regex": "^%s(,0)*$" % QQ(x)}} for x in inp.split(",")]
            collapse_ors(["$or", opts], query)
        else:
            raise SearchParsingError("With no field specified, it needs to be a rational number or comma separated list of rationals.")
    elif field_label is None:
        raise SearchParsingError("You must specify a field when searching by %s" % name)
    else:
        deg = int(field_label.split(".")[0])
        if "," in inp:
            collapse_ors(["$or", [{qfield: ",".join(pol_string_to_list(f, deg=deg))} for f in inp.split(",")]], query)
        else:
            query[qfield] = ",".join(pol_string_to_list(inp, deg=deg))

# see SearchParser.__call__ for actual arguments when calling
@search_parser(clean_info=True)
def parse_container(inp, query, qfield):
    inp = inp.replace("T", "t")
    format_ok = re.match(r"^\d+(t\d+)?$", inp)
    if format_ok:
        query[qfield] = str(inp)
    else:
        raise SearchParsingError("You must specify a permutation representation, such as 6T13")

@search_parser  # see SearchParser.__call__ for actual arguments when calling
def parse_hmf_weight(inp, query, qfield):
    parallel_field, normal_field = qfield
    try:
        query[parallel_field] = int(inp)
    except ValueError:
        try:
            query[normal_field] = str(split_list(inp))
        except ValueError:
            raise SearchParsingError("It must be either an integer (parallel weight) or a comma separated list of integers enclosed in brackets, such as 2, or [2,2], or [2,4,6].")
