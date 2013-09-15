Installation
============

  * To contribute, see below on sharing your work.  To simply run a copy of the site move into a new directory and type
```
    git init
    git clone git@github.com:LMFDB/lmfdb.git
```

  * Install dependencies, i.e. you need Sage. Inside the Sage environment `sage -sh`:
```
    easy_install -U flask
    easy_install -U flask-login
    easy_install -U pymongo
    easy_install -U flask-markdown
    easy_install -U flask-cache
    easy_install -U pyyaml
    easy_install -U unittest2
```
  * From the command-line:
    `
    sage -i gap_packages
    ` 
  (should check if we really need gap_packages.)
    `
    sage -i database_gap 
    `
    
  * Regarding !MathJax: No longer necessary to install !MathJax.

  `
  ssh -C -N -L 37010:localhost:37010 mongo-user@lmfdb.warwick.ac.uk
  ` 
  (please send your public SSH key to Harald Schilly, Jonathan Bober or John Cremona to make it work)

    * -C for compression of communication
    * -N to not open a remote shell, just a blocking command in the shell (end connection with Ctrl-C)
  If you don't have access to this server, you can temporarily start your own mongodb server and use it locally. There is no data (obviously) but it will work.
    * Mongo locally:
    ` 
    mongod --port 40000 --dbpath [db_directory] --smallfiles 
    `

Note: Inside Sage, you might have to update the setuptools first, i.e. ` easy_install -U setuptools `

Optional Parts
--------------

* `dirichlet_conrey.pyx`:
```
goto [https://github.com/jwbober/conrey-dirichlet-characters its github page]
download dirichlet_conrey.pyx and setup.py
run: `sage setup.py install`
if it doesn't compile, update sage's cython and then try again:
    `sage -sh`
    `easy_install -U cython`
    `exit`
either case, rebuild sage afterwards:
    `sage -b`
```

* Lfunction plots:

To get plots locally:

From within sage
```
     hg_sage.apply("http://trac.sagemath.org/raw-attachment/ticket/8621/trac8621.patch")
     hg_sage.apply("http://trac.sagemath.org/raw-attachment/ticket/8621/trac8621_review_rebase.patch")

```

Then rebuild:

```
     sage -b
```

* Memcache:

```
   ` easy_install -U python-memcached` or even better and only possible if you have the dev headers: ` easy_install -U pylibmc `
   install *memcached* (e.g. ` apt-get install memcached `)
   run the service at 127.0.0.1:11211
```

Running
=======

Once everything is setup, `sage -python start-lmfdb.py` should do the trick, but there can be some problems running in debug mode, so you might have omit the `--debug` (`--debug` doesn't work right now, but will soon!).  Once the server is running, visit http://localhost:37777/

Maybe, you have to suppress loading of your local python libraries: `sage -python -s start-lmfdb.py`

If you use a local MongoDB instance, specify its port:  `sage  -python start-lmfdb.py --debug --dbport 40000` 

Troubleshooting
===============

Sometimes the `pymongo` module is not able to connect to the database.
It works, if you force it to an earlier version:

    easy_install pymongo==2.4.1

Sharing Your Work
=================

 * Get a (free) github account if you do not have one already
 * Login to github
 * Go to `https://github.com/LMFDB/lmfdb` and click on `Fork` in the upper right corner
 * On your machine, create a new directory and type
```
    git init
    git clone git@github.com:YourGithubUserId/lmfdb.git
```
  using your own github user id. 
 * Push your code to the fork.
 * Tell the [lmdb mailing list](https://groups.google.com/forum/#!forum/lmdb) that you have some new code!
