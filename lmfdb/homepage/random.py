from ..app import is_beta

def get_random():
    if is_beta():
        routes = ["ModularForm/GL2/Q/holomorphic/",
                    "ModularForm/GL2/Q/Maass/",
                    "ModularForm/GL2/TotallyReal/",
                    "ModularForm/GL2/ImaginaryQuadratic/",
                    "ModularForm/GSp/Q/",
                    "EllipticCurve/Q/",
                    "EllipticCurve/",
                    "Genus2Curve/Q/",
                    "HigherGenus/C/Aut/",
                    "Variety/Abelian/Fq/",
                    "Belyi/",
                    "NumberField/",
                    "LocalNumberField/",
                    "Character/Dirichlet/",
                    "ArtinRepresentation/",
                    "Motive/Hypergeometric/Q/",
                    "GaloisGroup/",
                    "SatoTateGroup/",
                    "Lattice/"
                ]
    else:
        routes = ["ModularForm/GL2/Q/holomorphic/",
                    "ModularForm/GL2/Q/Maass/",
                    "ModularForm/GL2/TotallyReal/",
                    "ModularForm/GL2/ImaginaryQuadratic/",
                    "ModularForm/GSp/Q/",
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
    route = routes[randint(0,len(routes)-1)]
    return redirect(route+"random", 404)
