/* Event handlers for lmfdb/knowledge/templates/knowl-review-recent.html

The code there should set up two global dictionaries: content and reviewed_content.
*/

function click_diff(evt) {
  evt.preventDefault();
  var kid = evt.target.getAttribute("kid");
  var type = evt.target.getAttribute("type");
  if (type == "sidebyside") {
    var othertype = "inline";
  } else {
    var othertype = "sidebyside";
  }
  var output_id = '#' + type + "[kid=" + kid + "]";
  var output = $(output_id);
  var otheroutput = $('#' + othertype + "[kid=" + kid + "]");
  if (otheroutput.length > 0) {
    otheroutput.parent().parent().hide("fast");
  }
  if (output.length == 0) {
    var scroll = $('html').scrollTop();
    var pp = $("." + type + "[kid=" + kid + "]");
    var comp = $("<div></div>").attr("id", type).attr("kid",kid);
    pp.append(($("<div></div>").attr("class", "diff_wrapper")).append(comp));
    lhs = reviewed_content[kid];
    rhs = content[kid];
    if (type == "sidebyside") {
      comp.mergely({
        license: 'gpl-separate-notice',
        cmsettings: {
          readOnly: true,
          linewrap: true,
          viewportMargin: 50,
        },
        lineNumbers: true,
        wrap_lines: true,
        width: 'auto',
        height: '100%',
        ignorews: false,
        lhs: function(setValue) { setValue(lhs); },
        rhs: function(setValue) { setValue(rhs); },
      });
      comp.trigger('resize');
      // there is a timeout somewhere of 150..
      setTimeout( function() { $('html').scrollTop(scroll);}, 151);
    } else {
      comp.html('<pre>' + diff(lhs, rhs) + '</pre>');
    }
    output = $(output_id);
  }
  output.parent().parent().slideToggle("fast");
  return false;
}
