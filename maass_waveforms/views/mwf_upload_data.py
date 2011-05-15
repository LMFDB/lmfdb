r"""
Upload data and insert into database for Maass waveforms.


"""
from mwf_utils import *

import flask
from flask import render_template, url_for, request, redirect, make_response,send_file
import bson
from sets import Set
import pymongo
from sage.all import is_odd,is_even

# Make a list of the entries which we allow to be put in the database
# Hardcoded for simplicity
# also hard-code the proper ordering of keys
allowed_entries={
    'ordered_keys':['N','k','char','R','sym','fricke','err','grp','misc'],
    'N'     :{'name':'Level'     ,'type':'Integer'},
    'k'     :{'name':'Weight'    ,'type':'Integer'},
    'char'  :{'name':'Charakter' ,'type':'Integer'},
    'R'     :{'name':'Eigenvalue','type':'Real'},
    'sym'   :{'name':'Type'      ,'type':'Integer'},
    'fricke':{'name':'Fricke eigenvalue','type':'Complex'},    
    'err'   :{'name':'Error Estimate','type':'Real'},
    'misc'  :{'name':'Misc.'     ,'type':'String'},
    'grp'   :{'name':'Group.'    ,'type':'String'},
    }

def check_data(info):
    r"""
    Check data for upload to see that it follows 
    the requested format.
    """
    f=info['files']
    mimetype = f.content_type
    print "mimetype=", mimetype
    s="<table>"
    s+="<thead><tr>"
    for (name,key) in info['format']:
        s+="<td>%s </td>" % name
    for l in f:
        print l
        data=l.split(' ')
        

        ## Try to parse the file with info['format'] as keys

    #datafiles.save(f)

def get_format_for_file_to_db(info):
    r"""

    """
    
    if not info.has_key("field0"):
        return ""
    fields=dict()
    for i in range(len(info.keys())):
        fld="field"+str(i)
        if info.has_key(fld):
            fields[i]=info[fld]
    return fields



def get_args_upload():
    r"""
    Extract parameters for upload data.
    Note: we need a "post" here
    """
    info=dict()
    if request.method == 'GET':
	info   = to_dict(request.args)
        print "req:get=",request.args
    else:
	info   = to_dict(request.form)
        print "req:post=",request.form
    # fix formatting of certain standard parameters
    info['files'] = request.files['file']
    tmp=get_format_for_file_to_db(info)
    info['format']= tmp
    return info
    
