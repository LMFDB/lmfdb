from lmfdb.lfunctions.Lfunction import Lfunction_EC_Q, ArtinLfunction, Lfunction_Dirichlet, HypergeometricMotiveLfunction

def lf_data(L):
    first_zeroes = L.compute_quick_zeros(upper_bound = 20)
    data = {"Ltype": L.Ltype(),
            "selfdual" : L.selfdual, 
            "first_zeroes": map(float, first_zeroes),
            "degree":  L.degree,
            "values" : [],
            "farmer": {
                    "degree": int(L.degree),
                    "mu": map(float, L.mu_fe), 
                    "nu": map(float, L.nu_fe),
                    "N": int(L.level)
            }
            }
    try:
        data["object"] = L.source_object().label()
    except:
        pass
    for location in [0.5, 1.]:
        try:
            data["values"].append([location, float(L.sageLfunction.value(location))])
        except TypeError:       # The conversion failed
            pass
    try:
        data.update( { "Lkey" : L.Lkey() } )
    except:
        pass
    return data


from pipes import populator

def ec_l_iterator(min_conductor = 10, max_conductor = 20, **kwargs):
    from elliptic_curves import ec_isogeny_label_iterator
    ec_labels = ec_isogeny_label_iterator(min_conductor, max_conductor)
    for ec_label in ec_labels:
        print ec_label
        L_E = Lfunction_EC_Q(label = ec_label)
        yield L_E

def artin_l_iterator(signed = False, min_conductor = 1, max_conductor = 20):
    from artin_representations import artin_label_iterator
    artin_labels = artin_label_iterator(max_conductor = max_conductor, min_conductor = min_conductor)
    for artin_label in artin_labels:
        L_artin = ArtinLfunction(**artin_label)
        if signed:
            if L_artin.sign == 0:    # This means no sign is known
                continue
        print artin_label
        yield L_artin

def dirichlet_l_iterator(min_conductor = 2,  max_conductor = 10**5):
    from dirichlet_conrey import DirichletGroup_conrey
    for modulus in filter(lambda _:_%4 != 2, xrange(min_conductor, max_conductor)):
        print modulus
        for c in DirichletGroup_conrey(modulus).primitive_characters():
            L_dirichlet = Lfunction_Dirichlet(charactermodulus = modulus, characternumber = c.number())
            yield L_dirichlet

def hypergeometric_l_iterator(min_conductor = 2, max_conductor = 10**5):
    from hypergeometric import hypergeometric_label_iterator
    for hgm_label in hypergeometric_label_iterator(min_conductor = min_conductor, max_conductor = max_conductor):
        print hgm_label
        L_hgm = HypergeometricMotiveLfunction(label = hgm_label)
        yield L_hgm


up_ec = populator("test","l_ec")
up_artin = populator("test","l_artin")
up_dirichlet = populator("test", "l_dirichlet")
up_hypergeometric = populator("test", "l_hgm")
