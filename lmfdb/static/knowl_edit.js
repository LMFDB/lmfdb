/* These functions are used for editing knowls.  Note that the functions for showing knowls on normal lmfdb pages are still in lmfdb.js */

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
  return '<a title="'+title+'" knowl="'+kid+'" kwargs="">'+label+'</a>';
}

/* Switching between edit modes */
function enable(edit_mode) {
  view_refresh(edit_mode);
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
  // text_present is a set of knowl labels already present in the content
  var text_present = {};
  // kid_present is a set of knowl ids already present in the content
  var kid_present = {};
  // we_define is a set of the definitions in the content (wrapped in **   **)
  var we_define = {};
  // bad_intervals is a list of intervals that should be excluded from suggestions: KNOWLS and mathmode
  var bad_intervals = [];
  var content = $kcontent.val();
  do {
    m = wedef.exec(content);
    if (m) {
      we_define[normalize_define(m[1])] = true;
    }
  } while (m);
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
      bad_intervals.push([m.index, m.index+m[0].length]);
    }
  } while (m);
  // Add mathmode intervals to bad_intervals
  var math_res = [/[^\$]\$.+?\$/g, // We assume people aren't using \$ in their mathmode expressions
                  /\$\$.+?\$\$/g,
                  /\\\(.*?\\\)/g,
                  /\\\[.*?\\\]/g];
  var re_offset = [1, 0, 0, 0];
  // We don't want to include the first character of the first regex in the bad interval.
  // We could do this with a negative lookbehind, but that's not supported on Firefox.
  for (i = 0; i < math_res.length; i++) {
    do {
      m = math_res[i].exec(content);
      if (m) {
        // We need to add one to the index in order to ignore the starting character
        // which was necessary to include in order to make the first regex work
        bad_intervals.push([m.index + re_offset[i], m.index+m[0].length]);
      }
    } while (m);
  }
  // Sort bad_intervals and deal with overlaps (true overlaps shouldn't occur, but nesting might)
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
  bad_intervals.sort(sort_pairs);
  i = 0;
  while (i < bad_intervals.length-1) {
    cur = bad_intervals[i];
    next = bad_intervals[i+1];
    if (cur[1] >= next[0]) {
      if (cur[1] < next[1]) {
        cur[1] = next[1];
      }
      bad_intervals.splice(i+1, 1); // remove next
    } else {
      i++;
    }
  }
  function is_bad(pos, dir=0, i0=0, i1=bad_intervals.length) {
    // If dir=0, return a boolean value: whether pos is in a bad interval
    // If dir is 1 or -1, return the closest non-bad position in that direction.
    // We can just use pos as the start of the string, because kdef_finder is delimited at word boundaries
    if (bad_intervals.length == 0) {
      if (dir == 0) {
        return false;
      } else {
        return pos;
      }
    }
    if (i1 <= i0+1) {
      var spot_is_bad = (bad_intervals[i0][0] <= pos) && (pos < bad_intervals[i0][1]);
      if (dir == 0) {
        return spot_is_bad;
      } else if (!spot_is_bad) {
        return pos;
      } else if (dir == 1) {
        return bad_intervals[i0][1];
      } else {
        return bad_intervals[i0][0];
      }
    }
    mid = Math.floor((i0+i1)/2);
    if (pos < bad_intervals[mid][0]) {
      return is_bad(pos, dir, i0, mid);
    } else {
      return is_bad(pos, dir, mid, i1);
    }
  }
  $linkul.empty();
  var some_link = false;
  var to_insert = [];
  for (kdef in all_defines) {
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
    if (found) {
      continue;
    }
    var kdef_finder = new RegExp('\\b'+kdef+'\\b', 'ig');
    do {
      var match = kdef_finder.exec(content);
      if (match !== null && !is_bad(match.index)) {
        some_link = true;
        // Have to construct the Knowl link by hand
        for (var i = 0; i < all_defines[kdef].length; i++) {
          var definer_id = all_defines[kdef][i];
          if (!(definer_id in kid_present)) {
            var match_end = match.index + match[0].length;
            var label = match[0];
            var klink = knowl_link(definer_id, label);
            // Add five words of context on each side, stopping at newlines
            var pre_mark = match.index
            for (var j = 0; j < 5; j++) {
              pre_mark = content.lastIndexOf(" ", pre_mark-1);
              if (pre_mark == -1) {
                pre_mark = 0;
                break;
              }
            }
            var nl_mark = content.lastIndexOf("\n", match.index);
            pre_mark = Math.max(pre_mark, nl_mark);
            pre_mark = is_bad(pre_mark, -1); // Don't stop in the middle of mathmode/KNOWL
            var post_mark = match_end;
            for (var j = 0; j < 5; j++) {
              post_mark = content.indexOf(" ", post_mark+1);
              if (post_mark == -1) {
                post_mark = content.length;
                break;
              }
            }
            var nl_mark = content.indexOf("\n", match_end);
            post_mark = Math.min(post_mark, nl_mark);
            post_mark = is_bad(post_mark, 1); // Don't stop in the middle of mathmode/KNOWL
            var select_link = `<a href="#" class="select_klink" start=`+match.index+` end=`+match_end+`>Select</a>`;
            var inserter = `<a href="#" class="insert_klink" definer_id="`+definer_id+`" start=`+match.index+` end=`+match_end+` match="`+match[0]+`">insert `+definer_id+`</a>`;
            to_insert.push([match.index, "<li>" + inserter + " &bull; " + content.substring(pre_mark, match.index) + klink + content.substring(match_end, post_mark) + " &bull; " + select_link + "</li>"]);
          }
        }
        break;
      }
    } while (match !== null);
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
  evt.preventDefault();
  var $kcontent = $("#kcontent");
  var kid = $(this).attr("definer_id");
  var ktext = $(this).attr("match");
  var start = $(this).attr("start");
  var end = $(this).attr("end");
  // This knowl link is showing up in the content, so we can use jinja. :-)
  var new_link = "{{KNOWL('"+kid+"', '"+ktext+"')}}"
  update_content(start, end, new_link);
  $kcontent.keyup();
}

function select_klink(evt) {
  evt.preventDefault();
  var $kcontent = $("#kcontent");
  var start = $(this).attr("start");
  var end = $(this).attr("end");
  // There's no good way to scroll a textarea to
  var content = $kcontent.val();
  var pretext = content.substr(0, start);
  $kcontent.blur();
  $kcontent.val(pretext);
  $kcontent.focus();
  $kcontent.val(content);
  $kcontent[0].selectionStart = start;
  $kcontent[0].selectionEnd = end;
}

function update_content(start, end, new_text) {
  var $kcontent = $("#kcontent");
  // Update the content area, replacing the selection from start to end with new_text.
  var isFirefox = typeof InstallTrigger !== 'undefined';
  if (isFirefox) {
    // the insertText method doesn't work on Firefox, so we have to just replace the val, losing undo capability
    // See https://bugzilla.mozilla.org/show_bug.cgi?id=1220696
    var content = $kcontent.val();
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
  var $title = $("#knowl-title");
  var $kcontent = $("#kcontent");
  var $content = $("#knowl-content");
  var $refresh = $("#refresh-view");
  $.post(render_url, { "content" : $kcontent.val(), "footer" : "0" },
    function(data) {
      $title.html("Processing ...");
      $content.html(data);
      renderMathInElement($content.get(0), katexOpts);
      refresh_id = null;
      // once rendering is done.
      // has there been a call in the meantime and we have to do this again?
      if (reparse_latex) {
        /* console.log("reparse_latex == true"); */
        reparse_latex = false;
        view_refresh();
      }
      /* finally, set the title and hide the refresh link */
      $title.html($("#ktitle").val());
      renderMathInElement($title.get(0), katexOpts); // render any math in the title
      $refresh.fadeOut();
    }).fail(function() { $title.html("ERROR"); })
}

function refresh_history() {
}
function refresh_diffs() {
  content_change();
  //$('#compare').trigger('resize');
}

function find_current_edit_mode() {
  for (var i = 0; i < all_modes.length; i++) {
    mode = all_modes[i];
    if ($('#activate-' + mode).is(":hidden")) {
      return mode;
    }
  }
}


function dispatch_refresh() {
  // Some edit modes want a timer, others don't.  This is the function that's called by the keyup event on content.
  edit_mode = find_current_edit_mode();
  if (edit_mode == 'preview') {
    delay_refresh();
  } else {
    view_refresh(edit_mode);
  }
}

/* if nothing scheduled, refresh delayed
   otherwise tell it to reparse the latex */
function delay_refresh() {
  unsaved = true;
  $("#refresh-view").fadeIn();
  if (refresh_id) {
    reparse_latex = true;
  } else {
    refresh_id = window.setTimeout(view_refresh, REFRESH_TIMEOUT);
  }
}

function view_refresh(edit_mode='cur') {
  if (refresh_id) {
    /* this case happens, when we click "refresh" while a timer is running. */
    window.clearTimeout(refresh_id);
  }
  if (edit_mode === 'cur') {
    edit_mode = find_current_edit_mode();
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

/* Check before saving if changing knowl category */
function check_knowl_category() {
  var curname = $("input[name='id']").val();
  var newname = $("input[name='krename']").val();

  if (newname) {
    if (newname.includes(".")) {
      var newcat = newname.split(".").slice(0,-1).join(".");
    } else {
      var newcat = newname;
    }
    if (curname.includes(".")) {
      var oldcat = curname.split(".").slice(0, -1).join(".");
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
