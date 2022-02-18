
function setraw(elt) {
  var $this = $(elt);
  // typeset container
  var $tset = $this.children("span.tset-container").first();
  var tset_rect = ($tset)[0].getBoundingClientRect();
  var $ta = $this.children("textarea.raw-container").first();
  if ( $this.hasClass("compressed") ) {
    $ta.width(Math.max(25, tset_rect.width - (2 + 3))); // 2*border + 2*padding
    $ta.height(tset_rect.height - (2 + 3));
  } else {
    var properties_rect = $("#properties")[0].getBoundingClientRect();
    // we aim to avoid overlapping properties box
    // we could check for properties_rect.bottom > tset_rect.top
    // but that creates funny behaviour as the current line
    // might have enough space, but not one the parents, e.g. a table
    $ta.css('max-width', properties_rect.left - tset_rect.left - 75);
    $ta.height(0);
    // we need a delay to read the correct scrollHeight
    setTimeout(function() {$ta.height($ta[0].scrollHeight - (2+3));}, 1);
  }

  $this.removeClass("tset");
  $this.addClass("raw");
}



function double_rawtset(evt) {
  console.log("double");
  console.log(evt);
  var $this = $(evt.currentTarget.parentElement);
  if( $this.hasClass("tset") ) {
    console.log("inside");
    setraw($this);
    $ta = $this.children("textarea.raw-container").first();
    $ta.select();
    // we need a delay to set the scrollHeight
    setTimeout(function() {$ta.scrollTop(0);}, 1);
  }
}


function settset(elt) {
  var $this = $(elt);
  $this.removeClass("raw");
  $this.addClass("tset");
}


function toggle(elt) {
  if( $(elt).hasClass("raw") ) {
    settset(elt);
  } else {
    setraw(elt);
  }
}


function iconrawtset(elt) {
  toggle(elt.parentElement);
}

function iconrawtsetall(elt) {
  var $this = $(elt);
  if( $this.hasClass("raw") ) {
    // we remove the class first, so it doesn't show up in the following selector
    $this.removeClass("raw");
    $("span.raw-tset-container.raw").toArray().forEach(settset);
    $this.addClass("tset");
  } else {
    // we remove the class first, so it doesn't show up in the following selector
    $this.removeClass("tset");
    $("span.raw-tset-container.tset").toArray().forEach(setraw);
    $this.addClass("raw");
  }
}


function copyTextOf(elt) {
  var copyText = $(elt);
  navigator.clipboard.writeText(copyText.text());

  copyText.parent().children('.raw-tset-copy-btn').notify("Copied!",
    {className: "success", position:"bottom right" }
);
}

function copyrawcontainer(elt) {
  copyTextOf($(elt).parent().children("textarea.raw-container").first());
}



$(document).ready( function(){
  if ($("span.raw-tset-container").length > 0) {
    $("#rawtseticonspot").html('<span class="tset all raw-tset-container" onclick="iconrawtsetall(this)"><span class="raw-tset-toggle"><img class="tset-icon" alt="Toggle raw display"></span></span>');
    $(".tset-container").dblclick(double_rawtset);
  }
});

