# Issues discussed with David,Nathan and ralf on Oct 2, 2015

  * The collections should be listed on the home page in a reasonable order.
  DONE
  
  * The 'formexamples' in the serach part on the home page should be reviewed.
  DONE
  
  * There should be a 'testfile' for the SMF part.

  * Reduction Ideal on the sample pages should be renamed from \mathfrak{l} to \mathfrak{a}.
  DONE (But I took \mathfrak{L} since \mathfrak{a} waslike \alpha and 'a'.)

  * There should be more knowls explaining notions like 'collection', 'Miyawaki lift',
    'GL(n,C) representations' and the like.

  * There should be a uniform standard for entering aguments in textboxes in the lmfdb.
    Instead of '4+20' some people prefer '4..24'
    (since typing and calculating is fun for the user :-).

  * The label for the textboxes for inputting dimension ranges should be induvidualized
    for the collections.
  DONE
  
  * The collections pages should show up with some default precalcuated
    dimension tables.
  DONE
  
  * The column headings for dimensions on M_{k,2}(Sp(4,Z)) are somehow wrong.
  NONE
  
  * The last link on M_{k,2}(Sp(4,Z))'s collection page is dead.
  DONE

  * 'GL(n,C) representation' select box does not work for input '0'.
  DONE



# Issues fixed in the week Sept. 28 to Oct. 2, 2015 

## Bugs

  * "Browse samples", "By degree of its field of definition", never gives any results.
  DONE (We needed to add a "degree_of_field" to the data sets
  
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
  DONE
  
  * Reduction of polynomials should be implemented so that vector valued SMF are
    shown correctly (e.g. Error at ModularForm/GSp/Q/Sp4Z_2.14_C/)
  DONE
  
  * Complete the documentation:

    * How to add new collections
  DONE
  
    * Explanation of the code parts: "what happens next after queries?"
      
  * func_doc for dimensions_Gamma0_4_half is missing.
  DONE

  * If a sampel belongs to several collections it should also show up
    in all those on the collection page.
  DONE  


## Easy issues

  * Need knowl for "collections of Siegel modular forms".

  * How about a knowl for Miyawaki lift on ModularForm/GSp/Q/Sp6Z.12_Miyawaki/ ?

  * Explain what GL(n,\C) representation means and what the numbers are that should be entered. 

  * list of l should be list of \ell
    http://beta.lmfdb.org/ModularForm/GSp/Q/Kp.2_PY2_587_plus/?dets=8
  DONE


## Desired features which need more thought/discussion and can be dealt with after a non-beta release

  * Outputs like this: ModularForm/GSp/Q/search_results/?query={"degree"%3A"2"}
    should be formatted in table form and somehow ordered, maybe by collection.

  * Concerning sample pages:

    * Can we populate the Discriminant, Signature, Is Galois lines under "Field"
      (sometimes there are no such fields, as in ModularForm/GSp/Q/Kp.2_PY2_523/)?
  DONE
    * Sometimes it gives the field equation as polynomial in x
      (ModularForm/GSp/Q/Sp4Z.28_Maass/), sometimes with a show/hide button
      (ModularForm/GSp/Q/Sp4Z.32_Ups/)
  DONE (That is fine: polynomials with more than 100 bytesasstrings are hidden
       not to cluutter the page.)

  * ModularForm/GSp/Q/Sp4Z_j/ and ModularForm/GSp/Q/Gamma1_2/ and ModularForm/GSp/Q/Gamma0_2/:
    Explain what the input should be. (If you follow the first two suggestions under "e.g.",
    it doesn't actually work.)

  * Better explain output in pages like this:
    ModularForm/GSp/Q/Gamma1_2/?dim_args=[range(20%2C31)%2C4]
  DONE

  * Say "... for each weight k..." and put in actual value of j in top line.

    * What is the meaning of the triples?
  DONE
  
    * What is the meaning of 3, 21 and 111?
  DONE
  
  * formatting weird for More \lambda(\ell)... should be above the list
    of available lambdas

  * same as before for C(F)

  * What's the Principal ideal (0) of Integer Ring at the bottom about?

  * The data objects are partly too big to fit in the mongodb, so one needs to use gridfs.
    Who knows how to handle this?

  * Pull down menu on http://beta.lmfdb.org/ModularForm/GSp/Q/ should
    have latex looking code


## Issues which need more feedback or explanation

  * R: The space M_k(\Gamma_0(2)) is no longer a collection,
    whereas the old page looked pretty good:
    http://www.lmfdb.org/ModularForm/GSp/Q?page=dimensions&level=17&group=Gamma0_2&weight_range=20-30


  * R: "Search for samples":

    *  Make sure that every suggested input is valid and leads to a meaningful page that has data.
  DONE
    
    * "Find a specific form by its LMFDB label": Typing in any of the suggestions
      leads to a cryptic javascript box, followed in the first two cases by an empty search result.
  DONE

  * R: Every input I try on ModularForm/GSp/Q/Sp8Z/ ends in an error message.
  DONE
  
  * N: Link to http://beta.lmfdb.org/ModularForm/GSp/Q/Sp4Z_2/ on
    http://beta.lmfdb.org/ModularForm/GSp/Q/Sp4Z_2/ doesn't work: Limk below

  * N: Page for M_k,j(Gamma_0(2)) might be the same as that for M_k(Gamma0(2))
  DONE
  
  * N: On the main page I want to type 6+20 2 into weights but it won't
    accept it.  I guess I'm supposed to use GL(n,C) representation?  But
    that won't let me either.
  DONE

  * N: generators of ... cut off at
    http://beta.lmfdb.org/ModularForm/GSp/Q/Kp.2_PY2_587_plus/?dets=8
