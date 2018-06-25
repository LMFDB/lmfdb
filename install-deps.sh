#/bin/bash
##
## Script to check and install dependencies under the sage shell
## Author: Fredrik Stromberg (2013)
## 
# Parse the (few) parameters we take
dry_run=0
verbose=0
force_install=0
sage_exec=`which sage`
for par in $@
do 
    if [ `expr match $par '-h'` -ge 1 ]
    then 
        echo "Parameters:"
        echo " -h -- Print help (this) message"
        echo " -n or -dry-run -- do a dry-run: check but do not install python packages"
        echo " -v -- verbose; output more info"
        echo " -f : force installation of packages even if version is not tested"
        echo " -sage=path-to-sage -- use a specific sage, if not set we use the system default"
	echo " -u --user -- do install packages in the user directory, not in the system-wide installation"
        echo " Observe that some matching stuff does not work with all shell versions. Use -f in this case." 
        exit
    fi
    if [ `expr match $par '-n'` -ge 1 ] || [ `expr match $par '-dry-run'` -ge 1 ]
    then
        dry_run=1
        echo "nothing will get installed! We do a dry run!"
    fi
    if [ `expr match $par '-f'` -ge 1 ]
    then 
        force_install=1
    fi
    if [ `expr match $par '-v'` -ge 1 ]
    then 
        verbose=1
    fi
    if [ `expr match $par '-u'` -ge 1 ] || [ `expr match $par '--user'` -ge 1 ]
    then
        user_install=1
        easy_opts="$easy_opts --user"
    fi
    if [ `expr match $par '-sage'` -ge 1 ]
    then 
        # extract executable
        i=`expr index "$par" =`
        sage_exec=${par:$i}
        if [[ -x $sage_exec ]]
        then
            echo $sage_exec "is exectuable!"
        else
            echo $sage_exec "is not exectuable!"
            exit
        fi
     fi
done
SAGEVERSION=`$sage_exec -v`
# Grab the major version
i=`expr index "$SAGEVERSION" .`
SAGE_MAJORVERSION=${SAGEVERSION:12:i-13} 
# Grab the minor version
j=`expr index "$SAGEVERSION" ,`
SAGE_ROOT=`$sage_exec -root`
if [ $verbose = 1 ]
then
    echo "sage_exec is " $sage_exec
    echo "SAGE_ROOT is" $SAGE_ROOT
    echo "SAGEVERSION is" $SAGEVERSION
fi
# Cut of any beta etc...
if [[ "$SAGEVERSION" =~ 'beta' ]]
then
    TMP=${SAGEVERSION:i:-1} 
    k=`expr index "$TMP" .`
    SAGE_MINORVERSION=${TMP:0:k-1}
else
    SAGE_MINORVERSION=${SAGEVERSION:i:j-i-1} 
fi
if [[ "$SAGE_MINORVERSION" =~ '.' ]]
then
    j=`expr index "$SAGE_MINORVERSION" .`
    SAGE_MINORVERSION=${SAGE_MINORVERSION:0:j-1} 
fi
if [ $verbose -ge 1 ]
then
    echo "SAGE_MINORVERSION is " $SAGE_MINORVERSION
fi
if [ $SAGE_MAJORVERSION -ge 5 ]  && [ $SAGE_MINORVERSION -ge 7  ] || [ $SAGE_MAJORVERSION -ge 6 ]
then
   echo "Sage version $SAGE_MAJORVERSION.$SAGE_MINORVERSION is ok!"
else
   echo "Sage version $SAGE_MAJORVERSION.$SAGE_MINORVERSION is too old!"
   t=`grep "$SAGE_ROOT"/devel/sage/sage/structure/sequence.py "13998"`
   # Check if the patch has been applied...
   t=`grep -c 13998 "$SAGE_ROOT"/devel/sage/sage/structure/sequence.py`
   if [ $t -ge 1 ]
   then
       echo "This will (presumably) work since patch from 13998 is applied."
   else
       echo "Please update Sage (or apply patch from trac ticket 13998)"
       if [ $SAGE_MINORVERSION -lt 6  ]
           then
           echo "This sage version is completely unsupported. Please do update!"
           exit
           fi
   fi
fi
###
### Now check python packages and install / upgrade / downgrade
###
### TODO: add different tested versions of the dependencies (possibly different for different sage versions)
checked_versions="8 10 11"

deps="flask flask-login flask-cache flask-markdown psycopg2 pyyaml unittest2"
#deps="flask==0.10.1 flask-login==0.2.6 flask-cache==0.12 flask-markdown==0.3 psycopg2==2.7.5 pyyaml==3.10"

if ! [[ $checked_versions =~ $SAGE_MINORVERSION  ]]
then 
    echo "This minor version is not tested. If something doesn't work please test to down/upgrade packages and add appropriate dependencies."
fi

if ([ $SAGE_MAJORVERSION -ge  5 ]  && [[ $checked_versions =~ $SAGE_MINORVERSION  ]] || [ $force_install = 1 ])
then
    # We set the environment variables from sage (the same as when running sage -sh)
    sage_env="$SAGE_ROOT/spkg/bin/sage-env"
    if ! [[ -e $sage_env ]]
    then
        sage_env="$SAGE_ROOT/src/bin/sage-env"
    fi
    . ""$sage_env"" >&2
    for dep in $deps
    do
        if [ $verbose = 1 ] 
        then
            echo $dep
        fi
        if [ $dry_run = 1 ]
        then
            easy_install -n $easy_opts $dep
        else
            easy_install -U $easy_opts $dep
        fi
    done
fi

###
### While we are at it we can also check for and install some of the required sage packages
###
sage_packages="gap_packages database_gap"
for package in $sage_packages
do
    if [ $dry_run = 1 ]
    then
        if [ $verbose -gt 0 ]
        then
            echo "Would have installed $package"
        fi
    else
        if [ $verbose -gt 0 ]
        then
            echo "Installing $package"
        fi
        $sage_exec -i "$package"
    fi
done
###
### And we also want to have DirichletCharacterconrey package
###
## First see if we already have it and if not we get an egg and install it.
##
test=`$sage_exec -c "print sys.modules.get('dirichlet_conrey')==None"` 
if [ $test='True' ]
then
    if [ $verbose -gt 0 ]
    then
        echo "Do not have dirichlet_conrey!"
    fi
    . ""$sage_env"" >&2
    if [ $dry_run = 1 ]
    then
        easy_install $easy_opts -n http://sage.math.washington.edu/home/stromberg/pub/DirichletConrey-0.1-py2.7-linux-x86_64.egg
    else
        easy_install $easy_opts http://sage.math.washington.edu/home/stromberg/pub/DirichletConrey-0.1-py2.7-linux-x86_64.egg
    fi
else
    if [ $verbose -gt 0 ]
    then
        echo "dirichlet_conrey is already installed!"
    fi

fi
