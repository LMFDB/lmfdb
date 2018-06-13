R0 = PolynomialRing(QQ,'nu')
R = PolynomialRing(R0,2,'x,y')
F = FractionField(R)
latex(F(map_str))

R = PolynomialRing(QQ, 3, "x,y,nu")
x,y,nu = R.gens()
F = FractionField(R)
crv_str = sample_galmap['curve']
sides = crv_str.split("=")
lhs = latex(F(sides[0]))
rhs = latex(F(sides[1]))
eqn_str = lhs + '=' + rhs

R = PolynomialRing(QQ, 3, "x,y,nu")
x,y,nu = R.gens()
F = FractionField(R)
crv_str = sample_galmap['curve']
sides = crv_str.split("=")
lhs_str = sides[0]
rhs_str = sides[1]
lhs = F(lhs_str)
rhs = F(rhs_str)
lhs_latex = latex(lhs)
rhs_latex = latex(rhs)
eqn_str = lhs_latex + '=' + rhs_latex
