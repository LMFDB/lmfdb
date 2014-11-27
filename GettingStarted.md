Installation
============

* To contribute, see below on sharing your work. To simply run a copy of the site move into a new directory and type
  ```
     git clone git@github.com:LMFDB/lmfdb.git lmfdb
  ```

* Make sure you have sage (>=6.4) installed and that
  `sage` is available from the commandline

* Install dependencies (in the `lmfdb/` directory):
  ```
      sage -i gap_packages
      sage -i database_gap
      sage -i pip
      sage -pip install -r requirements.txt
  ```

  * [optional] Memcache:

   ` easy_install -U python-memcached` or even better and only possible if you have the dev headers: ` easy_install -U pylibmc `
   install *memcached* (e.g. ` apt-get install memcached `)
   run the service at `127.0.0.1:11211`

Running
=======

* You need to connect to the lmfdb database
  ```
     ssh -C -N -L 37010:localhost:37010 mongo-user@lmfdb.warwick.ac.uk 
  ```
  (please send your public SSH key to Harald Schilly, Jonathan Bober or John Cremona to make it work)

  * -C for compression of communication
  * -N to not open a remote shell, just a blocking command in the shell (end connection with Ctrl-C)
  * If you don't have access to this server, you can temporarily start your own mongodb server and use it locally.
    There is no data (obviously) but it will work.
    Mongo locally:
    ``` 
       mongod --port 40000 --dbpath [db_directory] --smallfiles 
    ``` 

* Then launch the webserver
  ```
     sage -python start-lmfdb.py
  ```
  should do the trick, but there can be some problems running in debug mode, so you might have omit the `--debug`
  (`--debug` doesn't work right now, but will soon!).

* Once the server is running, visit http://localhost:37777/

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
 * Add the (official) LMFDB repository as a remote called `upstream`
```
    git remote add upstream git@github.com:LMFDB/lmfdb.git
```
 * You should make a new branch if you want to work on a new feature.
   The following command creates a new branch named `new_feature` and switches to that branch.
```
    git checkout -b new_feature
```
 * Push your code to your own fork.
```
    git push -u origin new_feature
```
   Here, the option -u tells git to set up the remote branch `origin/new_feature` to be the corresponding upstream
   branch you push to.
 * Also, you should make sure from time to time that you pull the latest changes from the official LMFDB repository.
   For this reason, we added it to the remotes. Now you can do
```
    git pull --rebase upstream 
```
 * Tell the [lmdb mailing list](https://groups.google.com/forum/#!forum/lmdb) that you have some new code!
 * You should also issue a pull request at github (from your feature branch `new_feature`) at the same time.
