def mu_nu(hodge, signature):
    """
        Computes the mu and nu given hodge numbers and signature
    """
    #hodge = [int(a) for a in hodge.split(',')]
    motivic_weight = len(hodge) - 1
    hodge_index = lambda p: hodge[p]
            # The hodge number p,q

    q = lambda p: motivic_weight - p

    assert len(hodge) == motivic_weight + 1

    tmp = [[(q(p) - p) / 2.] * int(hodge_index(p)) for p in range((motivic_weight + 1) / 2)]  # This division does some flooring!!!
    nu = sum(tmp, [])

    if motivic_weight % 2 == 0:
        a = (hodge_index((motivic_weight) / 2) - abs(signature)) / 2
        tmp = [0] * a
        nu += tmp

    if signature <= 0:
        mu = [1] * abs(signature)
    else:
        mu = [0] * abs(signature)

    return mu, nu
