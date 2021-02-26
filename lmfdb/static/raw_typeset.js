function SelectText(element) {
  var txt = document.getElementById(element);
  var selection = window.getSelection();
  var range = document.createRange();
  range.selectNodeContents(txt);
  selection.removeAllRanges();
  selection.addRange(range);
}

function setraw (elt, iconid, iconpath) {
    $(elt).attr("tset", $(elt).html());
    $(elt).html($(elt).attr("raw"));
    $(elt).attr("israw", "1");
    $(iconid)[0].src=iconpath;
}

function settset (elt, iconid, iconpath) {
    $(elt).html($(elt).attr("tset"));
    $(elt).attr("israw", "0");
    $(iconid)[0].src=iconpath;
}

function setallraw (iconpath) {
  $(".tset-raw").each(function (i,elt) {
    var eltid = $(elt).prop("id");
    var matchinfo = eltid.match(/tset-raw-(\d+)$/);
    var eltidnum = matchinfo[1];
    if ($(elt).attr("israw") == "0") {
      setraw(elt, "#tset-raw-icon-"+eltidnum, iconpath);
  }});
}

function clearallraw (iconpath) {
  $(".tset-raw").each(function (i,elt) {
    var eltid = $(elt).prop("id");
    var matchinfo = eltid.match(/tset-raw-(\d+)$/);
    var eltidnum = matchinfo[1];
    if ($(elt).attr("israw") == "1") {
      settset(elt, "#tset-raw-icon-"+eltidnum, iconpath);
  }});
}

function ondouble (clicknum) {
  var elt = "#tset-raw-"+clicknum;
  var iconid = "#tset-raw-icon-"+clicknum;
  var iconsrc = $(iconid)[0].src;
  var iconRe = /^(.*)(.2.)\.png$/;
  var matcharray = iconsrc.match(iconRe);
  if ($(elt).attr("israw")=="0") {
    setraw(elt, iconid, matcharray[1]+"r2t.png");
  }
  $(elt).focus();
  SelectText("tset-raw-"+clicknum);
}

function iconrawtset(idnum) {
  var elt = "#tset-raw-"+idnum;
  var iconid = "#tset-raw-icon-"+idnum;
  var iconsrc = $(iconid)[0].src;
  var iconRe = /^(.*)(.2.)\.png$/;
  var matcharray = iconsrc.match(iconRe);
  if ($(elt).attr("israw") == "0") {
    setraw(elt, iconid, matcharray[1]+"r2t.png");
  } else {
    settset(elt, iconid, matcharray[1]+"t2r.png");
  }
}

function iconrawtsetall() {
  var iconid = "#tset-raw-icon-all";
  var iconsrc = $(iconid)[0].src;
  var iconRe = /^(.*)(.2.)\.png$/;
  var matcharray = iconsrc.match(iconRe);
  if (matcharray[2] == "t2r") {
    $(iconid)[0].src = matcharray[1]+"r2t.png";
    setallraw(matcharray[1]+"r2t.png");
  } else {
    $(iconid)[0].src = matcharray[1]+"t2r.png";
    clearallraw(matcharray[1]+"t2r.png");
  }
}
