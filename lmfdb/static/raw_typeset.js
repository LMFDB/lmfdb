function setraw(elt) {
  var $this = $(elt);
  console.log($this);
  $this.attr("tset", $this.html());
  $this.html($this.attr("raw"));
  $this.addClass("raw");
  $this.removeClass("tset");
  $next = $this.next();
  $next.addClass("raw");
  $next.removeClass("tset");
}


function settset(elt) {
  var $this = $(elt);
  $this.html($this.attr("tset"));
  $this.addClass("tset");
  $this.removeClass("raw");
  $next = $this.next();
  $next.addClass("tset");
  $next.removeClass("raw");
}

// safe versions to be used with each in setall*
function setraw_safe(i, elt) {
  if( $(elt).hasClass("tset") ) {
    setraw(elt);
  }
}
function settset_safe(i, elt) {
  if( $(elt).hasClass("raw") ) {
    settset(elt);
  }
}

function toggle(elt) {
  if( $(elt).hasClass("raw") ) {
    settset(elt);
  } else {
    setraw(elt);
  }
}

function setallraw(iconpath) {
  console.log("setallraw");
  $("span.tset-raw").each(setraw_safe);
}

function setalltset(iconpath) {
  console.log("setalltset");
  $("span.tset-raw").each(settset_safe);
}

function ondouble(elt) {
  setraw(elt);
}

function iconrawtset(elt) {
  toggle(elt.parentElement.children[0]);
}

function iconrawtsetall(elt) {
  var $this = $(elt);
  if( $this.hasClass("raw") ) {
    setalltset();
    $this.removeClass("raw");
    $this.addClass("tset");
  } else {
    setallraw();
    $this.removeClass("tset");
    $this.addClass("raw");
  }
}


function copyTextOf(elt) {
  var copyText = $(elt);
  navigator.clipboard.writeText(copyText.text());
  copyText.notify("Copied!",
    {className: "success", position:"bottom right" }
);
}

function copyuncle(elt) {
  copyTextOf(elt.parentElement.parentElement.children[0]);
}


