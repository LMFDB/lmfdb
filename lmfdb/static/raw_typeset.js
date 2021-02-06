  function SelectText(element) {
    var txt = document.getElementById(element);
    var selection = window.getSelection();
    var range = document.createRange();
    range.selectNodeContents(txt);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  function clearallraw () {
    $(".tset-raw").each(function (i,elt) {
    if ($(elt).attr("israw") == "1") {
      $(elt).html($(elt).attr("tset"));
      $(elt).attr("israw", "0");
    }});
}

  function rawtset (clickidorig) {
    clickid = "#"+clickidorig;
    if ($(clickid).attr("israw")=="0") {
      clearallraw();
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
