artin_location = ("limbo","tim_artin_02")
galois_group_location = ("limbo","tim_nfgal_02")

from type_generation import String, Array, Dict, Int, Anything, Float

from standard_types import PolynomialAsString, PermutationAsList,\
    TooLargeInt, LabelString, FiniteSequence, FiniteSet, PrimeIndexedSequence, AlgebraicNumberPolynomialString, \
    PolynomialAsString, AlgebraicNumberString_Root, PolynomialAsSequenceInt, PolynomialAsSequenceTooLargeInt
    
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.integer_ring import ZZ


Polynomial_X_QQ_AsString = PolynomialAsString(PolynomialRing(QQ,"x", sparse=False))
Polynomial_X_ZZ_AsString = PolynomialAsString(PolynomialRing(ZZ,"x", sparse=False))
Polynomial_a_ZZ_AsString = PolynomialAsString(PolynomialRing(ZZ, "a", sparse = False))

from bind_collection import bind_collection

Dokchitser_AlgebraicNumber_MinPol = PolynomialAsString(PolynomialRing(PolynomialRing(ZZ,"x", sparse = False),"a", sparse = False))
Dokchitser_AlgebraicNumber_Root = AlgebraicNumberString_Root
    
class Dokchitser_AlgorithmLabel(LabelString):
    pass
#### Not precise ####

class Custom_GroupLabel(LabelString):
    pass

class BadFactor(Array(Int)):
    pass
#### Not precise ####

Dokchitser_Character = FiniteSequence(Anything)
#### Not precise ####

class IndexAt1(Int):
    pass

Dokchitser_ArtinRepresentation = Dict({
        "_id":              Anything,
        "Dim" :             Int,                                #
        "Indicator":        Int,                                #
        "Conductor" :       TooLargeInt,                        #
        "BadFactors":       FiniteSequence(IndexAt1),           #   
        "BadPrimes":        FiniteSequence(TooLargeInt),        #
        "LocalFactors":     FiniteSequence(Anything),
                        # actually, not Anything but PolynomialAsSequence(PolynomialCyclotomic)
        "DBIndex" :         IndexAt1,        # Starting at 1    #
        "NFGal" :           FiniteSequence(Anything),           #
        "Character" :       Anything,
        "Sign":             Int,                                #
        "CharacterField":   Int                                 #
    })


class CycleType(FiniteSequence(Int)):
    pass
    
Dokchitser_FrobResolvent = Dict(
            {
                "CycleType":    CycleType,
                "Algorithm":    Dokchitser_AlgorithmLabel,
                "Data":         Anything,
                "Classes":      Anything
            })

Dokchitser_ArtinRepresentation_Short = Dict(
            {
                "Dim":              Int, 
                "Conductor":        TooLargeInt,
                "DBIndex":          Int,        # Starting at 1
                "CharacterField":   Int,
                "Character":        Dokchitser_Character
            })

Dokchitser_ConjugacyClass = Dict(
            {
                "Order":            Int,
                "Size":             TooLargeInt,
                "Representative":   PermutationAsList
            })

class pAdicApproximationAsString(String):
    # If the numbers get too unwidely, one can use this class to overload self.latex() and display it in a better form
    pass

Dokchitser_NumberFieldGaloisGroup = Dict({
    "_id" :                 Anything,
    "ArtinReps" :           FiniteSequence(Dokchitser_ArtinRepresentation_Short),
    "ComplexConjugation" :  Int,
    "ConjClasses" :         FiniteSequence(Dokchitser_ConjugacyClass),
    "DBIndex" :             Int,                    # Starting at 1
    "FrobResolvents" :      Array(Dokchitser_FrobResolvent),
    "Frobs" :               PrimeIndexedSequence(Int), 
    "G-Gens" :              FiniteSet(PermutationAsList),
    "G-Name" :              Custom_GroupLabel,
    "Polynomial" :          PolynomialAsSequenceInt,
    "QpRts" :               FiniteSequence(pAdicApproximationAsString),
    "QpRts-minpoly" :       PolynomialAsSequenceInt,
    "QpRts-p" :             Int,
    "QpRts-prec" :          Int,
    "Size" :                TooLargeInt,
    "TransitiveDegree" :    Int,
    "label" :               LabelString
})


Dokchitser_ArtinRepresentation_Collection = bind_collection(artin_location, Dokchitser_ArtinRepresentation)
Dokchitser_NumberFieldGaloisGroup_Collection = bind_collection(galois_group_location, Dokchitser_NumberFieldGaloisGroup)
