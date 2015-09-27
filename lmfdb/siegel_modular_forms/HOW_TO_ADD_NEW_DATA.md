# How to add new data

## Author: Nils Skoruppa <nils.skoruppa@gmail.com>, September 2015

### New collection

If you create a collection you should have either a dimensıon formula
or samples (see below); the best is of course to have both. If this ıs
fulfilled we have to find a name for the collection. For examples see
the names `static/*.json`.

Next we have to create a file `static/My_Coll.json` describing the
collection. This file should look like this:

```
{
  "description": "includes/Sp4Z_basic.html", 
  "dimension": "lmfdb.siegel_modular_forms.dimensions.dimension_Sp4Z", 
  "latex_name": "M_k\\left({\\textrm{Sp}}(4,\\mathbb{Z})\\right)", 
  "name": "Sp4Z"
}
```

The field `dimension` is optional.

Next you have to create the file descriptions. It is recommended to
keep to the naming scheme `includes/My_Coll_base.html`.

If you provide field `dimension` you need also to provide python code
for the dimension. Look below for some requirements.

The file `My_Coll_base.html` explains

  1. which samples are availabe ('- not available -' is perfectly acceptable),
  2. whether dimension formulas are available
  (again, '- not available -' is perfectly acceptable),
  3. whatever explanations and comments you want to provide.

Note that the naming scheme for samples should follow
`collection.weight.type.no`.


### Dimension formula


### Samples

If you want to add a sample to 
 

### MongDB