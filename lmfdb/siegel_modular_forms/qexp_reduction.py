# -*- coding: utf-8 -*-
"""
Reduction of the indices of Fourier coefficients of paramodular forms, as used to store them
(smf_lmfdb/db_tables/fourier_tables.py and qexp_from_eigenforms.reduce_signed).

An index T = [a, b, c] with N | c is the matrix [[a, b/2], [b/2, c]], i.e. the binary quadratic
form a x^2 + b xy + c y^2.  For U in GL(2, Z) with N | U[0, 1], a(T[U]) = det(U)^k a(T).  A class
is stored under (qf_legendre, qf_tag): the reduced form of T and a tag in P^1(Z/N) minimized over
the automorphisms of the reduced form; reduce_signed also returns the sign det(U) relating T to
the class (0 when both signs occur, so that a(T) = 0 in odd weight).
"""
from sage.all import ZZ, Matrix, MatrixSpace, BinaryQF, pari


def P1N_lex_minimize(vec, level):
    a = vec[0, 0] % level
    if a != 0:
        d = a.gcd(level) % level
        u = (a // d).inverse_mod(level // d)
        while not u.gcd(level) == 1:
            u += (level // d)
        res = (u * vec) % level
        if d != 1:
            mults = [(1 + (level // d) * i) for i in range(d)
                     if ZZ(level).gcd(1 + (level // d) * i) == 1]
            b = res[1, 0]
            m = b
            for u in mults:
                m = min(m, (u * b) % level)
            res[1, 0] = m
    else:
        b = vec[1, 0] % level
        d = b.gcd(level)
        res = Matrix([[0], [d]])
    return res


def reduce_signed(abc, N):
    """For a positive definite index (a, b, c), with the form a x^2 + b xy + N c y^2:
    ((a', b', c'), tag, sign) as stored, with a(T) = sign^k a(class)."""
    a, b, c = abc
    S = MatrixSpace(ZZ, 2, 2)
    qf = BinaryQF(a, b, N * c)
    pol = qf.reduced_form().polynomial()
    x, y = pol.parent().gens()
    ap, bp, cp = pol.coefficient(x**2), pol.coefficient(x * y), pol.coefficient(y**2)
    m1 = S([2 * a, b, b, 2 * N * c])
    m2 = S([2 * ap, bp, bp, 2 * cp])
    u = S(pari.qfisom(m2, m1))
    auts = [S(v) for v in pari.qfauto(m2)[1]]
    key = lambda v: (int(v[0, 0]), int(v[1, 0]))
    v0 = P1N_lex_minimize(S(u ** (-1)) * Matrix([[0], [1]]), N)
    dets = {key(v0): {1}}
    todo = [(v0, 1)]
    while todo:
        v, dv = todo.pop()
        for m in auts:
            w = P1N_lex_minimize(m * v, N)
            dw = dv * int(m.det())
            if dw not in dets.setdefault(key(w), set()):
                dets[key(w)].add(dw)
                todo.append((w, dw))
    tag = min(dets)
    ds = dets[tag]
    sign = 0 if len(ds) == 2 else int(u.det()) * ds.pop()
    return (int(ap), int(bp), int(cp)), tag, sign
