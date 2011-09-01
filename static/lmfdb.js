/* this file contains global javascript code for all parts of the lmfdb website
   it's just one file for faster page loading */

/* global logger */
function log(msg) {
  if(window.console != undefined) { console.log(msg); }
}

function error(msg) {
  if(window.console != undefined) { console.error(msg); }
}

/* only show main content after processing all the latex */
$(function() {
  if ($("body").hasClass("knowl") || $("body").hasClass("users")) return;
  var revealed = false;
  function show_content() {
    revealed = true;
    $("#content").css("opacity", "1").show();
    $("#mathjax-info").hide();
  }
  MathJax.Hub.Queue(function() {show_content()}); 
  $("#mathjax-info").click(function() {show_content()});

  window.setTimeout(function() {
    if(!revealed) {
      $("#mathjax-info").show();
      $("#content").hide();
    }
  }, 100);

  /* delay some secs and tell the user, that it is
   * still loading and clicking removes the banner */
  window.setTimeout(function() {
    /* still waiting? */
    if(revealed) return;
    if($("#content").css("display") == "none") {
      $("#content").css("opacity", "0.2").show();
      $("#mathjax-log").html("<strong>Still loading, click here to show it.</strong>");
    }
  }, 5000);

  /* 
  var $mjlog = $("#mathjax-log");
  MathJax.Hub.Register.MessageHook("New Math",function (msg) {
    var script = MathJax.Hub.getJaxFor(message[1]).SourceElement();
    var txt = msg.join(" ")+": '"+script.text+"'";
    $mjlog.html(txt);
  });
  */
}); 

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
  var $pb = $("#properties-body");
  var $pc = $("#properties-collapser");
  var $ph = $("#properties-header");
  var pb_h = $pb.height();
  $pb.animate({"height": "toggle", "opacity" : "toggle"}, 
    { 
      duration: 100 + 100 * Math.log($pb.height()),
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
 $("#properties-header,#properties-collapser").click(function(evt) { properties_collapser(evt); });
 /* providing watermark examples in those forms, that have an 'example=...' attribute */
 $('input[example]').each(function(a,b) { $(b).watermark($(b).attr('example')  ) } )
 $('textarea[example]').each(function(a,b) { $(b).watermark($(b).attr('example'), {useNative:false}  ) } )
});

/* javascript code for the knowledge db features */
/* global counter, used to uniquely identify each help-output element
 * that's necessary because the same knowl could be referenced several times
 * on the same page */
var knowl_id_counter = 0;
/* site wide cache, TODO html5 local storage to cover whole domain
 * /w a freshness timeout of about 10 minutes */
var knowl_cache = {};
 
function knowl_click_handler($el) {
  // the knowl attribute holds the id of the knowl
  var knowl_id = $el.attr("knowl");
  // the uid is necessary if we want to reference the same content several times
  var uid = $el.attr("knowl-uid");
  var output_id = '#knowl-output-' + uid; 
  var $output_id = $(output_id);
 
  // if we already have the content, toggle visibility
  if ($output_id.length > 0) {
    $output_id.slideToggle("fast");
    $el.toggleClass("active");

  // otherwise download it or get it from the cache
  } else { 
    $el.addClass("active");
    // create the element for the content, insert it after the one where the 
    // knowl element is included (e.g. inside a <h1> tag) (sibling in DOM)
     var idtag = "id='"+output_id.substring(1) + "'";
    $el.parent().after("<div class='knowl-output'" +idtag+ ">loading '"+knowl_id+"' …</div>");
 
    // "select" where the output is and get a hold of it 
    var $output = $(output_id);

    // cached?
    if(knowl_id in knowl_cache) {
      log("cache hit: " + knowl_id);
      $output.hide();
      $output.html(knowl_cache[knowl_id]);
      MathJax.Hub.Queue(['Typeset', MathJax.Hub, $output.get(0)]);
      MathJax.Hub.Queue([ function() { $output.slideDown("slow"); }]);

    } else {
      $output.addClass("loading");
      $output.show();
      log("downloading knowl: " + knowl_id);
      $output.load('/knowledge/render/' + knowl_id, function(response, status, xhr) { 
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
        }
        // in any case, reveal the new output after mathjax has finished
        MathJax.Hub.Queue(['Typeset', MathJax.Hub, $output.get(0)]);
        MathJax.Hub.Queue([ function() { $output.slideDown("slow"); }]);
      });
    } /* ~~ end not cached */
  }
} //~~ end click handler for *[knowl] elements

/** register a click handler for each element with the knowl attribute 
 * @see jquery's doc about 'live'! the handler function does the 
 *  download/show/hide magic. also add a unique ID, 
 *  necessary when the same reference is used several times. */
$(function() {
  $("*[knowl]").live({
    click: function(evt) {
      evt.preventDefault();
      var $knowl = $(this);
      if(!$knowl.attr("knowl-uid")) {
        log("knowl-uid = " + knowl_id_counter);
        $knowl.attr("knowl-uid", knowl_id_counter);
        knowl_id_counter++;
      }
      knowl_click_handler($knowl, evt);
    }
  });
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
