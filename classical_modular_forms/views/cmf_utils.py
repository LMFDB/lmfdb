import random
from flask import  jsonify
from utils import *


def ajax_more2(callback, *arg_list, **kwds):
    r"""
    Like ajax_more but accepts increase in two directions.
    Call with
    ajax_more2(function,{'arg1':[x1,x2,...,],'arg2':[y1,y2,...]},'text1','text2')
    where function takes two named argument 'arg1' and 'arg2'
    """
    inline = kwds.get('inline', True)
    text = kwds.get('text', 'more')
    print "inline=",inline
    
    print "text=",text
    text0 = text[0]
    text1 = text[1]
    print "arglist=",arg_list
    nonce = hex(random.randint(0, 1<<128))
    if inline:
        args = arg_list[0]
        print "args=",args
        key1,key2=args.keys()
        l1=args[key1]
        l2=args[key2]
        print "key1=",key1
        print "key2=",key2
        print "l1=",l1
        print "l2=",l2
        args={key1:l1[0],key2:l2[0]}
        l11=l1[1:]; l21=l2[1:]
        #arg_list = arg_list[1:]
        arg_list1 = {key1:l1,key2:l21}
        arg_list2 = {key1:l11,key2:l2}
        #print "arglist1=",arg_list
        if isinstance(args, tuple):
            res = callback(*arg_list)
        elif isinstance(args, dict):
            res = callback(**args)
        else:
            res = callback(args)
            res = web_latex(res)
    else:
        res = ''
    print "arg_list1=",arg_list1
    print "arg_list2=",arg_list2
    arg_list1=(arg_list1,)
    arg_list2=(arg_list2,)
    if arg_list1 or arg_list2:
        url1 = ajax_url(ajax_more2, callback, *arg_list1, inline=True, text=text)
        url2 = ajax_url(ajax_more2, callback, *arg_list2, inline=True, text=text)
        print "arg_list1=",url1
        print "arg_list2=",url2
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
    print "text=",text
    print "arglist=",arglist
    print "kwds=",kwds
    #print "req=",request.args
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
    print "text=",text
    print "arglist=",arglist
    print "kwds=",kwds
    print "callback=",callback
    #print "req=",request.args
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
        print "ajax_url=",url
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
        print "s0+s1=",s2+s0
        return s2+s0+s1
    else:
        res = callback(do_now=do_now)
        return jsonify(result=res)



