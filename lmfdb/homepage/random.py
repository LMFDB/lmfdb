from lmfdb.app import is_beta, app
from flask import redirect
from sage.all import randint

def random_url():
    routes = [
            "L/",
            "L/",
            "L/",
            "ModularForm/GL2/Q/holomorphic/",
            "ModularForm/GL2/Q/Maass/",
            "ModularForm/GL2/TotallyReal/",
            "ModularForm/GL2/ImaginaryQuadratic/",
            "EllipticCurve/Q/",
            "EllipticCurve/",
            "Genus2Curve/Q/",
            "HigherGenus/C/Aut/",
            "Variety/Abelian/Fq/",
            "NumberField/",
            "LocalNumberField/",
            "Character/Dirichlet/",
            "ArtinRepresentation/",
            "GaloisGroup/",
            "SatoTateGroup/"
            ]
    if is_beta():
        routes += [
                "ModularForm/GSp/Q/",
                "Belyi/",
                "Motive/Hypergeometric/Q/",
                "Lattice/"
                ]
    route = routes[randint(0,len(routes)-1)]
    if route == "ModularForm/GL2/Q/holomorphic/":
        ind = randint(0,1)
        if ind == 0:
            route += "random"
        else:
            route += "random_space"
    elif route == "Motive/Hypergeometric/Q/":
        ind = randint(0,1)
        if ind == 0:
            route += "random_motive"
        else:
            route += "random_family"
    else:
        route += "random"
    return route

@app.route("/random")
def go_random():
    url = random_url()
    return redirect(url)
