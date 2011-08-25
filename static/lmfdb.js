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
