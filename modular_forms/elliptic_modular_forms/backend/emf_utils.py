# -*- coding: utf-8 -*-
#*****************************************************************************
#  Copyright (C) 2010 Fredrik Strömberg <fredrik314@gmail.com>,
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#  The full text of the GPL is available at:
#
#                  http://www.gnu.org/licenses/
#*****************************************************************************
r"""
Utilities file for elliptic (holomorhic) modular forms.

AUTHOR: Fredrik Strömberg


"""
import random
from flask import  jsonify
from utils import *
from modular_forms.elliptic_modular_forms import EMF,emf, emf_logger
logger = emf_logger

def ajax_more2(callback, *arg_list, **kwds):
    r"""
    Like ajax_more but accepts increase in two directions.
    Call with
    ajax_more2(function,{'arg1':[x1,x2,...,],'arg2':[y1,y2,...]},'text1','text2')
    where function takes two named argument 'arg1' and 'arg2'
    """
    inline = kwds.get('inline', True)
    text = kwds.get('text', 'more')
    emf_logger.debug("inline={0}".format(inline))
    emf_logger.debug("text={0}".format(text))
    text0 = text[0]
    text1 = text[1]
    emf_logger.debug("arglist={0}".format(arg_list))
    nonce = hex(random.randint(0, 1<<128))
    if inline:
        args = arg_list[0]
        emf_logger.debug("args={0}".format(args))
        key1,key2=args.keys()
        l1=args[key1]
        l2=args[key2]
        emf_logger.debug("key1={0}".format(key1))
        emf_logger.debug("key2={0}".format(key2))
        emf_logger.debug("l1={0}".format(l1))
        emf_logger.debug("l2={0}".format(l2))
        args={key1:l1[0],key2:l2[0]}
        l11=l1[1:]; l21=l2[1:]
        #arg_list = arg_list[1:]
        arg_list1 = {key1:l1,key2:l21}
        arg_list2 = {key1:l11,key2:l2}
        #emf_logger.debug("arglist1={0}".format(arg_list))
        if isinstance(args, tuple):
            res = callback(*arg_list)
        elif isinstance(args, dict):
            res = callback(**args)
        else:
            res = callback(args)
            res = web_latex(res)
    else:
        res = ''
    emf_logger.debug("arg_list1={0}".format(arg_list1))
    emf_logger.debug("arg_list2={0}".format(arg_list2))
    arg_list1=(arg_list1,)
    arg_list2=(arg_list2,)
    if arg_list1 or arg_list2:
        url1 = ajax_url(ajax_more2, callback, *arg_list1, inline=True, text=text)
        url2 = ajax_url(ajax_more2, callback, *arg_list2, inline=True, text=text)
        emf_logger.debug("arg_list1={0}".format(url1))
        emf_logger.debug("arg_list2={0}".format(url2))
        s0 = """<span id='%(nonce)s'>%(res)s """  % locals()
        s1 = """[<a onclick="$('#%(nonce)s').load('%(url1)s', function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text0)s</a>""" % locals()
        t = """| <a onclick="$('#%(nonce)s').load('%(url2)s', function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text1)s</a>]</span>""" % locals()
        return (s0+s1+t)
    else:
        return res

def ajax_url(callback, *args, **kwds):
    if '_ajax_sticky' in kwds:
        _ajax_sticky = kwds.pop('_ajax_sticky')
    else:
        _ajax_sticky = False
    if not isinstance(args, tuple):
        args = args,
    nonce = hex(random.randint(0, 1<<128))
    pending[nonce] = callback, args, kwds, _ajax_sticky
    return url_for('ajax_result', id=nonce)


def ajax_once(callback,*arglist,**kwds):
    r"""
    """
    
    text = kwds.get('text', 'more')
    emf_logger.debug("text={0}".format(text))
    emf_logger.debug("arglist={0}".format(arglist))
    emf_logger.debug("kwds={0}".format(kwds))
    #emf_logger.debug("req={0}".format(request.args
    nonce = hex(random.randint(0, 1<<128))
    res = callback()
    url = ajax_url(ajax_once,arglist,kwds,inline=True)
    s0 = """<span id='%(nonce)s'>%(res)s """  % locals()
    #	s1 = """[<a onclick="$('#%(nonce)s').load('%(url)s', {'level':22,'weight':4},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text)s</a>""" % locals()
    s1 = """[<a onclick="$('#%(nonce)s').load('%(url)s', {a:1},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text)s</a>""" % locals()
    return s0+s1


def ajax_later(callback,*arglist,**kwds):
    r"""
    Try to make a function that gets called after displaying the page.
    """
    
    text = kwds.get('text', 'more')
    text = 'more'
    emf_logger.debug("text={0}".format(text))
    emf_logger.debug("arglist={0}".format(arglist))
    emf_logger.debug("kwds={0}".format(kwds))
    emf_logger.debug("callback={0}".format(callback))
    #emf_logger.debug("req={0}".format(request.args
    nonce = hex(random.randint(0, 1<<128))
    # do not call the first time around
    if kwds.has_key("do_now"):
        if kwds['do_now']==1:
            do_now=0
        else:
            do_now=1
    else:
        do_now=0
    if not do_now:
        url = ajax_url(ajax_later,callback,*arglist,inline=True,do_now=do_now,_ajax_sticky=True)
        emf_logger.debug("ajax_url={0}".format(url))
        s0 = """<span id='%(nonce)s'></span>"""  % locals()
        s1 = """<a class='later' href=# id='%(nonce)s' onclick='this_fun()'>%(text)s</a>""" % locals()
        s2= """<script>
        function this_fun(){
        $.getJSON('%(url)s',{do_now:1},
        function(data) {
        $(\"span#%(nonce)s\").text(data.result);
        });
        return true;
        };
        </script>
        
        """ % locals()
        emf_logger.debug("s0+s1={0}".format(s2+s0))
        return s2+s0+s1
    else:
        res = callback(do_now=do_now)
        return jsonify(result=res)



class EmfTable(object):
    def __init__(self,db_name,skip=[0,0],limit=[6,10],keys=['Level','Eigenvalue'],weight=0):
        r"""
        Table of HOlomorphic modular forms spaces.
        Skip tells you how many chunks of data you want to skip (from the geginning) and limit tells you how large each chunk is.
        """
        self.keys=keys
        self.skip=skip
        self.limit=limit
        self.db = connect_db()
        self.metadata=[]
        self.title=''
        self.cols=[]
        self.get_collections()
        self.table=[]
        self.wt=weight

    def shift(self,i=1,key='Level'):
        if not key in self._keys:
            logger.warning("{0} not a valid key in {1}".format(key,self._keys))
        else:
            ix = self._keys.index[key]
            self.skip[ix]+=i

    def get_collections(self):
        cols = get_collection(self.collection)        
        if not cols:
            cols=list()
            for c in self.db.collection_names():
                if c<>'system.indexes' and c<>'metadata':
                    print "cc=",c
                cols.append(self.db[c])        
        self.cols=cols

    def get_metadata(self):
        if not self.cols:
            self.get_collections()
        metadata=list()
        for c in self.cols:
            f=self.db.metadata.find({'c_name':c.name})
            for x in f:
                print "x=",x
                metadata.append(x)
        self.metadata=metadata
        

    def set_table(self):
        logger.debug("skip= {0}".format(self.skip))
        logger.debug("limit= {0}".format(self.limit))
        self.table=[]
        level_ll=(self.skip[self.keys.index('Level')])*self.limit[self.keys.index('Level')]
        level_ul=(self.skip[self.keys.index('Level')]+1)*self.limit[self.keys.index('Level')]
        ev_limit=self.limit[self.keys.index('Eigenvalue')]
        ev_skip=self.skip[self.keys.index('Eigenvalue')]*ev_limit
        for N in get_all_levels():
            N=int(N)
            if N<level_ll:
                continue
            if N>level_ul:
                break
            evs=[]
            for c in self.cols:
                finds=c.find({'Level':N,'Weight':self.wt}).sort('Eigenvalue',1).skip(ev_skip).limit(ev_limit);
                for f in finds:
                    _id = f['_id']
                    R = f['Eigenvalue']
                    url = url_for('mwf.render_one_maass_waveform',objectid=str(_id),db=c.name)
                    evs.append([R,url,c.name])
            evs.sort()
            # If we have too many we delete the 
            while len(evs)>ev_limit:
                t=evs.pop()
                logger.debug("removes {0}".format(t))
            #logger.debug("found eigenvalues in {0} is {1}".format(c.name,evs))
            self.table.append({'N':N,'evs':evs})
        
