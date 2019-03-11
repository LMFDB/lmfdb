/* Event handlers for lmfdb/knowledge/templates/knowl-knowl-history.html */
/* The fakeclick handler is set there */

function clickall(evt) {
  evt.preventDefault();
  $('.history').find('[knowl=cmf]').not('.active').trigger("fakeclick");
  $('.expand_button').switchClass('expand_button', 'hide_button')
  return false;
};
function hideall(evt) {
  evt.preventDefault();
  $('.history').find('.knowl-output*').slideUp("fast");
  $('.history').find('[knowl=cmf]').removeClass('active');
  $('.hide_button').switchClass('hide_button', 'show_button')
  return false;
};
function showall(evt) {
  evt.preventDefault();
  $('.history').find('.knowl-output*').slideDown("fast");
  $('.history').find('[knowl=cmf]').addClass('active');
  $('.show_button').switchClass('show_button', 'hide_button')
  return false;
};

function revert_to_version(evt) {
  evt.preventDefault();
  timestamp = parseInt($(this).attr('ms_timestamp'));
  // edit_history is defined in knowl-edit.html
  if (!unsaved || confirm('Do you really want to revert to this version and overwrite your changes?')) {
    update_content(0, $('#kcontent').val().length, edit_history[timestamp]);
    $kcontent.trigger("keyup");
  }
  return false;
}
