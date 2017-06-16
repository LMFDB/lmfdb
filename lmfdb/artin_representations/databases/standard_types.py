from type_generation import String, Array, Int

def PolynomialAsString(convention):
    class ParametrizedPolynomialAsString(String):
        def sage(self):
            return convention(self)

        def latex(self, letter=convention.variable_name()):
            return self.sage().change_variable_name(letter)._latex_()

    return ParametrizedPolynomialAsString


class PermutationAsList(Array(Int)):
    def cycle_string(self):
        from sage.combinat.permutation import Permutation
        return Permutation(self).cycle_string()


class TooLargeInt(String):
    pass


class LabelString(String):
    pass


FiniteSequence = Array
FiniteSet = Array

InfiniteSequence = Array


class PolynomialAsSequenceInt(FiniteSequence(Int)):
    from sage.rings.all import RationalField

    def sage(self, var="x", base_field=RationalField()):
        from sage.rings.all import PolynomialRing, QQ
        PP = PolynomialRing(QQ, var)
        return PP(self)

    def latex(self, letter="x"):
        return self.sage(var=letter)._latex_()


class PowerSeriesAsSequenceInt(InfiniteSequence(Int)):
    pass


class PolynomialAsSequenceTooLargeInt(FiniteSequence(TooLargeInt)):
    from sage.rings.all import RationalField

    def sage(self, var="x", base_field=RationalField()):
        from sage.rings.all import PolynomialRing, QQ, Integer
        PP = PolynomialRing(QQ, var)
        return PP([Integer(val) for val in self])

    def latex(self, letter="x"):
        return self.sage(var=letter)._latex_()


class GAP_GroupLabel(LabelString):
    pass


def PrimeIndexedSequence(x):
    return Array(x)


def AlgebraicNumberPolynomialString(pol_as_string_convention):
    class ParametrizedAlgebraicNumberPolynomialString(String):
        pass
    return ParametrizedAlgebraicNumberPolynomialString

