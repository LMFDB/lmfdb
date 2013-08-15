#/bin/sh
##
## Script to check and install dependencies under the sage shell
## Author: Fredrik Stromberg (2013)
## 
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
        echo " -sage=path-to-sage -- use a specific sage, if not set we use the system default"
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
            sage_exec=`which sage`
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
if [ verbose = 1 ]
then
    echo "sage_exec is " $sage_exec
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
       if [ $SAGE_MINORVERSION -lt 6  ]
           then
           echo "This sage version is completely unsupported. Please do update!"
           exit
           fi
   fi
fi
###
### Now check packages and install / upgrade / downgrade
###
### TODO: add different tested versions of the dependencies (possibly different for different sage versions)
checked_versions="8 10"
deps="flask==0.10.1 flask-login==0.2.6 flask-cache==0.12 flask-markdown==0.3 pymongo==2.4.1 pyyaml==3.10"
if ! [[ $checked_versions =~ $SAGE_MINORVERSION  ]]
then 
    echo "This minor version is not tested. If something doesn't work please test to down/upgrade packages and add appropriate dependencies."
fi

if [ $SAGE_MAJORVERSION -ge  5 ]  && [[ $checked_versions =~ $SAGE_MINORVERSION  ]]
then
    # We set the environment variables from sage (the same as when running sage -sh)
    . "$SAGE_ROOT/spkg/bin/sage-env" >&2
    for dep in $deps
    do
        if [ $verbose = 1 ] 
        then
            echo $dep
        fi
        if [ $dry_run = 1 ]
        then
            easy_install -n $dep
        else
            easy_install $dep
        fi
    done
fi

