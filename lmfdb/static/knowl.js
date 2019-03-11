/* These functions are used for viewing and editing knowls.  Note that the functions for showing knowls on normal lmfdb pages are still in lmfdb.js */

/* We need various global variables set and html elements present to function

Global variables:
  - edit_history -- should be a dictionary with keys ms_timestamps
                    and value the knowl content at that timestamp.
  - all_defines -- should be a dictionary with keys terms defined in other knowls,
                   and value a list of knowl ids defining that term.

HTML elements:
  - #ktitle -- an input for the knowl title
  - #kcontent -- a textarea for editing the knowl content
  - #knowl-title -- a div for holding the knowl title in preview mode
  - #knowl-content -- a div for holding the knowl content in preview mode
  - #refresh-view -- a link allowing the user to explicitly refresh the mode
  - #link-suggestions-ul -- an unordered list containing the link suggestions

var $ktitle    = $("#ktitle");
var $kcontent  = $("#kcontent");
var $title     = $("#knowl-title");
var $content   = $("#knowl-content");
var $refresh   = $("#refresh-view");
var $linkul    = $("#link-suggestions-ul");
var $diffview  = $("#diff-container");
var $slider    = $("#history-slider");
*/

/* parameters */
var all_modes = ['link-suggestions', 'history', 'diffs', 'preview'];
var REFRESH_TIMEOUT = 2000;
/* state flags */
var refresh_id    = null;
var reparse_latex = false;
var unsaved = false;

function normalize_define(s) {
  // Removes quotes and extra spaces.  Should match normalize_define in know.py
  return s.replace(/\s+/g, ' ').replace('"', '').replace("'", "").toLowerCase();
}

function knowl_link(kid, label, title=null) {
  if (title === null) {
    title = label + ' [' + kid + ']';
  }
  return '<a title="'+title+'" knowl="'kid+'" kwargs="">'+label+'</a>';
}

function refresh_view(edit_mode='cur') {
  if (refresh_id) {
    /* this case happens, when we click "refresh" while a timer is running. */
    window.clearTimeout(refresh_id);
  }
  if (edit_mode === 'cur') {
    for (var i = 0; i < all_modes.length; i++) {
      mode = all_modes[i];
      if ($('#activate-' + mode).is(":hidden")) {
        edit_mode = mode;
        break;
      }
    }
  }
  if (edit_mode === 'link-suggestions') {
    refresh_link_suggestions();
  } else if (edit_mode === 'history') {
    refresh_history();
  } else if (edit_mode === 'diffs') {
    refresh_diffs();
  } else {
    refresh_preview();
  }
  $('#refresh-view').hide();
}


/* Switching between edit modes */
function enable(edit_mode) {
  refresh_view(edit_mode);
  for (var i = 0; i < all_modes.length; i++) {
    mode = all_modes[i];
    if (mode === edit_mode) {
      $('#activate-' + mode).hide();
      $('#inactive-' + mode).show();
      $('#view-' + mode).show();
    } else {
      $('#activate-' + mode).show();
      $('#inactive-' + mode).hide();
      $('#view-' + mode).hide();
    }
  }
}

function refresh_link_suggestions() {
  var knowldef = /\{\{\s*KNOWL(_INC)?\s*\(\s*['"]([^'"]+)['"]\s*,\s*(title\s*=\s*)?([']([^']+)[']|["]([^"]+)["]\s*)\)\s*\}\}/g;
  var wedef = /\*\*([^\*]+)\*\*/g;
  var $kcontent = $("#kcontent");
  var $linkul    = $("#link-suggestions-ul");
  var text_present = {};
  var kid_present = {};
  var we_define = {};
  var content = $kcontent.val();
  do {
    m = wedef.exec(content);
    if (m) {
      we_define[normalize_define(m[1])] = true;
    }
  } while (m);
  log(we_define);
  do {
    m = knowldef.exec(content);
    if (m) {
      var thisdef = null;
      if (m[5]) {
        thisdef = normalize_define(m[5]);
      } else if (m[6]) {
        thisdef = normalize_define(m[6]);
      }
      text_present[thisdef] = true;
      kid_present[m[2]] = true;
    }
  } while (m);
  $linkul.empty();
  var some_link = false;
  var to_insert = [];
  for (kdef in all_defines) {
    var kdef_finder = new RegExp('\\b'+kdef+'\\b', 'i');
    var match = kdef_finder.exec(content);
    if (match !== null) {
      if (normalize_define(kdef) in we_define) {
        continue;
      }
      found = false;
      for (pdef in text_present) {
        if (pdef.indexOf(kdef) != -1) {
          found = true;
          break;
        }
      }
      if (!found) {
        some_link = true;
        // Have to construct the Knowl link by hand
        for (var i = 0; i < all_defines[kdef].length; i++) {
          var definer_id = all_defines[kdef][i];
          if (!(definer_id in kid_present)) {
            var label = match[0]+' ['+definer_id+']';
            var klink = knowl_link(definer_id, label, label);
            var inserter = `<a href="#" class="insert_klink" definer_id=`+definer_id+` match=`+match[0]+`>insert</a>`;
            to_insert.push([match.index, "<li>" + klink + " - " + inserter + "</li>"]);
          }
        }
      }
    }
  }
  function sort_pairs(a, b) {
    if (a[0] != b[0]) {
      return a[0]-b[0];
    } else if (a[1] < b[1]) {
      return -1;
    } else if (a[1] > b[1]) {
      return 1;
    } else {
      return 0;
    }
  }
  to_insert.sort(sort_pairs);
  for (var i = 0; i < to_insert.length; i++) {
    var $new_item = $(to_insert[i][1]);
    $linkul.append($new_item);
  }
  if (!some_link) {
    $linkul.append("<li>No suggestions available</li>");
  }
  // Now find the terms that are already knowled
  // And the terms that aren't but could be
}

function insert_klink(evt) {
  var $kcontent = $("#kcontent");
  evt.preventDefault();
  var kid = $(this).attr("definer_id");
  var ktext = $(this).attr("match");
  var content = $kcontent.val();
  var ktext_finder = new RegExp('\\b'+ktext+'\\b', 'i');
  var match = ktext_finder.exec(content);
  if (match !== null) {
    start = match.index;
    end = start + match[0].length;
    var new_link = knowl_link(kid, match[0]);
    update_content(start, end, new_link);
  }
  refresh_link_suggestions();
  $kcontent.keyup();
}

function update_content(start, end, new_text) {
  var $kcontent = $("#kcontent");
  // Update the content area, replacing the selection from start to end with new_text.
  var isFirefox = typeof InstallTrigger !== 'undefined';
  if (isFirefox) {
    // the insertText method doesn't work on Firefox, so we have to just replace the val, losing undo capability
    // See https://bugzilla.mozilla.org/show_bug.cgi?id=1220696
    var new_content = content.substring(0, start) + new_text + content.substring(end);
    $kcontent.val(new_content);
  } else {
    $kcontent.focus();
    $kcontent[0].selectionStart = start;
    $kcontent[0].selectionEnd = end;
    document.execCommand('insertText', false, new_text);
  }
}

function refresh_preview() {
  var url = "{{ url_for('.render', ID=k.id)}}";
  var $title = $("#knowl-title");
  var $kcontent = $("#kcontent");
  var $content = $("#knowl-content");
  var $refresh = $("#refresh-view");
  $.post(url, { "content" : $kcontent.val(), "footer" : "0" },
    function(data) {
      $title.html("Processing ...");
      $content.html(data);
      renderMathInElement($title.get(0), katexOpts); // FIXME this doesn't do what is intended as the contents of title is currently "Processing ..."
      renderMathInElement($content.get(0), katexOpts);
      refresh_id = null;
      // once rendering is done.
      // has there been a call in the meantime and we have to do this again?
      if (reparse_latex) {
        /* console.log("reparse_latex == true"); */
        reparse_latex = false;
        refresh_view();
      }
      /* finally, set the title and hide the refresh link */
      $title.html($("#ktitle").val());
      $refresh.fadeOut();
    }).fail(function() { $title.html("ERROR"); })
}

function refresh_history() {
}
function refresh_diffs() {
  $('#compare').trigger('resize');
}

/* if nothing scheduled, refresh delayed
   otherwise tell it to reparse the latex */
function refresh_delay() {
  unsaved = true;
  $("#refresh-view").fadeIn();
  if (refresh_id) {
    reparse_latex = true;
  } else {
    refresh_id = window.setTimeout(refresh_view, REFRESH_TIMEOUT);
  }
}

/* Check before saving if changing knowl category */
function check_knowl_category() {
  var newname = $("input[name='krename']").val();

  if (newname) {
    if (newname.includes(".")) {
      var newcat = newname.split(".").slice(0,-1).join(".");
    } else {
      var newcat = newname;
    }
    if ('{{k.id}}'.includes(".")) {
      var oldcat = '{{k.id}}'.split(".").slice(0, -1).join(".");
    } else {
      var oldcat = oldname;
    }
    if (newcat != oldcat) {
      if (confirm("Do you really want to change the knowl category from " + oldcat + " to " + newcat)) {
        unsaved = false;
        return true;
      } else {
        return false;
      }
    }
  }
  return set_saved();
}

function set_saved() {
  unsaved = false;
  return true;
}
