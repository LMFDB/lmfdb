Setup
=====
To set up your system for development see [Code development and sharing your work](https://github.com/LMFDB/lmfdb/blob/master/GettingStarted.md#running).

Conventions
===========

Template
--------

A template has several variables:
 * title - that appears on several places
 * properties - right hand bar, see below
 * bread - breadcumb hierarchy, i.e. [ ('name', 'url'), ... ]
 * sidebar - additional sidebar entries, datastructure is
   [ ('topic', [ ('text', 'url'), ...]), ... ]
   ** info.downloads, info.friends, info.learnmore have the same strucutre,
      names might change sometimes.
 * credit - small credits note at the bottom
 * support - either a default or a line that says who has supported this. 

For more details read templates/homepage.html


The idea is to extend "homepage.html" and replace the content block:
{% block content %}
   ... your stuff ...
{% endblock %}

CSS
---
The css should be kept in the .css files in lmfdb/templates/ and loaded into
homepage.html.  Preferably, new css should be added to one of the already existing .css files.  There are two .css files:
 * style.css - contains the majority of the css, for exmaple, for the
   properties and sidebar variables.
 * color.css - contains all color definitions and templates.  Always use a
   color defined in color.css, preferably one of the col_main's.  If you
   feel the need to use a color not defined here, please add it to this file.
   This helps keep the colors organized into a particular themes.

Code Organization / Blueprints
------------------------------

Each part of the website should be a Python module [1] and a
proper flask Blueprint [2]. Look at how /knowledge/ is done,
especially knowledge/__init__.py and knowledge/main.py. 
Also, templates and static files specific to the module
should be in their respective "templates" and "static"
folders, e.g. /knowledge/templates/. 

[1] http://docs.python.org/tutorial/modules.html
[2] http://flask.pocoo.org/docs/blueprints/

Basic Organization / Editorial Board
----------------------------

Behind the Scenes:
 * Backend: Harald Schilly
 * Server: Jonathan Bober
 * Data Management: Ralf Furmaniak

Sections:
 * Genus 2 Curves: Andrew Sutherland
 * Hilbert MF: John Voight
 * Elliptic Curves: John Cremona
 * L-functions: Stefan Lemurell
 * Siegeld MF: Nils Skoruppa
 * Elliptic MFs: Nathan Ryan
 * Maass Fs: Fredrik Stromberg
 * Number Fields / Galois Groups: John Jones
 * Artin Reps: Paul-Olivier Dehaye
 * Dirichlet Characters: Pascal Molin
 * Zeroes: Jonathan Bober

Code Attribution
----------------
Each file should begin with a short copyright information,
mentioning the people who are mainly involved in coding
this particular python file. 

Testing
-------

- Any contribution to the master LMFDB branch must *pass all the tests*. From the lmfdb folder:
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

<table class="ntdata">
  <thead><tr><td>...</td></tr></thead>

  <tbody>
   <tr class="odd"> <td>...</td></tr>
   <tr class="even"><td>...</td></tr>
   <tr class="odd"> <td>...</td></tr>
   ...
  </tbody>
</table>

... we might also switch to CSS3's nth-element selector and forget about this.

Properties
----------
the table on the right renders Strings formatted in the following datastructure:
prop = [ ( '<description>', [ '<value 1>', '<value 2>', ...] ), ... ]
or
prop = [ ( '<description>', '<value>'), ('<description>', '<value>'), ... ]
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
# this is based on http://stackoverflow.com/a/13057643/54236

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
