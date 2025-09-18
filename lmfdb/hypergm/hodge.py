from itertools import repeat
from sage.rings.integer import Integer


def mu_nu(hodge, signature) -> tuple[list, list]:
    """
    Compute ``mu`` and ``nu`` given Hodge numbers and signature.

    Here ``hodge[p]`` is the Hodge number `h_{p,q}`.
    """
    motivic_weight = Integer(len(hodge) - 1)

    nu = []
    for p in range((motivic_weight + 1) // 2):
        q_p = (motivic_weight - 2 * p) / 2
        nu.extend(repeat(q_p, int(hodge[p])))
    if not motivic_weight % 2:
        a = (hodge[motivic_weight // 2] - abs(signature)) // 2
        nu.extend(repeat(0, a))

    if signature <= 0:
        mu = [1] * abs(signature)
    else:
        mu = [0] * abs(signature)

    return mu, nu
