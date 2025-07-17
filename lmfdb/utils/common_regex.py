
"""
Common regular expressions used in various places
"""

import re

TERM_RE = r"(\+|-)?(\d*[A-Za-z]|\d+\*[A-Za-z]|\d+)(\^\d+)?"
STERM_RE = r"(\+|-)(\d*[A-Za-z]|\d+\*[A-Za-z]|\d+)(\^\d+)?"
POLY_RE = re.compile(TERM_RE + "(" + STERM_RE + ")*")
POLYLIST_RE = re.compile(r"(\[|)" + POLY_RE.pattern + r"," + POLY_RE.pattern + r"(\]|)")
ZLIST_RE = re.compile(r"\[(|((|(\+|-))\d+)*(,(|(\+|-))\d+)*)\]")
ZLLIST_RE = re.compile(r"(\[|)" + ZLIST_RE.pattern + r"," + ZLIST_RE.pattern + r"(\]|)")
G1_LOOKUP_RE = re.compile(r"(" + "|".join(elt.pattern for elt in [POLY_RE, POLYLIST_RE]) + r")")
G2_LOOKUP_RE = re.compile(r"(" + "|".join(elt.pattern for elt in [POLY_RE, POLYLIST_RE, ZLIST_RE, ZLLIST_RE]) + r")")
