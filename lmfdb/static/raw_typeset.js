function SelectText(element) {
  var txt = document.getElementById(element);
  var selection = window.getSelection();
  var range = document.createRange();
  range.selectNodeContents(txt);
  selection.removeAllRanges();
  selection.addRange(range);
}

function setallraw (iconpath) {
  $(".tset-raw").each(function (i,elt) {
    var eltid = $(elt).prop("id");
    var matchinfo = eltid.match(/tset-raw-(\d+)$/);
    var eltidnum = matchinfo[1];
    if ($(elt).attr("israw") == "0") {
      $(elt).attr("tset", $(elt).html());
      $(elt).html($(elt).attr("raw"));
      $(elt).attr("israw", "1");
      $("#tset-raw-icon-"+eltidnum)[0].src=iconpath;
  }});
}

function clearallraw (iconpath) {
  $(".tset-raw").each(function (i,elt) {
    var eltid = $(elt).prop("id");
    var matchinfo = eltid.match(/tset-raw-(\d+)$/);
    var eltidnum = matchinfo[1];
    if ($(elt).attr("israw") == "1") {
      $(elt).html($(elt).attr("tset"));
      $(elt).attr("israw", "0");
      $("#tset-raw-icon-"+eltidnum)[0].src=iconpath;
  }});
}

function rawtset (clickidorig) {
  var clickid = "#"+clickidorig;
  if ($(clickid).attr("israw")=="0") {
    clearallraw("foo");
    $(clickid).attr("israw","1");
    $(clickid).attr("tset", $(clickid).html());
    $(clickid).html($(clickid).attr("raw"));
    $(clickid).focus();
    SelectText(clickidorig);
  } else {
    $(clickid).attr("israw","0");
    $(clickid).html($(clickid).attr("tset")); 
  }
}

function iconrawtset(idnum) {
  var spanid = "tset-raw-"+idnum;
  var iconid = "tset-raw-icon-"+idnum;
  var iconsrc = $("#"+iconid)[0].src;
  var iconRe = /^(.*)(.2.)\.png$/;
  var matcharray = iconsrc.match(iconRe);
  if ($("#"+spanid).attr("israw") == "0") {
    $("#"+iconid)[0].src = matcharray[1]+"r2t.png"
    $("#"+spanid).attr("tset", $("#"+spanid).html());
    $("#"+spanid).attr("israw", "1");
    $("#"+spanid).html($("#"+spanid).attr("raw"));
  } else {
    $("#"+iconid)[0].src = matcharray[1]+"t2r.png"
    $("#"+spanid).html($("#"+spanid).attr("tset"));
    $("#"+spanid).attr("israw", "0");
  }
}

function iconrawtsetall() {
  var iconid = "tset-raw-icon-all";
  var iconsrc = $("#"+iconid)[0].src;
  var iconRe = /^(.*)(.2.)\.png$/;
  var matcharray = iconsrc.match(iconRe);
  if (matcharray[2] == "t2r") {
    $("#"+iconid)[0].src = matcharray[1]+"r2t.png";
    setallraw(matcharray[1]+"r2t.png");
  } else {
    $("#"+iconid)[0].src = matcharray[1]+"t2r.png";
    clearallraw(matcharray[1]+"t2r.png");
  }
}
