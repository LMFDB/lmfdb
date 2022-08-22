# The (new) design of the Siegel modular forms part of the LMFDB

## Author: Nils Skoruppa <nils.skoruppa@gmail.com>, September 2013


The pages in the package siegel_modular_forms (SMF) provide a view on
samples of Siegel modular forms or eigenvalue packages of all kind. A
single sample will ideally provide, (aside from some meta information
like origin, creators etc.), Fourier coefficients, explicit formulas,
eigenvalues, weights, group(s) and character(s).  A sample should be
uniquely identifiable by name. To set up such a unique name we
subdivide our forms into collections (which, however, are allowed to
overlap). A unique identifier is then

    `collection.weight.type.no`

like e.g. `Sp4Z.4.Eis.1` or `Gamma_2.30.Cusp.1`.  The choice of
collections has to ensure that these naming scheme makes our samples
uniquely identifiable by name. The `no` is arbitrarily chosen
according to the *begin of membership*, ı.e. *last in gets the smallest
free number*. Note that a sample will then possibly have several
unique identifiers.

For achieving this presentation of data we have to prepare three
layers:

  1. the organization of data in the data base
  2. the physical layout of data in web pages.
  3. the encapsulation of data in compound objects


### 1. Organization of data

The data should be represented as instances of the following objects.

```
                        Family/Collection
                                /\
                                |      
                                |
    Fourier coefficients <--- Sample --> Eigenvalues
                                |
                                |
                                \/
                               Field
```

The arrow indicates that every sample contains exactly one pointer to
an instance of field, Fourier coefficients, eigenvalues and
collection. Two instances of sample are *semantically identical* if
their Fourier coefficients are the same (since we shall have only
finitely many Fourier coefficients we have to make sure that two
instances point to the same Fourier coefficients only if we  are sure
that they are indeed mathematically identical).


### 2. Physical layout of data

According to the *BROWSE and SEARCH* paradigm of the lmfdb project
the entrance page of the SMF will provide

 * fields for browsing (i.e. providing views of the available forms ordered)
   * by family/collection
   * by weight
   * by group
   * by degree of fields
   * and to browse dimensions

  * forms for providing searches for available samples
    on restricting the search by
    * weight
    * group
    * degree of the number field
    * ???
    * and a form to fetch a specific sample (using 'expert' knowledge).

The collection pages (which you reach by choosing a collection)
provide background information about the collection and a dimension
calculator (if this make sense and dimensions are known).


### 3. Encapsulation of data

A collection consists of a set of data of a certain type of
automorphic forms.  Every collection will be represented by its own
home page, which shows which data are available for browsing or
searching. Codewise, collections are instances of the class
Collection.

Possible data are

  * group
  * character
  * sym_pow
  * dimension (a function computing dimensions
    for subspaces for this type of forms)
  * generators
  * description
  * learnmore page

Methods are (aside from providing the above data)

  * dimension (calculation on the fly or look up)
  * members (look up in the db).

### The members of a collection

is a set of forms, which are implemented by
the class Sample. The typical date of a form are

  * Fourier coefficients
  * eigenvalues
  * weight
  * list of collections it belongs to
  * the creator(s) of the data
  * explicit formula(s) (polynomial in generators of a ring of
    automorphic forms, a modular form whose arithmetic/multiplicative
    lift it is etc.)

The last sort of data is still a challenge and we push its
implementation until we have enough examples to respond to. 

### Finally

we will not be STRICT, i.e. we never force a collection or a form to
possess desired date (since because of the complexity of the involved
computations or diverging goals of the donators these cannot always be
provided).  If some requested data are not available we return
'None'. The rendering machinery has to take care of this possible
answer. This approach makes it possible that we can easily plugin new
collections even if the provided data do not exhibit an ideal
completeness.

In particular, we should be prepared to have samples with only one of
the possible informations 'field', 'Fourier coefficients' or
'eigenvalues'. This might lead to somewhat strange collections like
e.g. 'Gamma0(5)_fields'. However, since even such informations are
worthy in view of the computational complexity of Siegel modular forms
we are happy to present them.