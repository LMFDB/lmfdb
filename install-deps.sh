#/bin/sh
##
## Script to check and install dependencies under the sage shell
## Author: Fredrik Stromberg (2013)
## 
SAGEVERSION=`sage -v`
# Parse the (few) parameters we take
dry_run=0
verbose=0
for par in $@
do 
    if [ `expr match $par '-h'` -ge 1 ]
    then 
        echo "Parameters:"
        echo " -h -- Print help (this) message"
        echo " -n or -dry-run -- do a dry-run: check but do not install python packages"
        echo " -v -- verbose; output more info"
        exit
    fi
    if [ `expr match $par '-n'` -ge 1 ] || [ `expr match $par '-dry-run'` -ge 1 ]
    then
        dry_run=1
        echo "Do dry run!"
    fi
    if [ `expr match $par '-h'` -ge 1 ]
    then 
        verbose=1
    fi
done
# Grab the major version
i=`expr index "$SAGEVERSION" .` 
SAGE_MAJORVERSION=${SAGEVERSION:12:i-13} 
# Grab the minor version
j=`expr index "$SAGEVERSION" ,`
SAGE_ROOT=`sage -root`
if [ verbose = 1 ]
then
    echo "SAGE_ROOT is" $SAGE_ROOT
fi
SAGE_MINORVERSION=${SAGEVERSION:i:j-i-1} 
if [ $SAGE_MAJORVERSION -ge 5 ]  && [ $SAGE_MINORVERSION -ge 7  ]
then
   echo "Sage version $SAGE_MAJORVERSION.$SAGE_MINORVERSION is ok!"
else
   echo "Sage version $SAGE_MAJORVERSION.$SAGE_MINORVERSION is too old!"
   t=`grep "$SAGE_ROOT"/devel/sage/sage/structure/sequence.py "13998"`
   # Check if the patch has been applied...
   t=`grep -c 13998 $SAGE_ROOT/devel/sage/sage/structure/sequence.py`
   if [ $t -ge 1 ]
   then
       echo "This will (presumably) work since patch from 13998 is applied."
   else
       echo "Please update Sage (or apply patch from trac ticket 13998)"
   fi
fi
### Now check packages and install / upgrade / downgrade
deps="flask flask-login flask-cache flask-markdown pymongo==2.4.1 pyyaml"
if [ $SAGE_MAJORVERSION = 5 ]  && [ $SAGE_MINORVERSION = 10  ]
then
    # We set the environment variables from sage (the same as when running sage -sh)
    . "$SAGE_ROOT/spkg/bin/sage-env" >&2
    for dep in $deps
    do
        if [ $dry_run = 1 ]
        then
            easy_install -n $dep
        else
            easy_install $dep
        fi
    done
fi

