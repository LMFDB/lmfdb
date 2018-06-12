R.<x,y,nu> = PolynomialRing(QQ, 3)
F = FractionField(R)
crv_str = sample_galmap['curve']
sides = crv_str.split("=")
lhs_str = sides[0]
rhs_str = sides[1]
lhs = latex(lhs_str)
rhs = latex(rhs_str)
