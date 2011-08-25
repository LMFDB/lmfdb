/* this file contains global javascript code for all parts of the lmfdb website
   it's just one file for faster page loading */

/* code for the properties sidepanel on the right */
$(function() {
 $("#properties-header").click(function(evt) {
    evt.preventDefault();
    $("#properties-body").slideToggle("slow");
  });
});

/* providing watermark examples in those forms, that have an 'example=...' attribute */
$(function () {
    $('input[example]').each( function() { $(this).watermark($(this).attr('example')) } )
    $('textarea[example]').each( function() { $(this).watermark($(this).attr('example'), {useNative:false}) } )
});

/* javascript code for the knowledge db features */
// global counter, used to uniquely identify each help-output element
var knowl_id_counter = 0;
 
function knowl_click_handler($el, evnt) {
  evnt.preventDefault();
  
  // the knowl attribute holds the id of the knowl
  var knowl_id = $el.attr("knowl");
  // the uid is necessary if we want to reference the same content several times
  var uid = $el.attr("knowl-uid");
  var output_id = '#knowl-output-' + uid; 
  var $output_id = $(output_id);
 
  // if we already have the content, toggle visibility
  if ($output_id.length > 0) {
    $output_id.slideToggle("fast");

  // otherwise download it
  } else { 
    // create the element for the content, insert it after the one where the 
    // knowl element is included (e.g. inside a <h1> tag) (sibling in DOM)
    $el.parent().after("<div class='knowl-output' id='"+output_id.substring(1)+"'>loading ...</div>");
 
    // "select" where the output is and get a hold of it 
    var $output = $(output_id);
 
    $output.load('/knowledge/render/' + knowl_id, function(response, status, xhr) { 
      if (status == "error") {
        $output.html("<div class='knowl-output error'>ERROR: " + xhr.status + " " + xhr.statusText + '</div>');
      } else if (status == "timeout") {
        $output.html("<div class='knowl-output error'>ERROR: timeout. " + xhr.status + " " + xhr.statusText + '</div>');
      } else {
        $output.hide();
        MathJax.Hub.Queue(['Typeset', MathJax.Hub, output_id.substring(1)]);
        // inside the inserted knowl might be more references: process them, attach the handler!
        $output.find("*[knowl]").each(function() {
           var $knowl = $(this);
           $knowl.attr("knowl-uid", knowl_id_counter);
           knowl_id_counter++;
           $knowl.click(function(evnt) { knowl_click_handler($knowl, evnt) });
        });
      }
      // in any case, reveal the new output after mathjax has finished
      MathJax.Hub.Queue([ function() { $output.slideDown("slow"); }]);
    });
  }
} //~~ end click handler for *[knowl] elements

/** this is the main function */
$(function() {
/** for each one register a click handler that does the 
 *  download/show/hide magic. also register a unique ID to 
 *  avoid wrong behaviour if the same reference is used several times. */
  $("*[knowl]").each(function() { 
    $(this).attr("knowl-uid", knowl_id_counter);
    knowl_id_counter++;
  });
  $("*[knowl]").click(function(evt) {knowl_click_handler($(this), evt)});
});

//~~ end knowl js section
