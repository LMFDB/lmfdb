artin_location = ("contrib","pdehaye4f2bef4ce9841255c9000002")
galois_group_location = ("contrib","pdehaye4f2bef6ae9841255c9000004")

from type_generation import String, Array, Dict, Int, Anything, Float

from standard_types import PolynomialAsString, PermutationAsList,\
    TooLargeInt, LabelString, FiniteSequence, FiniteSet, GAP_GroupLabel, PrimeIndexedSequence, AlgebraicNumberPolynomialString, \
    PolynomialAsString, AlgebraicNumberString_Root
    
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

Dokchitser_Character = FiniteSequence(Dokchitser_AlgebraicNumber_Root)

Dokchitser_ArtinRepresentation = Dict({
        "_id":          Anything,
        "Dim" :         Int,
        "Conductor" :   TooLargeInt,
        "DBIndex" :     Int,        # Starting at 1
        "NFGal" :       FiniteSequence(Int),
        "Character" :   Dokchitser_Character
    })

class CycleType(Array(Int)):
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
                "Degree":           Int,   # ---> becomes "Dim" in new data
                "Conductor":        TooLargeInt,
                "Index":            Int,        # Starting at 1
                                                # Index ---> DBIndex
                "Character":        Dokchitser_Character
            })

Dokchitser_ConjugacyClass = Dict(
            {
                "Order":            Int,
                "Size":             TooLargeInt,
                "Representative":   PermutationAsList
            })

Dokchitser_NumberFieldGaloisGroup = Dict({
    "_id" :                 Anything,
    "Degree" :              Int,
    "Polynomial" :          Polynomial_X_ZZ_AsString,
    "Size" :                TooLargeInt,
    "DBIndex" :             Int,                    # Starting at 1
    
    "G-Gens" :              FiniteSet(PermutationAsList),
    "G-Name" :              GAP_GroupLabel,
    
    "QpRts-p" :             Int,
    "QpRts-minpoly" :       Polynomial_X_ZZ_AsString,
    "QpRts-prec" :          Int,
    "QpRts" :               FiniteSequence(Dokchitser_AlgebraicNumber_MinPol),
    
    "ConjClasses" :         FiniteSequence(Dokchitser_ConjugacyClass),

    "ComplexConjugation" :  Int,
    
    "Frobs" :               PrimeIndexedSequence(Int), 

    "FrobResolvents" :      FiniteSet(Dokchitser_FrobResolvent),
    
    "ArtinReps" :           FiniteSequence(Dokchitser_ArtinRepresentation_Short),
    "label" :               LabelString
})


Dokchitser_ArtinRepresentation_Collection = bind_collection(artin_location, Dokchitser_ArtinRepresentation)
Dokchitser_NumberFieldGaloisGroup_Collection = bind_collection(galois_group_location, Dokchitser_NumberFieldGaloisGroup)
