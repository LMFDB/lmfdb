Installation
============

* To develop and contribute new code, see below on Sharing Your
  Work. If you **only** want to run a copy of the site, move into a
  new directory and type

  ```
     git clone git@github.com:LMFDB/lmfdb.git lmfdb
  ```

  but **follow the instructions below instead** (see *Code development
  and sharing your work*) to set up your own fork on github and clone
  from there if you want to carry out development on the code.

* Make sure you have sage (>=6.8) installed and that
  `sage` is available from the commandline.

* Install dependencies.  This requires you to have write access to the
  Sage installation directory, so should be no problem on a personal
  machine, but if yo are using a system-wide Sage install on a shared
  machine, you will need ask a system administrator to do this step.

   ```
      sage -i gap_packages
      sage -i database_gap
      sage -i pip
      sage -b
      # in the `lmfdb/` directory:
      sage -pip install -r requirements.txt
   ```

  * [optional] Memcache.  *This step is not at all necessary and can
    safely be ignored!* Memcache speeds up recompilation of python
    modules during development.  Using it requires both installing the
    appropriate package for your Operating System and installing an
    additional python module.  The first line below needs to be run in
    a Sage shell, and the for second you need to be a super-user to
    install memcached if your machine does not have it.

    * `easy_install -U python-memcached`

    or even better and only possible if you have the dev headers:

    * `easy_install -U pylibmc`

    * install *memcached* (e.g. ` apt-get install memcached `) and
    run the service at `127.0.0.1:11211`

Running
=======

* You need to connect to the lmfdb database on the machine
  lmfdb.warwick.ac.uk, using ssh tunelling so that your local
  machine's port 37010 (where the website code expects the database to
  be running) maps to the same port number on the database server.
  For this to work you must first send your public SSH key (as an
  email attachment preferably) to Harald Schilly, Jonathan Bober or
  John Cremona who will install it on the database server
  lmfdb.warwick.ac.uk.  To make life easier, the necessary ssh command
  is in the lmfdb root directory in the script warwick.sh, so just
  type

  ```
     ./warwick.sh &
  ```

  The ampersand here makes this run in the background, so you should
  not have to run this more than once unless you close the current
  shell or logout.

* If you don't have access to this server, you can temporarily start
    your own mongodb server and use it locally.  There is no data
    (obviously) but it will work.  To start mongo locally (after
    installing mongo on your machine):

    ```
       mongod --port 40000 --dbpath [db_directory] --smallfiles
    ```

* Now you can launch the webserver like this:

  ```
     sage -python start-lmfdb.py --debug
  ```

  * The effect of the (optional) --debug is that you will be running
  with the beta flag switched on as at beta.lmfdb.org, and also that
  if code fails your browser will show useful debugging information.
  Without `--debug` what you see will be more like www.lmfdb.org.

* Once the server is running, visit http://localhost:37777/

* You may have to suppress loading of your local python libraries: `sage -python -s start-lmfdb.py`

* If you use a local MongoDB instance, specify its port:  `sage  -python start-lmfdb.py --debug --dbport 40000`

* If several people are running their own version of the webserver on
    the same machine, they cannot all use port 37777 -- if they try,
    they can get very confused.  In such a scenario, all involved
    should agree to using a sequence of port numbers from 37700
    upwards and allocate one such number to each user, then add it to
    the command line: e.g.

    ```
       sage -python ./start-lmfdb.py --debug -p 37702
    ```

    To avoid having to remember that, it is a good idea to define an
    alias for this.  e.g. with bash you can insert the line

    ```
    function start_lmfdb () { sage -python ./start-lmfdb.py --debug -p 37702;}
    ```

    in your .bashrc file, so that all you have to type to start the
    server is `start_lmfdb`.

* When running with `--debug`, whenever a python (*.py) file changes
      the server will reload automatically.  If you save while editing
      at a point where such a file is not syntactically correct, the
      server will crash and you will need to `start_lmfdb` again.   Any
      changes to html files will not cause the server to restart, so
      you will need to reload the pages in your borowser.  Changes in
      the yaml files which are read only once at startup will require
      you to manually stop the server and restart it.

Troubleshooting
===============

If the `pymongo` module is not able to connect to the database, make
sure that the warwick.sh script is still running.

Code development and sharing your work
======================================

 * Get a (free) github account if you do not have one already
 * Login to github
 * Go to `https://github.com/LMFDB/lmfdb` and click on `Fork` in the upper right corner
 * On your machine, create a new directory and type

```
    git init
    git clone git@github.com:YourGithubUserId/lmfdb.git
```

  using your own github user id.  Your github repository will be known
  to git as a remote called `origin`.

 * Add the (official) LMFDB repository as a remote called `upstream`

```
    git remote add upstream git@github.com:LMFDB/lmfdb.git
```

 * You should make a new branch if you want to work on a new feature.
   The following command creates a new branch named `new_feature` and
   switches to that branch, after first switching to the master branch
   and making sure that it is up-to-date:

```
    git checkout master
    git pull upstream master
    git checkout -b new_feature
```

 * After making your local changes, testing them and committing the
   changes, push your branch to your own github fork:

```
    git push -u origin new_feature
```

   * Here, the option -u tells git to set up the remote branch
   `origin/new_feature` to be the corresponding upstream  branch you
   push to.

   * You should make sure from time to time that you pull the latest
  changes from the official LMFDB repository.  There are three
  branches upstream to be aware of: `prod`, `beta` and `master`:

    - `prod` is changed rarely and contains the code currently running at
      www.lmfdb.org
    - `beta` is changed more often and contains the code currently running at
      beta.lmfdb.org
    - `master` is the development branch.

   Normal developers only need to be aware of the master
   (=development) branch.

   * To pull in the most recent changes there to your own master
     branch locally and update your github repository too:

    ```
    git checkout master
    git pull upstream master
    git push origin master
    ```

   * To rebase your current working branch on the latest master:

   ```
   git pull --rebase upstream master
   ```

   * Tell the [lmdb mailing
     list](https://groups.google.com/forum/#!forum/lmdb) that you have
     some new code!  You should also issue a pull request at github
     (from your feature branch `new_feature`) at the same time.  Make
     sure that your pull request is to the lmfdb `master` branch,
     whatever your own development or feature branch is called.
     Others will review your code, and release managers will
     (eventually, if all is well) merge it into the master branch.

LMFDB On Windows
================

We do not recommend attempting to run LMFDB from within the Sage virtual image.
For anyone who would like to attempt it, the following steps should theoretically work.

 * Download `VirtualBox` and the Sage appliance, following the instructions [here](http://wiki.sagemath.org/SageAppliance).
 * The default Sage appliance does not have enough space to install LMFDB's prerequisites.  Moreover, the default
   file type (vmdk) installed by `VirtualBox` does not support resizing.  You will need to
   increase the available space by cloning into a vdi file, increasing the space and cloning back, following the
   instructions [here](http://stackoverflow.com/questions/11659005/how-to-resize-a-virtualbox-vmdk-file) and
   [here](http://www.howtogeek.com/124622/how-to-enlarge-a-virtual-machines-disk-in-virtualbox-or-vmware/).  We had
   trouble at this stage: make sure to keep the .ova file in case you screw up your virtual image.
 * The resulting disk image needs to be repartitioned to make the space available.  Unfortunately, the Sage appliance
   does not include gparted, the linux partition editor.  So, you'll need to install gparted into the appliance
   (perhaps following instructions [here](https://gembuls.wordpress.com/2011/02/12/how-to-install-epel-repository-on-centos/))
   and use it to repartition.
 * You now need to set up port forwarding so that the sage appliance can use the ports 37777 and 37010 used by lmfdb.
   See Section 6.3.1 [here](https://www.virtualbox.org/manual/ch06.html).
 * Clone the LMFDB git repository into your host OS, and set up shared folders so that you can access
   the LMFDB code from within the Sage appliance.  See the [Sage instructions](http://wiki.sagemath.org/SageAppliance) for how to share folders.
 * Now you need to run ssh-keygen within the Sage appliance and e-mail the result to Harald Schilly, Jonathan Bober or John Cremona (see above).
   Since copy-and-paste can be tricky from inside the virtual image, we suggest writing to a file shared by the host OS.
 * The instructions for Linux/OS X should now work.  You should be able to forward the mongo database and run `sage -python start-lmfdb.py` within the Sage appliance,
   and access the resulting website from your host OS' web browser.
