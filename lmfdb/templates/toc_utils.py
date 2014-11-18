
def linked_name(item, level=""):
    """ take the dictionary describing a TOC entry and return the
    title wrapped in an appropriate href link.

    """

    this_entry = ""
    if level == "heading":
        if 'url_for' in item:
            this_entry += '<h2 class="link">\n'
            this_entry += '<a href="{{url_for(' + item['url_for'] + ')}}">'
     #       this_entry += '<a href="' + item['url_for'] + '">'
            this_entry += item['title']
            this_entry += '</a>'
            this_entry += '</h2>\n'
        elif 'url' in item:
            this_entry += '<h2 class="link">\n'
            this_entry += '<a href="' + item['url'] + '">'
            this_entry += item['title']
            this_entry += '</a>'
            this_entry += '</h2>\n'
        else:
            this_entry += '<h2>\n'
            this_entry += item['title']
            this_entry += '</h2>\n'

    else:
        if 'url_for' in item:
            this_entry += '<a href="{{url_for(' + item['url_for'] + ')}}">'
       #     this_entry += '<a href="{{url_for(\'' + item['url_for'] + '\')}}">'
        #    this_entry += '<a href="' + item['url_for'] + '">'
            this_entry += item['title']
            this_entry += '</a>'
        elif 'url_character' in item:
            this_entry += '<a href="{{url_character(type=' + item['url_character'] + ')}}">'
            this_entry += item['title']
            this_entry += '</a>'
        elif 'url' in item:
            this_entry += '<a href="' + item['url'] + '">'
            this_entry += item['title']
            this_entry += '</a>'
        else:
            this_entry += item['title']

        if 'status' in item and item['status'] == 'future':
            this_entry = '<div class="future">' + this_entry + '</div>'

    return this_entry

################

def toc_css():

    thecss = """
  <style type="text/css">
#sidebar .L a {
    display: inline;
}

#sidebar .L {
    padding-right: 1em;
}

#sidebar .heading {
    padding-right: 1em;
    margin-bottom: 1em;
}

#sidebar div.L {
    margin: 8px;
 /*   padding-top: 5px;
*/
}

#sidebar table td a {
    padding: 2px 5px; 
    border-radius: 0;
}

#sidebar table td .subtitle {
    color: black;
}

#sidebar table td.borc .subtitle .future {
    margin-left: 5px;
}

#sidebar table td.borc .subtitle a {
    margin-left: 5px;
}

#sidebar table td p {
    padding: 2px 5px;
}

#sidebar table td.full .future  {
    padding: 2px 5px;
}

#sidebar .future { 
    color:rgb(180,180,180);
    display: inherit;
}

#sidebar table td .parts {
    padding-left: 15px;
}

#sidebar table td .subitem {
    padding-right: 15px;
}

#sidebar table td.rotation { overflow: hidden; }

#sidebar li a {
    background: inherit;
}

/*
#sidebar .test { color:rgb(150,0,0);}
#sidebar .test a { color:rgb(150,0,0);
*/
display: inline;
  background: none;
  padding: 0px;}
/*#sidebar .list li {
    padding: px;
}*/
#sidebar .list a {
  display: inline;
  background: none;
  padding: 0px;

}
#sidebar h2 {
      margin: 10px 0px 0px;}

p.rotation  {
             -moz-transform: rotate(270deg);
             -webkit-transform: rotate(270deg);
             -o-transform: rotate(270deg);
             -ms-transform: rotate(270deg);
             transform: rotate(270deg); }


#sidebar table th, #sidebar table td {
	text-align: left;
	padding: 0px;
}

#sidebar table.short{
        width: 200px;
        table-layout:fixed;
	border-width: 5px;
        border-bottom: 0px;
	border-style: solid;
	padding: 0px;
	border-spacing: 0px;
	border-color: #efe;
	border-collapse: separate;
}

#sidebar table.short td.bor{
/*	border-bottom: 5px solid #fff;
*/	padding: 0px;
	text-align: left;
}

#sidebar table.short td.nbor{
	padding: 0px; text-align: left;
}

#sidebar table.short td.borc{
	text-align: center;
/*	border-bottom: 5px solid #fff;
*/	padding: 0px;
}
 
#sidebar table.short td.full{
        text-align: left;
/*      border-bottom: 5px solid #fff;
*/      padding: 0px;
}

#sidebar table.short td.off { 
	text-align: center;	
/*	border-bottom: 5px solid #fff;
*/	padding: 0px
	background: #fff }

</style>

    """

    return thecss

######

def mathjax_header():

    theheader = """

<script type="text/x-mathjax-config">
MathJax.Hub.Config({
  extensions: ["tex2jax.js","TeX/AMSmath.js","TeX/AMSsymbols.js","asciimath2jax.js","MathMenu.js","MathZoom.js",
               "TeX/autobold.js" ,"TeX/noErrors.js","TeX/noUndefined.js" ],
  jax: ["input/TeX","input/AsciiMath","output/HTML-CSS"],
  TeX: {
   Macros: {
    C: '{\\\\mathbb{C}}',
    R: '{\\\\mathbb{R}}',
    Q: '{\\\\mathbb{Q}}',
    Z: '{\\\\mathbb{Z}}',
    F: '{\\\\mathbb{F}}',
    H: '{\\\\mathbb{H}}',
    HH: '{\\\\mathcal{H}}',
    integers: '{\\\\mathcal{O}}',
    SL: '{\\\\textrm{SL}}',
    GL: '{\\\\textrm{GL}}',
    PSL: '{\\\\textrm{PSL}}',
    PGL: '{\\\\textrm{PGL}}',
    Sp: '{\\\\textrm{Sp}}',
    GSp: '{\\\\textrm{GSp}}',
    Gal: '{\\\\mathop{\\\\rm Gal}}',
    Aut: '{\\\\mathop{\\\\rm Aut}}',
    Sym: '{\\\\mathop{\\\\rm Sym}}',
    End: '{\\\\mathop{\\\\rm Reg}}',
    Reg: '{\\\\mathop{\\\\rm Res}}',
    Ord: '{\\\\mathop{\\\\rm Ord}}',
    sgn: '{\\\\mathop{\\\\rm sgn}}',
    trace: '{\\\\mathop{\\\\rm trace}}',
    Res: '{\\\\mathop{\\\\rm Res}}',
    ideal: ['{\\\\mathfrak{ #1 }}',1],
    classgroup: ['{Cl(#1)}',1],
    modstar: ['{\\\\left( #1/#2 \\\\right)^\\\\times}',2],
   },
  },
  tex2jax: {
    inlineMath: [['$','$'],["\\\\(","\\\\)"]],
    processEscapes: true,
  },
  asciimath2jax: { delimiters: [['#(',')#'], ['#[',']#']] },
  "HTML-CSS": { scale: 85 },
  menuSettings: { zscale: "150%", zoom: "Double-Click" }
});
</script>
<script type="text/javascript" src="http://cdn.mathjax.org/mathjax/latest/MathJax.js"></script>
    """

    return theheader
