# How to add new data

## Author: Nils Skoruppa <nils.skoruppa@gmail.com>, September 2015

### Important remark

The SMF part of the lmfdb should be viewed as an *interface*. In other
words, it is a black box encapsulating all the code providing a view
on the Siegal data, and it should therefore be accessed only via the
provided interfaces as described below. ALL ATTEMPTS TO HACK INSIDE
THE BLACK BOX TO MAKE AN EXCEPTIONAL POINT IN THE VIEW  OF YOUR
FAVORITE DATE WILL VERY LIKELY BREAK THE CODE. IF YOU STILL NEED TO
MAKE CHANGES INSIDE THE BLACK BOX MAKE SURE THAT YOU UNDERSTAND HOW IT
WORKS and that the redefined black box is *downwards compatible*
(Which might require a bit of advanced programming skills).


### New collection

If you create a collection you should have either a `dimensıon
formula` or `samples` or an html file explaining the background of
your collection.  The best is of course to have all three, but each of
these items is optional.


If you have at least one one of the above you have to find a name for
your collection. Lets call your collection 'Dummy_0'.  Next you have
to make the lmfdb recognize it by adding a file `static/Dummy_0.json`
to the static directory (inside the Siegel modular forms module). 


#### The file Dummy_0.json

The contents of this file should look like this:

```
{
    "description": "includes/Dummy_0_basic.html", 
    "dimension": "lmfdb.siegel_modular_forms.dimensions.dimension_Dummy_0", 
    "dim_args_default": "[range(21)]",
    "latex_name": "{\\textrm{Dummy}}_0", 
    "name": "Dummy_0",
    "order": 10
}
```

All fields are optional but you should at least provide '{}' as
contents of your file.  Also the name and location for your
`Dummy_0_basic.html' and your dimension formula are optional. Of
course, for helping others it is best to stick to the proposed naming.
The file is written in *json*-format; see the Wikipedia if you want to
learn more.


#### Samples

If you have samples the easiest is to convert them into a *.json file
similar to the ones that you can download on the samples page of the
SMF part.  Just fetch one and study it.  Do not forget to provide a
field `"collections": ["Dummy_0", ...]`, since otherwise your sample will
dissaper into the dark of the mongodb.  To upload it to the lmfdb
mongodb use the script upload.py in the directory utils ('python
upload my_sampe.json').


#### Dimension formula

If you have a dimension formula you should implement it. For this
follow the example `Dimension formulas for Dummy_0` at the end of the
file dimension.py (just duplicate this part, rename one copy and fill
in your code).


#### Misc informations

Finally if you have some comments ot explanations to add to your data
formulate them into the file `Dummy_0_basic.html`. Note that this is a
file which will be included by a surrounding genuine html file. So use
html for formatting but do not provide '<html>', '<head>' or '<body>'
tags or the like.


That is it!

---Nils Skoruppa, Octobe 2015
