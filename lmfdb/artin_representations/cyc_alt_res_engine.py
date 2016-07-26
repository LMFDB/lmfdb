# Computes the coefficients of Artin L-functions in the so-called CYC, ALT and RES types.
# Artin L-functions' local information is provided by Tim Dokchitser
# Each Artin representation stores a table matching conjugacy classes of the Galois group to the
# corresponding local factor. The question is thus to identify the conjugacy class that is involved.
# This is done in one of 4 ways:
#           - if the prime is "hard" (a finite superset of the bad primes), use stored information (index of conjugacy class).
#               List of hard prime is provided for each Artin representation, but Tim is not quite sure if it is complete each time.
#               This case is handled in math_classes.py
# This file handles the other 3 cases:
#           - if "CYC", the cycle type is enough to determine the conjugacy class.
#           - if "ALT", use Serre's trick to distinguish which of two conjugacy classes is the right one.
#               Compute a particular invariant alpha, and use a precomputed table (dependent on the Galois group) whose keys are polynomials.
#               Exactly one of these polynomials will cancel alpha (if there was more than one, this should have been an additional hard prime...),
#               the value of the associated key is the index of the conjugacy class.
#           - if "RES", the general idea is very similar to "ALT", except that the invariant is differently computed, and another table is to be used.
#
# The "HardPrimes" case is implemented in math_classes.py
# This implements the "CYC", "ALT" and "RES" cases.

# This is based on Tim Dokchitser's desc.pdf file, with title Algorithm to compute Frobenius elements

# The only function defined here useful to the outside is
# from_cycle_type_to_conjugacy_class_index_dict
# This takes as argument the defining polynomial of the field and the frobenius resolvent information originally provided by Tim
# It outputs a dictionary,
#       whose keys are the various cycle_types
#       and values are functions, themselves with
#                           input a prime p,
#                           output the corresponding conjugacy class index

# The goal of making it this way is to have maximal reuse of computations between primes
# The function from_cycle_type_to_conjugacy_class_index_dict is called
# once for each number field (and thus once for each artin representation)

# Author: Paul-Olivier Dehaye

from sage.all import Integer, lcm, PolynomialRing, Integers, FiniteField


def polynomial_conjugacy_class_matcher_fn(input):
    """ Given an input of the form
        [{"RootOf":["0","1"], "ConjugacyClass":3}, {"RootOf":["-7","1"], "ConjugacyClass":4}]
        returns a function that
            - takes an argument alpha
            - matches alpha as a root to one of the 'RootsOf'
            - returns the value in the corresponding 'ConjugacyClass'
    """
    P = PolynomialRing(Integers(), "x")
    fn_cc_pairs = []
    for d in input:
        pol = P([Integer(int_val) for int_val in d["RootOf"]])
        fn_cc_pairs.append((pol, d["ConjugacyClass"]))

    def polynomial_conjugacy_class_matcher(alpha):
        """
        A function that has an internal list of pairs (pol, return_val). Given alpha, finds the pol that it is a root of and returns
        the associated return_val
        """
        for pol_fn, conjugacy_class_index in fn_cc_pairs:
            if pol_fn(alpha) == 0:
                return conjugacy_class_index
        raise AssertionError("alpha = %s is supposed to be root of one of %s" % (alpha, input))
    return polynomial_conjugacy_class_matcher


def powers_sum(r, powers, p):
    return sum([r ** (p ** j) for j in powers])


def alpha_res_fn(data):
    powers = data["Powers"]
    P = PolynomialRing(Integers(), "x")
    gamma_polynomial = P(data["Resolvent"])

    def alpha_res(roots, p):
        """ Computes invariant alpha in the 'RES' case
        """
        return sum(gamma_polynomial(r) * powers_sum(r, powers, p) for r in roots)
    return alpha_res


def frobenius_permutation(roots, p):
    """ Returns the permutation associated to the action of Frobenius on the roots
    """
    try:
        sigma = [1 + roots.index(roots[i] ** p) for i in range(len(roots))]
    except ValueError:
        # .index fails somewhere
        raise ValueError("Frobenius does not seem to permute the roots")
    return sigma


def are_conjugate_in_alternating(rho, sigma):
    """ Tests whether rho and sigma are conjugate in the corresponding alternating group.
        Does not assume rho and sigma are the same length.
    """
    # This seems 10x faster than calling corresponding IsConjugate on corresponding gap objects.
    # Only used in the ALT case

    rho_cycle_type = rho.cycle_type()
    sigma_cycle_type = sigma.cycle_type()
    if sum(rho_cycle_type) != sum(sigma_cycle_type):
        return False
    if rho_cycle_type != sigma_cycle_type:
        return False

    # Conjugacy classes in A_n are the same as in S_n, except when all the cycles are of odd and different lengths
    # In that case, S_n conjugacy classes split up in 2 A_n conjugacy classes
    if len(set(sigma_cycle_type)) != len(sigma_cycle_type):
        return True
    for x in sigma_cycle_type:
        if x % 2 == 0:
            return True

    # Now we know we only have odd length cycles, all different
    rho_augmented_cycles = sorted([(len(x), x) for x in rho.cycle_tuples()])
    sigma_augmented_cycles = sorted([(len(x), x) for x in sigma.cycle_tuples()])
    # Because sort bases itself first on the first argument of the tuple, the
    # cycles match up with their lengths
    tmp = [0 for i in range(sum(rho_cycle_type))]
    for i in range(len(rho_augmented_cycles)):
        rho_tuple = rho_augmented_cycles[i][1]
        sigma_tuple = sigma_augmented_cycles[i][1]
        for j in range(len(rho_tuple)):
            tmp[rho_tuple[j] - 1] = sigma_tuple[j]
    from sage.all import Permutation
    sig = Permutation(tmp).signature()
    if sig == -1:
        return False
    else:
        return True


def alpha_alt_fn(data):
    try:
        from sage.all import AlternatingGroup, Permutation
        alternating_group = AlternatingGroup(len(data))
        data_perm = Permutation(alternating_group(data))
    except TypeError:
        raise TypeError("The data element given is not an element of the alternating group")

    def alpha_alt(roots, p):
        """ Computes invariant alpha in the 'ALT' case
        """
        from sage.all import prod, Permutation
        tmp = prod(roots[i] - roots[j] for i in range(len(roots)) for j in range(i))
        try:
            frob_perm = Permutation(alternating_group(frobenius_permutation(roots, p)))
        except TypeError:
            raise TypeError("The Frobenius element does not generate an element of the alternating group")

        sign = -(-1) ** are_conjugate_in_alternating(frob_perm, data_perm)
        return tmp * sign
    return alpha_alt


def roots_finite_field_fn(cycle_type, defining_polynomial):
    d = lcm(cycle_type)

    def roots_finite_field(p):
        Fq = FiniteField(p ** d, "a")
        Fq_X = PolynomialRing(Fq, "x")
        pol = Fq_X(defining_polynomial)
        # print "Got cycle_type", cycle_type
        # print "I compute the polynomial to be ", pol
        # print "I am looking for solution over ", Fq_X
        roots = pol.roots(multiplicities=False)
        assert len(roots) == len(defining_polynomial) - 1
        return roots
    return roots_finite_field


def RES_from_cycle_type_to_conjugacy_class_index_fn(technique, defining_polynomial):
    cycle_type = tuple(map(Integer, technique["CycleType"]))
    data = technique["Data"]
    classes = technique["Classes"]

    # print "RES", cycle_type, data, technique

    roots_finite_field = roots_finite_field_fn(cycle_type, defining_polynomial)
    alpha_res = alpha_res_fn(data)
    polynomial_conjugacy_class_matcher = polynomial_conjugacy_class_matcher_fn(classes)

    def RES_from_cycle_type_to_conjugacy_class_index(p):
        # print "RESp", cycle_type, data, technique, p

        roots = roots_finite_field(p)
        # print "The roots of ", defining_polynomial, " over ",p," are ", roots

        alpha = alpha_res(roots, p)
        # print "alpha is ", alpha
        return polynomial_conjugacy_class_matcher(alpha)
    # raise NotImplementedError, "Do not know how to construct the Euler polynomial when type is RES"
    return RES_from_cycle_type_to_conjugacy_class_index


def ALT_from_cycle_type_to_conjugacy_class_index_fn(technique, defining_polynomial):
    cycle_type = tuple(map(Integer, technique["CycleType"]))
    data = technique["Data"]
    classes = technique["Classes"]

    # print "ALT", cycle_type, data, technique

    roots_finite_field = roots_finite_field_fn(cycle_type, defining_polynomial)
    alpha_alt = alpha_alt_fn(data)
    polynomial_conjugacy_class_matcher = polynomial_conjugacy_class_matcher_fn(classes)

    def ALT_from_cycle_type_to_conjugacy_class_index(p):
        # print "ALTp", cycle_type, data, technique, p
        roots = roots_finite_field(p)
        alpha = alpha_alt(roots, p)
        return polynomial_conjugacy_class_matcher(alpha)
    # raise NotImplementedError, "Do not know how to construct the Euler polynomial when type is ALT"
    return ALT_from_cycle_type_to_conjugacy_class_index


def CYC_from_cycle_type_to_conjugacy_class_index_fn(technique):
    return lambda p: technique["Classes"]


def from_cycle_type_to_conjugacy_class_index_dict(defining_polynomial, frobenius_resolvents):
    """
        This function takes as input:
            - the defining polynomial of the number field (in the [c_0, c_1, ... c_d] format)
            - the frobenius resolvent data, pulled straight from the database
        Reorganizes this data, mostly, to output a dictionary,
            - with keys: the cycle types (as tuples)
            - with values: the functions of primes that return the cycle index
    """
    # print "Constructing the dict ",defining_polynomial, frobenius_resolvents
    output_dict = dict()
    for technique in frobenius_resolvents:
        # Each technique will lead to different functions
        if technique["Algorithm"] == "CYC":
            tmp = CYC_from_cycle_type_to_conjugacy_class_index_fn(
                technique)   # a bit convoluted but nice to have the same structure, helps understand
        elif technique["Algorithm"] == "RES":
            tmp = RES_from_cycle_type_to_conjugacy_class_index_fn(technique, defining_polynomial)
        elif technique["Algorithm"] == "ALT":
            tmp = ALT_from_cycle_type_to_conjugacy_class_index_fn(technique, defining_polynomial)
        else:
            raise ValueError("Only three cases are possible: 'CYC', 'RES' and 'ALT'")
        cycle_type = tuple(map(Integer, technique["CycleType"]))
        output_dict[cycle_type] = tmp
    return output_dict
