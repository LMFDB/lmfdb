/* Event handlers for lmfdb/knowledge/templates/knowl-knowl-history.html */
/* The fakeclick handler is set there */
function escapeSelector(s){
    return s.replace( /(:|\.|\[|\])/g, "\\$1" );
}
function escapeId(s){
    return s.replace( /(:|\.|\[|\])/g, "\\\\$1" );
}
function showall(evt) {
  evt.preventDefault();
  var kid = $(this).attr('kid');
  $('.history').find('a[knowl='+escapeSelector(kid)+']').not('.active').trigger("fakeclick");
  $('.show_button').switchClass('show_button', 'hide_button')
  return false;
};
function hideall(evt) {
  evt.preventDefault();
  var kid = $(this).attr('kid');
  $('.history').find('a.active[knowl='+escapeSelector(kid)+']').trigger("fakeclick");
  $('.hide_button').switchClass('hide_button', 'show_button')
  return false;
};

function revert_to_version(evt) {
  evt.preventDefault();
  timestamp = parseInt($(this).attr('ms_timestamp'));
  // edit_history is defined in knowl-edit.html
  if (!unsaved || confirm('Do you really want to revert to this version and overwrite your changes?')) {
    update_content(0, $('#kcontent').val().length, edit_history[timestamp]);
    $('#kcontent').trigger("keyup");
  }
  return false;
}

$(document).ready(function () {
  $("body").on("fakeclick", "[knowl]", knowl_handle);
  $("body").on("click", ".hide_button", hideall);
  $("body").on("click", ".show_button", showall);
  $("body").on("click", ".revert_button", revert_to_version);
});
