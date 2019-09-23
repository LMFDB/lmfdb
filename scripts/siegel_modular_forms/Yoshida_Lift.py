# This script was created using the 2012 paper of Johnson-Leung and Roberts. 

# INPUTS:
# F is a real quadratic number field
# hhecke_evals is a dictionary of eigenvalues of a hilbert modular form over F. It should contain primes up to norm of primeprec**2
# hweight is the pair even integers that gives the weight of the hilbert modular form, no reason to default to [2,2]
# primeprec is the uper bound on the size of the rational primes which will have eigenvalues calculated

# OUTPUTS:
# Paramodular Level: An int
# Paramodular Weight: an Int
# T(1,1,p,p): a dictionary which has keys all the primes up to primeprec, and has values which are hecke eigenvalues
# T(1,p,p,p^2): See above

from sage.all import prime_range


def Yoshida_Lift(F, hhecke_evals, hlevel, hweight = [2,2], primeprec = 100):
	weight = (hweight[1] + 2)/2
	level = F.disc()**2*hlevel.norm()
	lam = {}
	mu = {}
	for p in prime_range(primeprec):
		v = level.valuation(p)
		if v == 0:
			if len(F.primes_above(p)) == 1:
				lam[p] = 0
				mu[p] = p**(2*(weight -3))*(-p**2 - p*hhecke_evals[F.prime_above(p)] - 1)
			else:
				lam[p] = p**((weight  - 3))*p*(hhecke_evals[F.primes_above(p)[0]] + hhecke_evals[F.primes_above(p)[1]])
				mu[p] = p**(2*(weight - 3))*(p**2 + p*hhecke_evals[F.primes_above(p)[0]]*hhecke_evals[F.primes_above(p)[1]] - 1)
		if v == 1:
			if hlevel.valuation(F.primes_above(p)[0]) == 1:
				po = F.primes_above(p)[0]
				pt = F.primes_above(p)[1]
			else:
				pt = F.primes_above(p)[0]
				po = F.primes_above(p)[1]
			lam[p] =  p**((weight  - 3))*(p*hhecke_evals[po] + (p + 1)*hhecke_evals[pt])
			mu[p] = p**(2*(weight  - 3))*(p*hhecke_evals[F.primes_above(p)[0]]*hhecke_evals[F.primes_above(p)[1]])
		else:
			if len(F.primes_above(p)) == 2:
				lam[p] = p**((weight  - 3))*p*(hhecke_evals[F.primes_above(p)[0]] + hhecke_evals[F.primes_above(p)[1]])
				if hlevel.valuation(F.primes_above(p)[0])*hlevel.valuation(F.primes_above(p)[1]) == 0:
					mu[p] = 0
				else:
					mu[p] = p**(2*(weight  - 3))*(-p**2)
			else:
				if F.ideal(p).valuation(F.prime_above(p)) == 2:
					lam[p] = p*hhecke_evals[F.prime_above(p)]
					if hlevel.valuation(F.prime_above(p)) == 0:
						mu[p] = 0
					else:
						mu[p] = p**(2*(weight  - 3))*(-p**2)
				else:
					lam[p] = 0
					mu[p] = p**(2*(weight  - 3))*(-p**2-p*hhecke_evals[F.prime_above(p)])
	return {'paramodular_level':level, 'weight':weight, 'T(1,1,p,p)':lam, 'T(1,p,p,p^2)':mu}
	#return lam,mu,level,weight
