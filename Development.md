LMFDB Developer's Guide
=======================

This document describes the development process of the LMFDB. In addition, it
describes the principles behind the pages in the LMFDB, the writing style, the
use of knowls, and the URLs of the home pages of mathematical objects. This
document is not meant as a rigid set of rules. Rather, it is intended to help
speed the creation and adoption of new material, and to help maintain a unified
design as the website grows.

If you are interested in developing the LMFDB, it would be a very good idea to
introduce yourself to the current developers, who can then help you get
involved in current development meetings.


Setup
=====

To set up your system for development see [Code development and sharing your
work](https://github.com/LMFDB/lmfdb/blob/main/GettingStarted.md#running).


Adding material to the LMFDB
============================

New pages are developed through an iterative process that involves input from
both experts and nonexperts. The goal is to make everyone happy.

A principle to keep in mind is that a novice must be able to click their way
around the site, exploring objects about which they might know very little;
at the same time, an expert has to be able to quickly find what they are
looking for.




Structural Conventions
======================

Below, we describe several of the structural conventions used in the LMFDB. Note
that we also have styling conventions for the content of individual pages. These
styling conventions are described in
[StyleGuide.md](https://github.com/LMFDB/lmfdb/blob/main/StyleGuide.md).

Pages in the LMFDB
------------------

- Each mathematical object in the LMFDB has a "home page".
- This home page should have a mathematically meaningful URL.
- The home pages can be reached by browse pages and search pages.
- On both the "home page" for an object and on the browse pages and search
  pages, knowls provide information about technical terms.

We elaborate on these four points.

### Homepages

Every object in the LMFDB has a "home page". The home page of a
mathematical object is based on the idea of a home page of an individual
mathematician, or the wikipedia article of someone famous.

An object's home page should provide a wide variety of information about the
object. Basic information, of interest to both experts and non-experts,
should appear ear the top. More specialized information should appear
near the bottom.

In the upper right corner of each home page should be the "properties" box,
summarizing the most basic facts about the object. The information in the
properties box should also appear in the body of the page.

Below the properties box is the "Related objects" box, containing links to
the home pages of related objects. Below the related objects box is the
"Downloads box", containing links to data and code. And below the downloads
box is the "Learn more about" box, containing information about the
completeness and source of the shown data.

Standard practice for creating the home page for a new object is to copy the
template for an existing object with a good home page. *(This has often been
elliptic curves or global number fields in the past --- classical modular
forms have some newer features and might be copied now too)*. The "Properties
box" and other features will already be there, and you can use them without
necessarily knowing all the details of how the templates work.

Descriptions of the terminology on the home page for an object should be put in
knowls. This allows nonexperts to find basic information without
forcing experts to skim through documentation. The links to the knowls should
be the words being defined. **Don't add extraneous words like "click here"**.

For a given type of object, all of the home pages should have the same entries.
If some piece of data is not known for an object, still list that entry and
say "data not computed", or some similar phrase if that does not properly
capture the situation.  The only exception is if some property only makes sense
for certain objects in that class.  For example, number field pages only have
a section for Reflection fields if the number field is a CM field.  But all
number field pages have a place to show the regulator even though it has not
been computed in all cases.

When creating a new home page for an object, get feedback from both experts
and nonexperts about the order in which the information appears on the
home page, and the categories in which to group the material. If there is a
question about whether something should go on a home page, frequently the
answer is "yes"; the main exception is when the information is not of wide interest or if it more properly belongs on the home page of a related object.

In practice, it is a good idea to get feedback from the current group of
established LMFDB developers frequently.

*Historical note*: the properties box is also known as the "Lady Gaga" box, or
the "Gaga box". The name comes from John Voight's presentation at an LMFDB
workshop, where he used Lady Gaga's Wikipedia article as an illustration
of the value of gathering basic information in the upper-right corner of a
home page.


### Browse and search pages

The entry point to most mathematical objects in the LMFDB is through browse
and search pages. The upper portion of these pages (the part that is visible
in a typical browser when first visiting the page) should contain two things:

1. At the top should be a variety of links to specific objects, and to
   search pages where reasonable search parameters have already been
   selected. The point is that a novice should be able to click around with
   their mouse and explore the topic, without needing to fill out a form
   or even know anything about the topic to proceed.

2. Below the top section, but still visible without scrolling far, should be a
   search form which is suitable for use by experts.

Other material can appear in the lower portion of browse and search pages.


### Knowls

In order to be able to write or edit knowls, it is necessary to contact the
current developers of the LMFDB.

#### Anatomy of a knowl

There are three components to a knowl.

1. Identifier: this indicates where the knowl fits into the hierarchy of
   information in the LMFDB, but the scheme is not as elaborate or as rigid as
   URLs.

   Example: ec.q.conductor has `ec.q` as hierarchies.

   Consult with experts before trying to introduce new first or second-level
   identifiers. It is tedious to alter identifiers and change the places they
   are used afterwards.

2. Description/title: this consists of several words that describes the knowl
   and helps distinguish it among knowls on similar topics.

   Example: "Conductor of an elliptic curve over Q". Notice that this
   description would be inadequate if it were any shorter.

3. Content: this is the text that appears when someone clicks on the knowl.

  As originally envisioned by Harald Schilly, knowls should contain a
  relatively small amount of information (because it is better to have
  knowls-within-knowls so the reader can determine what additional
  information is needed), and the content of a knowl is *context
  independent*. This means that the information should make sense wherever it
  might appear.

  In the example of "Conductor of an elliptic curve over Q", the definitions
  in most textbooks may not be suitable for the content of the knowl,
  because the phrasing may not make sense unless the reader has read previous
  content in the text.

  Note that years of schooling have trained people to write in a linear
  fashion where each idea flows into the next. This training might not be
  helpful in writing knowls, as they should be *context independent*.
  Try not to think about the specific situation in which you want to use
  the knowl: write something that makes sense in all other places where
  others might use it.


#### Using knowls

Knowls are used in several ways:

1. To provide supplementary information (such as a definition) on a web
   page.

2. To provide all the material on a webpage in a way that can be easily
   edited. (Though this is relatively rare).

The above is a list of how knowls are *currently* being used in the LMFDB.
This might change over time.


### URLs

One of the fundamental principles of the LMFDB is that mathematical objects
should have a "home page" (described above).

As much as possible, the URLs for home pages of objects in the LMFDB
should be

1. mathematically meaningful
2. human readable
3. permanent
4. suitable for inclusion in a bibliography

Here and throughout this document, we say "should" instead of "must", with
the understanding that some compromises will be inevitable.

Here are some principles:

1. If X is the URL of an object, then L/X is the URL of its standard
   L-function. According to the Langlands program, other L-functions
   associated to X have the form L(s, X, rho). Examples include

   - L(s, f, sym^2)
   - L(s, f, spin)

   These should then have URLs, respectively,

   - `L/SymmetricPower/2/<url_for_f>`
   - `L/spin/<url_for_f>`

2. The group comes before the field. For example, GL2/Q could occur in the URL
   of some object.

3. The "type of object" should come first. For example, some top level
   URLs for home pages include

   - /ArtinRepresentation
   - /Character
   - /EllipticCurve
   - /L
   - /ModularForm

   There are other top level URLs, and not all top level URLs have
   home pages for mathematical objects below them.

4. "Nicknames" can sometimes be used for popular number fields. These include
   - QsqrtN: where N can be a positive or negative integer. For example,
     Qsqrt7 or Qsqrt-5
   - Q: the rationals
   - Qi: `Q(\sqrt{-1})`
   - QzetaN: the Nth cyclotomic field

   For example, the search page
   https://www.lmfdb.org/ModularForm/GL2/Q/holomorphic/ allows
   Qsqrt5 as a search parameter for the coefficient field.

   Note that number fields like Qsqrt5 has an "official name" as well as a
   nickname. Many discussions have occurred for what appropriate labels for
   objects should be. Examine the structure of existing objects in the
   LMFDB very closely to maintain correct labels and relationships.

5. The URL of an object provides successively narrower descriptions of the
   object. After some number of levels (depending on the object), one is
   faced with the issue of naming a specific object. This final specification
   can be done with a label, or with a hierarchy/directory-style
   specification.

   For example, the following examples are currently in use, and these URLs
   should be considered permanent:

   - `/ArtinRepresentation/\<dim>/\<conductor>/\<label>`
   - `/Character/Dirichlet/\<modulus>/\<number>`
   - `/Character/Hecke/\<number_field>/\<modulus>/\<number>`
   - `/EllipticCurve/Q/\<label>`
   - `/GaloisGroup/\<label>`
   - `/padicField/\<label>`
   - `/ModularForm/GL2/Q/holomorphic/\<label>`
   - `/ModularForm/GL2/Q/Maass/\<label>`
   - `/Motive/Hypergeometric/Q/\<label>`
   - `/NumberField/\<label>`

In practice, prior to deciding on a labelling scheme for new objects, one
should talk to the current LMFDB developers (who now have a lot of experience
in considering labelling schemes).


Templates
---------

Pages are displayed through flask+jinja templates. A template has several
typical variables:

 * title - that appears on several places
 * properties - right hand bar, see below
 * bread - breadcrumb hierarchy, i.e. [ ('name', 'url'), ... ]
 * sidebar - additional sidebar entries. The data structure is
   `[ ('topic', [ ('text', 'url'), ...]), ... ]`.

   - Note that `info.downloads`, `info.friends`, and `info.learnmore` have the
     same structure, though the names might differ from page to page.

 * credit - small credits note at the bottom
 * support - either a default or a line that says who has supported this.

For more details read templates/homepage.html


The idea is to extend "homepage.html" and replace the content block:

```
{% block content %}
   ... your stuff ...
{% endblock %}
```


CSS
---

The css should be kept in the .css files in lmfdb/templates/ and loaded into
homepage.html.  Preferably, new css should be added to:

 * style.css - contains the majority of the css, for example, for the
   properties and sidebar variables.

The colors are defined in `lmfdb.utils.color`, and are available in
Jinja as `color.header_background` for example.  Please use the colors
defined there rather than specific colors to facilitate future changes.


Code Organization / Blueprints
------------------------------

Each part of the website should be a Python module [1] and a proper flask
Blueprint [2]. Look at how /knowledge/ is done, especially knowledge/__init__.py
and knowledge/main.py. Also, templates and static files specific to the module
should be in their respective "templates" and "static" folders, e.g.
/knowledge/templates/.

[1] https://docs.python.org/tutorial/modules.html
[2] https://flask.pocoo.org/docs/blueprints/


Code Attribution
----------------

Each file should begin with a short copyright information, mentioning the people
who are mainly involved in coding this particular python file. In practice, 


Testing
-------

- Any contribution to the main LMFDB branch must *pass all the tests*. From the lmfdb folder:
  ```
  ./test.sh
  ```
  It takes a few minutes. If sage or some additional parts are missing it may fail,
  consider updating
  (see [Getting Started](https://github.com/LMFDB/lmfdb/wiki/GettingStarted) )

- New blueprints and features should include a `test_<name>.py` file
  which runs tests on all functions.

- A code coverage diagnostic can be obtained via
  ```
  ./test.sh html
  ```
  it produces beautiful coverage scores in `lmfdb/cover/index.html`

Pro Tip: Debugging
-------------------

Just add
```
  import pdb; pdb.set_trace()
```
somewhere (e.g. protected inside a sensible if) this magic
line and you will end up inside the interactive python
debugger. there, you can check for the local variables with dir()
you can execute python code (e.g. to introspect objects)
and use "pp <var name>" to pretty print variables and
to continue executing code use the "n" command.
When you get lost, the command "bt" shows you exactly where you
are and "up" helps you to get on step up on the stack.
Of course, "help `<command>`" will tell you more...

Git Tips
=========

global .gitignore
-----------------

Please configure Git to have a global .gitignore for all your projects.
It should contain all the files which are not project specific, but happen
on your machine. E.g. temporary files ending in `...~` or `.DS_store`.

[copy paste ready instructions on github](https://help.github.com/articles/ignoring-files#global-gitignore)

.gitconfig
----------

In your home directory, in the file ~/.gitconfig

```
[alias]
        st=status
        aliases=!git config --get-regexp 'alias.*' | colrm 1 6 | sed 's/[ ]/ = /'
        ci=commit
        br=branch
        co=checkout
        df=diff
        who=shortlog -s --
        ll = log --oneline --graph --decorate -25
        lla = log --oneline --graph --decorate --all -25
        wdiff=diff --word-diff=color
[color]
    ui = auto
    branch = auto
    diff = auto
    interactive = auto
    status = auto
```

List-table should always be like
--------------------------------

```
<table class="ntdata">
  <thead><tr><td>...</td></tr></thead>

  <tbody>
   <tr class="odd"> <td>...</td></tr>
   <tr class="even"><td>...</td></tr>
   <tr class="odd"> <td>...</td></tr>
   ...
  </tbody>
</table>
```

... we might also switch to CSS3's nth-element selector and forget about this.


Properties
----------

The table on the right renders Strings formatted in the following datastructure:

```
prop = [ ( '<description>', [ '<value 1>', '<value 2>', ...] ), ... ]
```

or

```
prop = [ ( '<description>', '<value>'), ('<description>', '<value>'), ... ]
```

you can mix list or non-list.


LaTeX Macros
------------

Latex macros are documented in a knowl that will appear when you start editing one.


Server Hook
-----------

This is in the `hooks/post-receive` in the bare Git repo:

```
#!/bin/sh
# update the lmfdb-git-beta or -prod server depending on the branch
# this is based on https://stackoverflow.com/a/13057643/54236

restart() {
    echo "updating $1"
    export GIT_WORK_TREE=/home/lmfdbweb/lmfdb-git-$1
    git checkout $1 -f
    echo 'git HEAD now at' `git rev-parse HEAD`
    bash ~/restart-$1
}

while read oldrev newrev refname
do
    branch=$(git rev-parse --symbolic --abbrev-ref $refname)
    case $branch in
        prod) restart $branch
              ;;

        beta) restart $branch
              ;;
    esac
done
```
