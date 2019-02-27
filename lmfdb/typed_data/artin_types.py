from type_generation import String, Array, Dict, Int, Anything

from standard_types import PolynomialAsString, PermutationAsList,\
    TooLargeInt, LabelString, FiniteSequence, FiniteSet, PrimeIndexedSequence, \
    PolynomialAsSequenceInt, PolynomialAsSequenceTooLargeInt

from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.integer_ring import ZZ


Polynomial_X_QQ_AsString = PolynomialAsString(PolynomialRing(QQ, "x", sparse=False))
Polynomial_X_ZZ_AsString = PolynomialAsString(PolynomialRing(ZZ, "x", sparse=False))
Polynomial_a_ZZ_AsString = PolynomialAsString(PolynomialRing(ZZ, "a", sparse=False))

Dokchitser_AlgebraicNumber_MinPol = PolynomialAsString(
    PolynomialRing(PolynomialRing(ZZ, "x", sparse=False), "a", sparse=False))


class Dokchitser_AlgorithmLabel(LabelString):
    pass
#### Not precise ####


class Custom_GroupLabel(LabelString):
    pass

Dokchitser_Character = FiniteSequence(Anything)
#### Not precise ####


class IndexAt1(Int):
    pass

LenPair = Dict({
    "len": Int,
    "val": TooLargeInt
})

Galois_Conjugate = Dict(
    {
    	"LocalFactors": FiniteSequence(Anything),
    	"Character": Anything,
    	"Sign": Int,
    	"HardFactors": FiniteSequence(IndexAt1),
    	"GalOrbIndex": Int
    })


Dokchitser_ArtinRepresentation = Dict({
    "_id": Anything,
    "Baselabel": String,
    "Container": Anything,
    "Dim": Int,
    "Indicator": Int,
    "Conductor": TooLargeInt,
    "HardPrimes": FiniteSequence(TooLargeInt),
    "BadPrimes": FiniteSequence(TooLargeInt),
    "NFGal": FiniteSequence(TooLargeInt),
    "CharacterField": Int,
    "Galt": Int,
    "Galn": Int,
    "Hide": Int,
    "GaloisConjugates": FiniteSequence(Galois_Conjugate),
    "GalConjSigns": FiniteSequence(Int)
})


class CycleType(FiniteSequence(Int)):
    pass

Dokchitser_FrobResolvent = Dict(
    {
        "CycleType": CycleType,
        "Algorithm": Dokchitser_AlgorithmLabel,
        "Data": Anything,
        "Classes": Anything
    })

ArtinRepresentation_Short = Dict(
    {
        "Baselabel": String,
        "GalConj": Int,
        "CharacterField": Int,
        "Character": Dokchitser_Character
    })

Dokchitser_ConjugacyClass = Dict(
    {
        "Order": Int,
        "Size": TooLargeInt,
        "Representative": PermutationAsList
    })


Dokchitser_NumberFieldGaloisGroup = Dict({
    "_id": Anything,
    "ArtinReps": FiniteSequence(ArtinRepresentation_Short),
    "ComplexConjugation": Int,
    "ConjClasses": FiniteSequence(Dokchitser_ConjugacyClass),
    "FrobResolvents": Array(Dokchitser_FrobResolvent),
    "Frobs": PrimeIndexedSequence(Int),
    "G-Gens": FiniteSet(PermutationAsList),
    "G-Name": Custom_GroupLabel,
    "Polynomial": FiniteSequence(int),
    "QpRts": FiniteSequence(PolynomialAsSequenceTooLargeInt),
    "QpRts-minpoly": PolynomialAsSequenceInt,
    "QpRts-p": Int,
    "QpRts-prec": Int,
    "Size": TooLargeInt,
    "TransitiveDegree": Int
})
