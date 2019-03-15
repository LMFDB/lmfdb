/* Event handlers for knowl diffs */

var diffmode='sidebyside';

var mergely_settings = {
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
}

function new_text(timestamp) {
  if( timestamp == -1) {
    return $('#kcontent').val();
  }
  else if ( timestamp >= 0 ) {
    return edit_history[timestamp];
  }
  else {
    return '';
  }
};

function inline_handler(evt) {
  evt.preventDefault();
  diffmode = 'inline';
  $('#lhsselect').trigger("change");
  $(".sidebyside").hide('fast');
  $(".inline").show('fast');
  return false;
}

function sidebyside_handler(evt) {
  evt.preventDefault();
  diffmode = 'sidebyside';
  $('#lhsselect').trigger("change");
  $('#rhsselect').trigger("change");
  $('#compare').trigger('resize');
  $(".inline").hide('fast');
  $(".sidebyside").show('fast');
  return false;
}

function lhs_change() {
  var lhs = new_text(parseInt($('#lhsselect').val()));
  if (diffmode == 'sidebyside') {
    var scroll = $('html').scrollTop();
    $('#compare').mergely('lhs', lhs);
    $('#compare').mergely('resize');
    // there is a timeout somewhere of 150..
    setTimeout( function() { $('html').scrollTop(scroll);}, 151);
  } else {
    var rhs = new_text(parseInt($('#rhsselect').val()));
    $('#compareinline').html('<pre>' + diff(lhs, rhs) + '</pre>');
  }
  return false;
}

function rhs_change() {
  var rhs = new_text(parseInt($('#rhsselect').val()));
  if (diffmode == 'sidebyside') {
    var scroll = $('html').scrollTop();
    $('#compare').mergely('rhs', rhs);
    $('#compare').trigger('resize');
    // there is a timeout somewhere of 150..
    setTimeout( function() { $('html').scrollTop(scroll);}, 151);
  } else {
    var lhs = new_text(parseInt($('#lhsselect').val()));
    $('#compareinline').html('<pre>' + diff(lhs, rhs) + '</pre>');
  }
  return false;
}

function add_editing_to_selects(ms_timestamp) {
  $('#lhsselect').prepend($("<option></option>")
                     .attr("value","-1")
                     .text("editing")
                     .prop('selected', true)
                    );
  if(Object.keys(edit_history).length > 0) {
    $('#lhsselect').val(ms_timestamp).change();
  }
  $('#rhsselect').prepend($("<option></option>")
                     .attr("value","-1")
                     .text("editing")
                     .prop('selected', true)
                    );

  content_change();
}

function content_change() {
  $('#lhsselect').trigger("change");
  $('#rhsselect').trigger("change");
  return false;
}
