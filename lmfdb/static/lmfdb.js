/* this file contains global javascript code for all parts of the lmfdb website
   it's just one file for faster page loading */

/* global logger */
function log(msg) {
  if(window.console != undefined) { console.log(msg); }
}

function error(msg) {
  if(window.console != undefined) { console.error(msg); }
}

/* beta logo displayed /w delay, -beta is default, so that it shows up when js
 * is disabled */
//$(function() {
//  $("#logo img").attr("src", '/static/images/lmfdb-logo.png');
//  window.setTimeout(function() {
//    $("#logo img").attr("src", '/static/images/lmfdb-logo-beta.png');
//  }, 2000);
//});

/* code for the properties sidepanel on the right */
/* jquery helper function, rotates element via css3 */
$.fn.rotate = function(rot) {
  this.css("-webkit-transform", "rotate("+rot+"deg)" );
  this.css("-moz-transform", "rotate("+rot+"deg)" );
  this.css("-o-transform", "rotate("+rot+"deg)" );
}

/* jquery helper function, bottom left round corner */
$.fn.round_bl = function(val) {
  this.css("border-bottom-left-radius", val + "px");
  this.css("-moz-border-radius-bottomleft", val + "px");
}

/** collapser: stored height is used to track progress. */
function properties_collapser(evt) {
  evt.preventDefault();
  var $pb = $(".properties-body");
  var $pc = $("#properties-collapser");
  var $ph = $(".properties-header");
  var pb_h = $pb.height();
  $pb.animate({"height": "toggle", "opacity" : "toggle"}, 
    {
      duration: 50 + 100 * Math.log(100 + $pb.height()),
      step: function() { 
       /* synchronize icon rotation effect */
       var val = $pb.height() / pb_h;
       var rot = 180 - 180 * val;
       $pc.rotate(rot);
       $ph.round_bl(0);
      },
      complete: function () {
        if ($pb.css("display") == "none") {
          $pc.rotate(180);
          $ph.round_bl(10);
        } else {
          $pc.rotate(0);
        }
      }
    }
  ); //~~ end animate
}


$(function() {
 /* properties box collapsable click handlers */
 $(".properties-header,#properties-collapser").click(function(evt) { properties_collapser(evt); });
 /* providing watermark examples in those forms, that have an 'example=...' attribute */
 /* Add extra spaces so that if you type in exactly the example it does not disappear */
 $('input[example]').each(function(a,b) { $(b).watermark($(b).attr('example')+'   '  ) } )
 $('textarea[example]').each(function(a,b) { $(b).watermark($(b).attr('example')+'   ', {useNative:false}  ) } )
});


/* javascript code to generate the properties box */
function properties_lfun(initialFriends, label, nf_url, conrey_indexes, rel_dim) {
  //body reference
  var body = document.getElementById("properties_script").parentElement
  var ul = document.createElement('ul');
  function add_friend(ulelement, text, href) {
    var friend = document.createElement('li');
    var url = document.createElement('a');
    url.appendChild(document.createTextNode(text));
    url.href = href;
    friend.appendChild(url);
    ulelement.appendChild(friend);
  }
  // initialFriends
  for (var k = 0; k < initialFriends.length; k++) {
    add_friend(ul, initialFriends[k][0], initialFriends[k][1]);
  }
  renderMathInElement(ul, katexOpts);

  for (var i = 0; i < conrey_indexes.length; i++) {
    for (var j = 1; j <= rel_dim; j++) {
      var lfun_text = 'L-function ' + label + '.' + conrey_indexes[i].toString() + '.' + j.toString();
      var lfun_url = '/L'+nf_url + '/' + conrey_indexes[i].toString() + '/' + j.toString();
      add_friend(ul, lfun_text, lfun_url);
    }
  }
  body.appendChild(ul);
}


/* javascript code for the knowledge db features */
/* global counter, used to uniquely identify each knowl-output element
 * that's necessary because the same knowl could be referenced several times
 * on the same page */
var knowl_id_counter = 0;
/* site wide cache, TODO html5 local storage to cover whole domain
 * /w a freshness timeout of about 10 minutes */
var knowl_cache = {};

//something like this should work:
//parseInt($('.knowl-output').css('border-left-width')) + parseInt($('.knowl-output').css('margin'));
var table_border_knowl_width = 20;


function knowl_click_handler($el) {
  // the knowl attribute holds the id of the knowl
  var knowl_id = $el.attr("knowl");
  // the uid is necessary if we want to reference the same content several times
  var uid = $el.attr("knowl-uid");
  var output_id = '#knowl-output-' + uid;
  var $output_id = $(output_id);

  // slightly different behaviour if we are inside a table, but
  // not in a knowl inside a table.
  var table_mode = $el.parent().is("td") || $el.parent().is("th");

  // if we already have the content, toggle visibility
  if ($output_id.length > 0) {
    if (table_mode) {
      $output_id.parent().parent().slideToggle("fast");
    }
    $output_id.slideToggle("fast");
    $el.toggleClass("active");

  // otherwise download it or get it from the cache
  } else {
    $el.addClass("active");
    // create the element for the content, insert it after the one where the
    // knowl element is included (e.g. inside a <h1> tag) (sibling in DOM)
    var idtag = "id='"+output_id.substring(1) + "'";

    // behave a bit differently, if the knowl is inside a td or th in a table.
    // otherwise assume its sitting inside a <div> or <p>
    if(table_mode) {
      // assume we are in a td or th tag, go 2 levels up
      var td_tag = $el.parent();
      var tr_tag = td_tag.parent();

      // figure out max_width
      var row_width = tr_tag.width();
      var sidebar = document.getElementById("sidebar");
      if ( sidebar == undefined ) {
        var sibebar_width = 0;
      } else {
        var sibebar_width = sidebar.offsetWidth;
      }
      var header_width = document.getElementById("header").offsetWidth;
      var desired_main_width =  header_width - sibebar_width;
      log("row_width: " + row_width);
      log("desired_main_width: " + desired_main_width);
      // no larger than the current row width (for normal tables)
      // no larger than the desired main width (for extra large tables)
      // at least 700px (for small tables)
      // and deduce margins and borders
      var margins_and_borders = 2*table_border_knowl_width + parseInt(td_tag.css('padding-left')) + parseInt(td_tag.css('padding-right'))
      var max_width = Math.max(700, Math.min(row_width, desired_main_width)) - margins_and_borders;

      log("max_width: " + max_width);
      var style_wrapwidth = "style='max-width: " + max_width + "px; white-space: normal;'";

      //max rowspan of this row
      var max_rowspan = Array.from(tr_tag.children()).reduce((acc, td) => Math.max(acc, td.rowSpan), 0)
      log("max_rowspan: " + max_rowspan);

      //compute max number of columns in the table
      var cols = Array.from(tr_tag.children()).reduce((acc, td) => acc + td.colSpan, 0)
      cols = Array.from(tr_tag.siblings()).reduce((ac, tr) => Math.max(ac, Array.from(tr.children).reduce((acc, td) => acc + td.colSpan, 0)), cols);
      log("cols: " + cols);
      for (var i = 0; i < max_rowspan-1; i++)
        tr_tag = tr_tag.next();
      tr_tag.after(
        "<tr><td colspan='"+cols+"'><div class='knowl-output'" +idtag+ style_wrapwidth + ">loading '"+knowl_id+"' …</div></td></tr>");
      // For alternatinvg color tables
      tr_tag.after("<tr class='hidden'></tr>")
    } else {
      $el.parent().after("<div class='knowl-output'" +idtag+ ">loading '"+knowl_id+"' …</div>");
    }

    // "select" where the output is and get a hold of it
    var $output = $(output_id);
    var kwargs = $el.attr("kwargs");

    if(knowl_id == "dynamic_show") {
      log("dynamic_show: " + kwargs);
      $output.html('<div class="knowl"><div><div class="knowl-content">' + kwargs + '</div></div></div>');
      // Support for escaping html within a div inside the knowl
      // Used for code references in showing knowls
      var pretext = $el.attr("pretext");
      log("pretext: " + pretext);
      if (typeof pretext !== typeof undefined && pretext !== false) {
        $output.find("pre").text(pretext);
      }
      try
      {
        renderMathInElement($output.get(0), katexOpts);
      }
      catch(err) {
        log("err:" + err)
      }
      $output.slideDown("slow");
      // adjust width to assure that every katex block is inside of the knowl
      var knowl = document.getElementById(output_id.substring(1))
      var new_width = Array.from(knowl.getElementsByClassName("katex")).reduce((acc, elt) => Math.max(acc, elt.offsetWidth), 0) + margins_and_borders;
      log("new_width:" + new_width)
      if( new_width > max_width ) {
        log("setting maxWidth:" + new_width)
        knowl.style.maxWidth = new_width + "px";
      }
    } else if((!kwargs || kwargs.length == 0) && (knowl_id in knowl_cache)) {
      // cached? (no kwargs or empty string AND kid in cache)
      log("cache hit: " + knowl_id);
      $output.hide();
      $output.html(knowl_cache[knowl_id]);
      try
      {
        renderMathInElement($output.get(0), katexOpts);
      }
      catch(err) {
        log("err:" + err)
      }
      $output.slideDown("slow");

    } else {
      $output.addClass("loading");
      $output.show();
      log("downloading knowl: " + knowl_id + " /w kwargs: " + kwargs);
      $output.load('/knowledge/render/' + knowl_id + "?" + kwargs,
       function(response, status, xhr) {
        $output.removeClass("loading");
        if (status == "error") {
          $el.removeClass("active");
          $output.html("<div class='knowl-output error'>ERROR: " + xhr.status + " " + xhr.statusText + '</div>');
        } else if (status == "timeout") {
          $el.removeClass("active");
          $output.html("<div class='knowl-output error'>ERROR: timeout. " + xhr.status + " " + xhr.statusText + '</div>');
        } else {
          knowl_cache[knowl_id] = $output.html();
          $output.hide();

          // if it is the outermost knowl, limit its height of the content to 600px
          if ($output.parents('.knowl-output').length == 0) {
            $(output_id + " div.knowl-content").first().parent().addClass("limit-height");
          }
        }
         // in any case, reveal the new output after math rendering has finished
         try
         {
           renderMathInElement($output.get(0), katexOpts);
         }
         catch(err) {
           log("err:" + err)
         }
         $output.slideDown("slow");
         // adjust width to assure that every katex block is inside of the knowl
         var knowl = document.getElementById(output_id.substring(1))
         var new_width = Array.from(knowl.getElementsByClassName("katex")).reduce((acc, elt) => Math.max(acc, elt.offsetWidth), 0) + margins_and_borders;
         if( new_width > max_width ) {
           knowl.style.maxWidth = new_width + "px";
         }
       });
    } // ~~ end not cached
  }
} //~~ end click handler for *[knowl] elements

/** register a click handler for each element with the knowl attribute 
 * @see jquery's doc about 'live'! the handler function does the 
 *  download/show/hide magic. also add a unique ID, 
 *  necessary when the same reference is used several times. */
function knowl_handle(evt) {
      evt.preventDefault();
      var $knowl = $(this);
      if(!$knowl.attr("knowl-uid")) {
        log("knowl-uid = " + knowl_id_counter);
        $knowl.attr("knowl-uid", knowl_id_counter);
        knowl_id_counter++;
      }
      knowl_click_handler($knowl, evt);
  }
$(function() {
  $("body").on("click", "*[knowl]", debounce(knowl_handle,500, true));
});

/*** end knowl js section ***/

/* global ajax event hook, for top right corner */
$(function() {
  var clear_timeout_id = null;
  var start_time = null;
  function clear(hideit, hideimg) {
    if(clear_timeout_id) {
      window.clearTimeout(clear_timeout_id);
      clear_timeout_id = null;
    }
    if (hideimg) $("#communication-img").hide();
    if (hideit) {
      $("#communication").append(" ["+((new Date()).getTime() - start_time) + "ms]");
      clear_timeout_id = window.setTimeout(
         function() {
           $("#communication-wrapper").fadeOut("slow");
         }, 1000);
    } else {
           $("#communication-wrapper").fadeIn("fast");
    }
  }
  $('#communication')
    .bind("ajaxSend", 
      function() { 
         $("#communication-img").fadeIn("slow");
         start_time = (new Date()).getTime(); 
         $(this).text("loading"); clear(false, false); })
    .bind("ajaxComplete", 
      function() { $(this).text("success"); clear(true, true); })
    .bind("ajaxError",
      function() { $(this).text("error"); clear(false, true); })
    .bind("ajaxStop",
      function() { $(this).text("done"); clear(true, true); });
});

function decrease_start_by_count_and_submit_form(form_id) {
  startelem = $('input[name=start]');
  count = parseInt($('input[name=count]').val());
  newstart = parseInt(startelem.val())-count;
  if(newstart<0) 
    newstart = 0;
  startelem.val(newstart);
  pagingelem = $('input[name=paging]');
  if (typeof pagingelem != 'undefined')
    pagingelem.val(1);
  $('form[id='+form_id+']').submit()
};
function increase_start_by_count_and_submit_form(form_id) {
  startelem = $('input[name=start]');
  count = parseInt($('input[name=count]').val());
  startelem.val(parseInt(startelem.val())+count);
  pagingelem = $('input[name=paging]');
  if (typeof pagingelem != 'undefined')
    pagingelem.val(1);
  $('form[id='+form_id+']').submit()
};

function get_count_of_results(download_limit) {
    var address = window.location.href;
    $("#result-count").html("computing...");
    $("#download-msg").html("Computing number of results...");
    if (address.slice(-1) === "#")
        address = address.slice(0,-1);
    address += "&result_count=1";
    var callback = function(res) {
        get_count_callback(res, download_limit);
    }
    $.ajax({url: address, success: callback});
};

function get_count_callback(res, download_limit) {
    $('#result-count').html(res['nres']);
    if (parseInt(res['nres'], 10) > download_limit) {
        $("#download-msg").html("There are too many search results for downloading.");
    } else {
        $("#download-msg").html("");
        $("#download-form").show();
    }
};

function js_review_knowl(kid) {
    var address = window.location.href;
    if (address.slice(-1) === "#")
        address = address.slice(0,-1);
    address = address + "?review=" + kid;
    kid = kid.replace('.','');
    $("#to_review_"+kid).hide("fast");
    //$("#to_review_"+kid.replace('.','')).html("HELLO");
    var callback = function(res) {
        js_review_callback(res, kid);
    }
    $.ajax({url: address, success: callback});
}
function js_review_callback(res, kid) {
    if (res['success'] === 1) {
        $('#to_beta_'+kid).show("fast");
    } else {
        $('#error_'+kid).show("fast");
    }
}

function js_beta_knowl(kid) {
    var address = window.location.href;
    if (address.slice(-1) === "#")
        address = address.slice(0,-1);
    address = address + "?beta=" + kid;
    kid = kid.replace('.','');
    $("#to_beta_"+kid).hide("fast");
    var callback = function(res) {
        js_beta_callback(res, kid);
    }
    $.ajax({url: address, success: callback});
}
function js_beta_callback(res, kid) {
    if (res['success'] === 1) {
        $('#to_review_'+kid).show("fast");
    } else {
        $('#error_'+kid).show("fast");
    }
}

function simult_change(event) {
    // simultaneously change all selects to the same value
    $(".simult_select").each(function (i) { this.selectedIndex = event.target.selectedIndex;});
};



function resetStart()
{
  // resets start if not changing search_type
  $('input[name=start]').val('')
  // this will be cleaned by the cleanSubmit
}

function cleanSubmit(id)
{
  var myForm = document.getElementById(id);
  var allInputs = myForm.getElementsByTagName('input');
  var allSelects = myForm.getElementsByTagName('select');
  var item, i, n = 0;
  for(i = 0; item = allInputs[i]; i++) {
    if (item.getAttribute('name') ) {
        // Special case count so that we strip the default value
        if (!item.value || (item.getAttribute('name') == 'count' && item.value == 50)) {
        item.setAttribute('name', '');
      } else {
        n++
      };
    }
  }
  for(i = 0; item = allSelects[i]; i++) {
    if (item.getAttribute('name') ) {
      if (!item.value) {
        item.setAttribute('name', '');
      } else {
        n++
      };
    }
  }
  if (!n) {
    var all = document.createElement('input');
    all.type='hidden';
    all.name='all';
    all.value='1';
    myForm.appendChild(all);
  }
}


/**
 * https://github.com/component/debounce
 * Returns a function, that, as long as it continues to be invoked, will not
 * be triggered. The function will be called after it stops being called for
 * N milliseconds. If `immediate` is passed, trigger the function on the
 * leading edge, instead of the trailing. The function also has a property 'clear' 
 * that is a function which will clear the timer to prevent previously scheduled executions. 
 *
 * Copyright (c) 2009-2018 Jeremy Ashkenas, DocumentCloud and Investigative
 * Reporters & Editors
 *
 * Permission is hereby granted, free of charge, to any person
 * obtaining a copy of this software and associated documentation
 * files (the "Software"), to deal in the Software without
 * restriction, including without limitation the rights to use,
 * copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following
 * conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 * OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 * WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */
function debounce(func, wait, immediate){
	var timeout, args, context, timestamp, result;
	if (null == wait) wait = 100;

	function later() {
		var last = Date.now() - timestamp;

		if (last < wait && last >= 0) {
			timeout = setTimeout(later, wait - last);
		} else {
			timeout = null;
			if (!immediate) {
				result = func.apply(context, args);
				context = args = null;
			}
		}
	};

	var debounced = function(){
		context = this;
		args = arguments;
		timestamp = Date.now();
		var callNow = immediate && !timeout;
		if (!timeout) timeout = setTimeout(later, wait);
		if (callNow) {
			result = func.apply(context, args);
			context = args = null;
		}

		return result;
	};

	debounced.clear = function() {
		if (timeout) {
			clearTimeout(timeout);
			timeout = null;
		}
	};

	debounced.flush = function() {
		if (timeout) {
			result = func.apply(context, args);
			context = args = null;

			clearTimeout(timeout);
			timeout = null;
		}
	};

	return debounced;
};

/* Contracting and expanding statistics displays */

function show_stats_rows(hsh, to_show) {
  $('.short_table_' + hsh).hide();
  $('.long_table_' + hsh).hide();
  $('.' + to_show + '_table_' + hsh).show();
  var elementBottom = $('#' + hsh + '-anchor').offset().top() + $('#' + hsh + '-anchor').outerHeight();
  var viewportTop = $(window).scrollTop();
  return elementBottom < viewportTop;
};

/* Show/hide sidebar */
$(document).ready(function () {
  console.log("ready");
  console.log(document.cookie);
  $('#menutoggle').click(
    function (evt) {
      evt.preventDefault();
      var sidebar = $('#sidebar');
      var main = $('#main');
      if( sidebar.is(":visible") )
      {
        $('#main').css( { "margin-left" : "0px", "transition": "margin 0.2s"} );
        sidebar.hide();
        document.cookie = 'showmenu=False;path=/';
        $('#menutoggle').text('Show Menu');
        console.log(document.cookie);
      } else {
        main.css( { "margin-left" : "200px", "transition": "margin 0.2s"} );
        sidebar.show("fast");
        document.cookie = 'showmenu=True;path=/';
        $('#menutoggle').text('Hide Menu');
        console.log(document.cookie);
      }
      return false;
    });
});
