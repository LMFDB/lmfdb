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
      var header = document.getElementById("header");
      if ( header == undefined ) {
        var header_width = row_width;
      } else {
        var header_width = header.offsetWidth;
      }
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
      cols = Array.from(tr_tag.siblings("tr")).reduce((ac, tr) => Math.max(ac, Array.from(tr.children).reduce((acc, td) => acc + td.colSpan, 0)), cols);
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
      // log("downloading knowl: " + knowl_id + " /w kwargs: " + kwargs);
	  // the prefix holds the base URL prefix. why necessary? if you're running on cocalc, javascript doesn't know that this isn't just the base domain!
      $output.load(url_prefix + '/knowledge/render/' + knowl_id + "?" + kwargs,
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

function update_start_by_count_and_submit_form(sign) {
  var startelem = $('form.re-search input[name=start]');
  var count = parseInt($('form.re-search input[name=count]').val());;
  var newstart = parseInt(startelem.val())+sign*count;
  if(newstart<0)
    newstart = 0;
  startelem.val(newstart);
  $('form.re-search').submit()
};

function decrease_start_by_count_and_submit_form() {
  update_start_by_count_and_submit_form(-1);
};
function increase_start_by_count_and_submit_form() {
  update_start_by_count_and_submit_form(1);
};


// callbacks for the search page to get exact count. Used in matches.html
function get_count_of_results() {
    var address = window.location.href;
    $("#result-count").html("computing...");
    $("span.download-msg").html("Computing number of results...");
    if (address.slice(-1) === "#")
        address = address.slice(0,-1);
    if (address.includes("?")) {
        address += "&result_count=1";
    } else {
        address += "?result_count=1";
    }
    $.ajax({url: address, success: get_count_callback});
};

function get_count_callback(res) {
    $('#result-count').html(res['nres']);
    $('#result-count2').html(res['nres']);
    $("span.download-msg").html("");
    $("span.download-form").show();
};

/**
 * Fetches the elliptic curve with `label` and calls the reduction function.
 * Uses route /adelic_image_modm_reduce in ec_page, calls modm_reduce in elliptic_curve.py.
 * Modifies the html element in ec_curve.html.
 * 
 * @param label of elliptic curve
 * @param m integer to reduce the adelic image by
 */
function modm_reduction(label, m, cur_lang) {
  address = "/EllipticCurve/Q/adelic_image_modm_reduce?label=" + label + "&m=" + m + "&cur_lang=" + cur_lang;
  if (!$.isNumeric(m) || (+m <= 0) || (Math.floor(+m) !== +m)) {
    alert("Invalid input. Please enter a positive integer.");
  } else {
    $('#modm_reduction').html("<em>Computing...</em>");
    $.ajax({url: address, success: modm_reduction_callback});
  }
}

function modm_reduction_callback(res) {
  if (res === "\\text{Invalid curve or adelic image not computed}"){
    alert("Invalid curve or adelic image not computed");
    return;
  }

  res = res.split('.');
  var latex_gens = res[0];
  var level = res[1];
  var gens = res[2];
  var cur_lang = res[3];
  var index = res[4];
  // {# this div is a workaround for a copy-tex bug where if a code block followed a hidden code block followed by math was selected and copied the hidden block would be also it is important that it has display: block #}
  var line_break = '<br><div style="margin: 0; padding: 0; height: 0;">&nbsp;</div>';
  
  var sage_code = `gens = ${gens}${line_break}GL(2,Integers(${level})).subgroup(gens)${line_break}`;
  $('#sage_modm_image').html(sage_code);
  if (! $('#sage_modm_image').hasClass("sage")){
    $('#sage_modm_image').show();
    $('#sage_modm_image').addClass('sage nodisplay code codebox');
  }
  var magma_code = `Gens := ${gens};${line_break}sub&ltGL(2,Integers(${level}))|Gens&gt&semi;${line_break}`;
  $('#magma_modm_image').html(magma_code);
  if (! $('#magma_modm_image').hasClass("magma")){
    $('#magma_modm_image').show();
    $('#magma_modm_image').addClass('magma nodisplay code codebox');
  }
  $('.'+cur_lang).css('display','inline-block');

  var modm_text = `The reduction of ${katex.renderToString('H')} has index ${index} in ${katex.renderToString('\\mathrm{GL}_2(\\Z/'+level+'\\Z)')} and is generated by<br><br>${katex.renderToString(latex_gens)}.`;
  $('#modm_reduction').html(modm_text);
}

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

function control_column(S, i) {
  var show = $("input[name=showcol]");
  var shown_cols = show.val().split(".").filter(o=>o); // remove empty strings
  var hide = $("input[name=hidecol]");
  var hidden_cols = hide.val().split(".").filter(o=>o);
  var label = S.options[i].text;
  var label = label.slice(2, label.length);
  var value = S.options[i].value;
  $('.col-'+value).toggle();
  // For column groups, have to adjust the width of the top column
  $('th.col-'+value).each(function(i, obj) {
    // We need to adjust the column width for any colgroup header containing this column.
    // there should only be one in the list, but doing this more than once won't hurt.
    var classes = $(this).attr('class').split(' ');
    for (i = 0; i < classes.length; i++) {
      if (classes[i].startsWith("colgroup-")) {
        var colspan = $('th.'+classes[i]+':visible').length;
        var header = $('.col-' + classes[i].slice(9));
        if (colspan == 0) {
          header.hide();
        } else {
          header.show();
          header.prop("colSpan", $('th.'+classes[i]+':visible').length);
        }
      }
    }
  });
  if ($('.col-'+value+':visible').length > 0) {
    S.options[i].text = '✓ ' + label; // note that the space after the checkbox is unicode, the size of an en-dash
    var i = hidden_cols.indexOf(value);
    if (i == -1) {
      shown_cols.push(value);
      show.val(shown_cols.join("."));
    } else {
      hidden_cols.splice(i, 1);
      hide.val(hidden_cols.join("."));
    }
  } else {
    S.options[i].text = '  ' + label; // the spaces are unicode: an em-dash and a thinspace
    var i = shown_cols.indexOf(value);
    if (i == -1) {
      hidden_cols.push(value);
      hide.val(hidden_cols.join("."));
    } else {
      shown_cols.splice(i, 1);
      show.val(shown_cols.join("."));
    }
  }
};

function all_are_selected(S) {
  for (i = 1; i < S.options.length - 1; i++) {
    if (S.options[i].text[0] != '✓') {
      return false;
    }
  }
  return true;
}

function control_columns(S) {
  if (S.selectedIndex == 0) {
    S.blur();
  } else {
    var allselected = all_are_selected(S);
    if (S.value == 'toggleall') {
      for (i = 1; i < S.options.length - 1; i++) {
        if (allselected || S.options[i].text[0] != '✓') {
          control_column(S, i);
        }
      }
      S.value = '';
    } else {
      control_column(S, S.selectedIndex);
      S.value = '';
    }
    var toggler = S.options[S.options.length - 1];
    if (all_are_selected(S)) {
      toggler.text = toggler.text.slice(0, 6) + "hide all";
    } else {
      toggler.text = toggler.text.slice(0, 6) + "show all";
    }
  }
};

function control_sort(S) {
  console.log("Starting control");
  var n = S.selectedIndex;
  var t, label = S.options[n].text;
  var spaces = '  '; // the spaces are U+2006 and U+2003, totaling 7/6 em
  var asc = '▲ '; // the space is U+2006, a 1/6 em space
  var dec = '▼ '; // the space is U+2006, a 1/6 em space
  var curdir = label.slice(0, 2);
  label = label.slice(2, label.length);
  for (var i = 0; i < S.length; i++) {
    t = S.options[i].text;
    S.options[i].text = spaces + t.slice(2, t.length);
  }
  if (curdir == asc) {
    S.options[n].text = dec + label;
    $("input[name=sort_dir]").val('op');
  } else {
    S.options[n].text = asc + label;
    $("input[name=sort_dir]").val('');
  }
  $("input[name=sort_order]").val(S.value);
  S.selectedIndex = -1;
};

function update_download_url(link, downid) {
  // console.log("before modification", link.href);
  var newval;
  var url = new URL(link.href);
  var params = url.searchParams;
  var keys = ["showcol", "hidecol", "sort_order", "sort_dir"];
  for (var i = 0; i < keys.length; ++i) {
    newval = $("input[name="+keys[i]+"]").val();
    if (newval.length == 0) {
      params.delete(keys[i]);
    } else {
      params.set(keys[i], newval);
    }
  }
  newval = $("input[name=download_row_count"+downid+"]").val();
  console.log("newval", newval);
  if (newval.length > 0 && newval != "all") {
    params.set("download_row_count", newval);
  }
  newval = $('#downlang-select'+downid).find(":selected").val();
  params.set("Submit", newval);
  url.search = params.toString();
  link.href = url.href;
  console.log(link.href);
  // console.log("after modification", link.href);
  return true;
};

function blur_sort(S) {
  S.size = 0;
  for (var i = 0; i < S.length; i++) {
    t = S.options[i].text;
    if (t.slice(0, 1) != ' ') { // unicode space
      S.selectedIndex = i;
      break;
    }
  }
};

function resetStart()
{
  // resets start if not changing search_type
  $('input[name=start]').val('')
}

function show_row_selector()
{
  $('#row_selector_hidden').hide();
  $('#row_selector_shown').show();
  return false;
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

/* Showing advanced search boxes */


$(document).ready(function () {
  $('#advancedtoggle').click(
    function (evt) {
      evt.preventDefault();
      var advanced = $('.advanced');
      if( advanced.is(":visible") )
      {
        advanced.hide();
        $('#advancedtoggle').text('Advanced search options');
      } else {
        advanced.show();
        $('#advancedtoggle').text('Hide advanced search options');
      }
      return false;
    });
});

function show_advancedQ () {
  var values = $('select.advanced, input.advanced');
  for(var i = 0; i < values.length; i++) {
    if( values[i].value != "" ) {
      $('.advanced').show();
      $('#advancedtoggle').text('Hide advanced search options');
      break;
    }
  }
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
      } else {
        main.css( { "margin-left" : "200px", "transition": "margin 0.2s"} );
        sidebar.show("fast");
        document.cookie = 'showmenu=True;path=/';
        $('#menutoggle').text('Hide Menu');
      }
      return false;
    });
});

function show_moreless(ml) {
  $('.more').hide();
  $('.less').hide();
  $('.'+ml).show();
}

function show_schema(tbl) {
  $("div."+tbl+"-schema-holder").show();
  $("#"+tbl+"-schema-hider").show();
  $("#"+tbl+"-schema-shower").hide();
  return false;
}

function hide_schema(tbl) {
  $("div."+tbl+"-schema-holder").hide();
  $("#"+tbl+"-schema-hider").hide();
  $("#"+tbl+"-schema-shower").show();
  return false;
}


/* add handler for search forms to clean their own
   form data and remove keys for empty (default) values */
$(document).ready(function () {
  document.querySelectorAll("form.search, form.re-search").forEach(
    form => form.addEventListener('formdata',
    function(event) {
      let formData = event.formData;
      let alldeleted = true;
      for (let [name, value] of Array.from(formData.entries())) {
        if (value === '' ||
	    (name === 'count' && value == 50)) {
	  formData.delete(name);
        } else {
          alldeleted = false;
        }
      }
      if (formData.has("hst") && formData.has("search_type") && formData.get("hst") == formData.get("search_type")) {
        formData.delete("hst");
      }
      if (alldeleted) {
        // Need at least one parameter to trigger search results.
        formData.set('search_type', '');
      }
    })
  )
});

/*
  if (!n) {
    var all = document.createElement('input');
    all.type='hidden';
    all.name='all';
    all.value='1';
    myForm.appendChild(all);
  }*/
