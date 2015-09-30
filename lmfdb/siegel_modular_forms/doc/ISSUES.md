## Bugs

  * "Browse samples", "By degree of its field of definition", never gives any results.

  * On ModularForm/GSp/Q/Gamma0_3/ it says "Dimensions not implemented".
    However, on the old page, the total dimensions are implemented:
    http://www.lmfdb.org/ModularForm/GSp/Q?page=dimensions&level=17&group=Gamma0_3&weight_range=20-30
  DONE
  
  * Same issue for ModularForm/GSp/Q/Gamma0_3_psi_3/
  DONE

  * and ModularForm/GSp/Q/Gamma0_4/
  DONE
  
  * and ModularForm/GSp/Q/Gamma0_4_psi_4/.
  DONE

  * Avoid showing an empty table when you navigate to page Sp8Z.
  DONE (Nils: David Yuen's data consisted of html pages - I needed hours
       to put them into a form which could be send to and used in Warwick.)
       
  * Implement downloading of mongodb obects as json file (important e.g. for people
    who need examples how to prepare the data which they want to add).

  * Reduction of polynomials should be implemented so that vector valued SMF are
    shown correctly (e.g. Error at ModularForm/GSp/Q/Sp4Z_2.14_C/)

  * Complete the documentation:

    * How to add new collections

    * Explanation of the code parts: "what happens next after queries?"
    
  * func_doc for dimensions_Gamma0_4_half is missing.
  DONE


## Desired features (not necessary for a first release)

  * The data objects are partly too big to fit in the mongodb, so one needs to use gridfs.
    Who knows how to handle this?
    

## Easy issues

  * Need knowl for "collections of Siegel modular forms".

  * How about a knowl for Miyawaki lift on ModularForm/GSp/Q/Sp6Z.12_Miyawaki/ ?

  * Explain what GL(n,\C) representation means and what the numbers are that should be entered. 



## Desired features which need more thought/discussion and can be dealt with after a non-beta release

  * Outputs like this: ModularForm/GSp/Q/search_results/?query={"degree"%3A"2"}
    should be formatted in table form and somehow ordered, maybe by collection.

  * Concerning sample pages:

  * Can we populate the Discriminant, Signature, Is Galois lines under "Field"
    (sometimes there are no such fields, as in ModularForm/GSp/Q/Kp.2_PY2_523/)?

  * Sometimes it gives the field equation as polynomial in x
    (ModularForm/GSp/Q/Sp4Z.28_Maass/), sometimes with a show/hide button
    (ModularForm/GSp/Q/Sp4Z.32_Ups/)



  * ModularForm/GSp/Q/Sp4Z_j/ and ModularForm/GSp/Q/Gamma1_2/ and ModularForm/GSp/Q/Gamma0_2/:
    Explain what the input should be. (If you follow the first two suggestions under "e.g.",
    it doesn't actually work.)

  * Better explain output in pages like this:
   ModularForm/GSp/Q/Gamma1_2/?dim_args=[range(20%2C31)%2C4]

    * Say "... for each weight k..." and put in actual value of j in top line.

    * What is the meaning of the triples?

    * What is the meaning of 3, 21 and 111?



## Issues which need more feedback or explanation

  * The space M_k(\Gamma_0(2)) is no longer a collection,
   whereas the old page looked pretty good:
   http://www.lmfdb.org/ModularForm/GSp/Q?page=dimensions&level=17&group=Gamma0_2&weight_range=20-30


  * "Search for samples":

    *  Make sure that every suggested input is valid and leads to a meaningful page that has data.

    * "Find a specific form by its LMFDB label": Typing in any of the suggestions
      leads to a cryptic javascript box, followed in the first two cases by an empty search result.


  * Every input I try on ModularForm/GSp/Q/Sp8Z/ ends in an error message.
