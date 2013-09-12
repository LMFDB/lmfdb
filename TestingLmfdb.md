Install Testing Tools
=====================

Low Level Testing
-----------------

Inside Sage

* `easy_install -U unittest2`
* `easy_install -U  nose`
* `easy_install -U coverage`

Then

* run `./test.sh` for the whole piece

* run `./test.sh lmfdb/<directory>` to check what's in a specific sub-module

High Level Testing
------------------

The page **[checklist](http://www.lmfdb.org/checklist)** is a helpful list of URLs 
that point to specific pages.
It should cover all areas of the page and contain their individual main pages,
the browse and search interface,
hard-code a certain search and some specific pages.
Also, if some page was broken, don't hesitate to add it there, too.

Besides the URL add a short human readable text explaining what the person testing this should watch out.

