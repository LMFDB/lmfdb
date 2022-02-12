function setraw(elt) {
  var $this = $(elt);
  // the textarea element
  var $tset = $this.children("span.tset-container").first();
  // the "real" rectangle around tset, so we get dimensions as floating points
  var rect = ($tset)[0].getBoundingClientRect();
  var $ta = $this.children("textarea.raw-container").first();
  $ta.width(Math.max(25, rect.width - (2 + 3))); // 2*border + 2*padding
  $ta.height(rect.height - (2 + 3));
  $this.removeClass("tset");
  $this.addClass("raw");
}



function double_rawtset(evt) {
  var $this = $(evt.currentTarget);
  if( $this.hasClass("tset") ) {
    setraw($this);
    $ta = $this.children("textarea.raw-container").first();
    $ta.select();
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

