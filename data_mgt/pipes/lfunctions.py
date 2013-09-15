from lmfdb.lfunctions.Lfunction import *
from pipes import populator

def lf_data(L):
    print "Computing with ", L
    first_zeroes = L.compute_realistic_zeros(upper_bound = 20)
    data = {"Ltype": L.Ltype(), 
            "selfdual" : L.selfdual, 
            "first_zeroes": map(float, first_zeroes),
            "degree":  L.degree,
            "values" : [
                [.5, float(L.sageLfunction.value(.5))],
                [ 1, float(L.sageLfunction.value( 1))] 
                ]
            }
    try:
        data.update( { "Lkey" : L.Lkey() } )
    except:
        pass
    print "Done with ", L
    return data


from pipes import populator

def ec_l_iterator(**kwargs):
    from elliptic_curves import ec_isogeny_label_iterator
    ec_labels = ec_isogeny_label_iterator(**kwargs)
    for ec_label in ec_labels:
        L_E = Lfunction_EC_Q(label = ec_label)
        tmp = lf_data(L_E)
        print tmp
        yield tmp

def artin_l_iterator(**kwargs):
    from artin_representations import artin_label_iterator
    artin_labels = artin_label_iterator(**kwargs)
    for artin_label in artin_labels:
        L_artin = ArtinLfunction(**artin_label)
        tmp = lf_data(L_artin)
        print tmp
        yield tmp



up = populator("test","testEC3")