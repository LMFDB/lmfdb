/*jshint esversion: 6 */
/* globals blockList */

var myStore = localStorage;
var storeExpiry = 172800; //Expiry time in seconds
var tagString = '<conflict>';
var tagStringClose = '</conflict>';

//---------- Editor update and viewer ----------------------------

function updateBlock(obj){
    //Handle updates to block text etc
    var block = mainBlockList.getBlock("#"+obj.id);
    block.newtext = obj.value;
    if(block.newtext != block.text){
      block.edited = true;
    }else{
      block.edited = false;
    }
    fitToText(block.docElementId);
}

function resetEdits(blockid=null){
  //Reset input fields to orginal values
  //Changes blocklist and DOM fields
  //If block is provided, only that id is reset, otherwise all are
  var block;
  if(blockid){
    var blockIds = mainBlockList.getBlockIdsFromPartialID(blockid);
    for(var id of blockIds){
      block = mainBlockList.getBlock(id);
      block.newtext = block.text;
      block.edited = false;
      $(escape_jq(block.docElementId)).val(block.newtext);
      fitToText(block.docElementId);
    }

  }else{
    //Clean up everything and remove any stored list
      for( var key in mainBlockList.blockList){
        block = mainBlockList.blockList[key];
        block.newtext = block.text;
        block.edited = false;
        fitToText(block.docElementId);
      }
      console.log("Removing "+'list'+pageKey);
      myStore.removeItem('list'+pageKey);
  }
}

function fillFromDrop(selector, box){
  //Fill box with selected item
  console.log("Got selector");
  box.value = selector.options[selector.selectedIndex].value;
  updateBlock(box);
  //Dismiss selector. parent is a div created by toggle
  var parent = selector.parentNode;
  parent.remove();
}


//---------- End editor update and viewer ------------------------

//---------- Editor local storage handing ------------------------

function storeBlockList(){
  //Convert blocklist to JSON and set in local storage
  if(mainBlockList.blockList){
    var date = new Date();
    var listAsJson = JSON.stringify([date, mainBlockList.blockList]);
    myStore.setItem('list'+pageKey, listAsJson);
  }
}

function retrieveBlockList(){
  //Retrieve blocklist from local storage and recreate
  //Several possibilities should be caught:
    //Nothing has been edited, so nothing to restore
    //The changes are "old", i.e. more than storeExpiry seconds old in which case we discard them
    //The served data has changed:
        //if the new served data matches the changes it's not an edit
        //otherwise we show a conflict
    //Otherwise we just copy the edited and newtext states

  var listAsJson = myStore.getItem('list'+pageKey);

  if (listAsJson && mainBlockList){
    var parsedData = JSON.parse(listAsJson);
    var anyEdits = false;
    for (var block in parsedData[1]){
      if(parsedData[1][block].edited){
        anyEdits = true;
        break;
      }
    }
    if(!anyEdits) return;
    var timeDiff = (new Date().getTime() - new Date(parsedData[0]).getTime())/1000; //Time since store in s
    if (timeDiff > storeExpiry ){
        console.log("Changes are more than "+storeExpiry+" seconds old. Removing.");
        myStore.removeItem('list'+pageKey);
        resetEdits(); //Override potential cached page
        return;
    }
    console.log("Restoring unsubmitted changes!");
    var list = parsedData[1];
    //We have a new mainBlockList, but the text will be wrong because it's been reset from the server
    //However, if the server has delivered new text for this field we want to say so
    for(var prop in list){
      block = mainBlockList.getBlock(prop);
      if(list[prop].edited && block && list[prop].text != block.text && list[prop].newtext != block.text ){
        console.log("Field changed on server!");
        //If our changes match the new server text then we don't need to submit an edit
        if(list[prop].newtext != block.text){
            block.edited = list[prop].edited;
            var tmpStr = tagString+"New server text"+tagStringClose+": "+block.text + '\n'+tagString+'Your text'+tagStringClose+': ' + list[prop].newtext;
            block.newtext = list[prop].newtext;
            $(escape_jq(block.docElementId)).val(String(tmpStr));
        }
      }else if(list[prop].edited){
        block.edited = list[prop].edited;
        block.newtext = list[prop].newtext;
        $(escape_jq(block.docElementId)).val(String(block.newtext));
      }
    }
  }
}

//---------- End editor local storage handing --------------------

//---------- Editor submission and export handling ---------------

function exportAsJson(){

  var responseText = exportEdits();
  saveTextAsFile(responseText, 'Edits_'+pageKey+'.txt');

}

function exportEdits(field){
  //Collect edited blocks and jsonify
  //If field is null, then all blocks are checked
  //Otherwise only those beginning with 'field'
  var editedBlocks = [];
  var returnableBlock;
  var anyEdits = false;

  for( var key in mainBlockList.blockList){
    var block = mainBlockList.blockList[key];
    var blockInPage = document.getElementById(block.docElementId.substr(1, block.docElementId.length));
    //First of these conditions shouldn't occur in current way of producing conflict text
    var newtext = (block.newtext ? block.newtext.toString() : '');
    if(newtext.indexOf(tagString) != -1 || (blockInPage && blockInPage.value.indexOf(tagString) != -1)){
      alert(block.fieldname+'.'+block.key+" seems to contain conflicts\n Please fix these before submitting");
      return;
    }
    if(block.edited &&
      (!field || (block.fieldname.substr(0, field.length-4) == field.substr(4,field.length) ))){
      returnableBlock = blockToServer(block);
      editedBlocks.push(returnableBlock);
      anyEdits = true;
    }
  }
  if(!anyEdits){
    alert("Nothing to submit");
    return;
  }

  var responseText = makeDiff(editedBlocks, {});

  return responseText;
}

function submitEdits(dest){

  console.log("Submitting");
  showSubmitInProgress();
  var responseText = exportEdits();
  if(!responseText){
    resetSubmitInProgress();
    return;
  }

  var XHR = new XMLHttpRequest();
  XHR.open('POST', dest);
  XHR.setRequestHeader('Content-Type', 'text/plain');

  XHR.addEventListener('load', function(event) {
    //On success redirect to a success page
    var response = JSON.parse(XHR.response);
    if(!response.success){
      alert('Error submitting edits. '+response.fail+ ' Please try again.');
      resetSubmitInProgress();
    }else{
      window.location.replace(response.url);
    }
  });

  // Define what happens in case of error
  XHR.addEventListener('error', function(event) {
    var response = JSON.parse(XHR.response);
    alert('Error submitting edits. '+response.fail+ ' Please try again.');
    resetSubmitInProgress();
  });

  XHR.send(responseText);

}

function submitBlockEdits(dest, field){

  showSubmitInProgress();
  var responseText = exportEdits(field);
  if(!responseText){
    resetSubmitInProgress();
    return;
  }

  var XHR = new XMLHttpRequest();
  XHR.open('POST', dest);
  XHR.setRequestHeader('Content-Type', 'text/plain');

  XHR.addEventListener('load', function(event) {
    //On success, reset screen
    var response = JSON.parse(XHR.response);
    if(!response.success){
      alert('Error submitting edits. '+response.fail+ ' Please try again.');
    }
    resetSubmitInProgress();
  });

  // Define what happens in case of error
  XHR.addEventListener('error', function(event) {
    var response = JSON.parse(XHR.response);
    resetSubmitInProgress();
    alert('Error submitting edits. '+response.fail+ ' Please try again.');
  });

  XHR.send(responseText);

}

function blockToServer(block){
  //Take a Block and return a ResponseBlock

  //Restore the identifiers for a special field. This just has to be distinct. The server can correct its actual form
  var name = block.fieldname;
  if(block.special) name = '__' + name + '__';
  if(block.record && recordHashMap) name = recordHashMap.get(name);
  return new ResponseBlock(name, block.key, block.newtext, block.special);
}

function showSubmitInProgress(){
  //Make some change to page to show that submission is procededing
  //This might be nice as changing the submmit button to a spinner?
  //For now we hide it and put in 'Submitting...'
  var el = document.getElementById('SubmitButton');
  el.classList.add('hide');
  el = document.getElementById('SubmitDummy');
  el.innerHTML = 'Submitting ...';

  $("input[type='button'][id*=submit").each(function() {
      this.disabled = true;
      this.classList.add('disabledbutton');
  });

}

function resetSubmitInProgress(){
  //Make some change to page to show that submission is procededing
  //This might be nice as changing the submmit button to a spinner?
  //For now we hide it and put in 'Submitting...'
  var el = document.getElementById('SubmitButton');
  el.classList.remove('hide');
  el = document.getElementById('SubmitDummy');
  el.classList.add('hide');

  $("input[type='button'][id*=submit").each(function() {
      this.disabled = false;
      this.classList.remove('disabledbutton');
  });
}

//---------- End editor submission and export handling -----------

//---------- Editor DOM creation ---------------------------------

function populateEditorPage(blockList, startVisible=true){
  //Create the HTML elements using the blocklist
  //We create in two chunks

  setScanDate(blockList.date);
  setNiceTitle(blockList);
  var specialsDiv = document.getElementById('specialsDiv');
  var dataDiv = document.getElementById('dataDiv');
  var lastField = "";
  var fieldDiv;

  var fields = getBoxTitles(blockList);

  for(var i=0; i < fields.length; i++){

    var id = fields[i].substr(fields[i].indexOf(id_delimiter)+1, fields[i].length);
    var h2 = createKeyTitle(id);
    fieldDiv = document.createElement('div');
    fieldDiv.id = fields[i];
    fieldDiv.class = 'collapser';
    headerDiv = document.createElement('div');
    headerDiv.id = 'Header'+id_delimiter+id;
    headerDiv.class = 'header';
    var butt = createCollapserButt(id, open=startVisible);
    headerDiv.appendChild(butt);
    headerDiv.appendChild(h2);

    var blocks = blockList.getBlockIdsFromPartialID('#'+fields[i]);
    var eg_block = blockList.getBlock(blocks[0]);

    if(eg_block.special){
        specialsDiv.appendChild(headerDiv);
    }else{
        dataDiv.appendChild(headerDiv);
    }
    var block;
    for(var blockId in blocks){
      block = blockList.getBlock(blocks[blockId]);
      if(!block) continue;
      var item = createItemDiv(block.fieldname, block.key, block.special);
      fieldDiv.appendChild(item);
    }
      //Add block-reset button
      butt = createResetButt(fields[i]);
      fieldDiv.appendChild(butt);
      butt = createBlockSubmitButt(fields[i]);
      fieldDiv.appendChild(butt);
      if(! startVisible) fieldDiv.classList.add('hide');
      if(block.special){
          specialsDiv.appendChild(fieldDiv);
      }else{
          dataDiv.appendChild(fieldDiv);
      }

  }
  $( document ).trigger( "blockListReady");
}

function createItemDiv(item, field, special){

  var docElementId = 'Box'+id_delimiter+item+id_delimiter+field;

  var div = document.createElement("div");
  div.id = item;
  div.classList.add("inventory_row");
  var label = document.createElement("label");
  label.for = docElementId;
  label.innerHTML = field;
  div.appendChild(label);

  var textBox = document.createElement("textarea");
  textBox.cols = 75;
  textBox.rows = 1;
  textBox.id = docElementId;
  textBox.classList.add("edit_input");
  textBox.oninput = (function() {
		return function() {
			updateBlock(this);
		};
	})();

  if(special){
    div.appendChild(textBox);
  }else{
    var span = document.createElement('span');
    span.appendChild(textBox);
    div.appendChild(span);
  }
  return div;
}

function createResetButt(field){

  var butt = document.createElement('input');
  butt.setAttribute('type', 'button');
  butt.className = "resetbutt";
  butt.style='float:inherit;display:inline;';
  butt.value = "Reset block";
  butt.onclick = (function() {
		return function() {
			this.blur();
      resetEdits(field);
		};
	})();
  butt.title = "Reset to Original";

  return butt;
}

function createBlockSubmitButt(field){

  var butt = document.createElement('input');
  butt.setAttribute('type', 'button');
  butt.className = "submitbutt";
  butt.id = 'submit';
  butt.style='float:inherit;display:inline;';
  butt.value = "Submit block";
  butt.onclick = (function() {
		return function() {
			this.blur();
      submitBlockEdits(submitDest, field);
		};
	})();
  butt.title = "Submit Block";

  return butt;
}

function fitToText(elementId){
  //We need to fit boxes to text in several places, so make it a function so we can adjust padding or similar
  var jq_elementId = escape_jq(elementId);
  if( $(jq_elementId).length){
    $(jq_elementId).height($(jq_elementId).css('minHeight'));
    $(jq_elementId).height( $(jq_elementId)[0].scrollHeight + 5);
    //Hardcoded extra padding. Is unwielddy to calculate interior padding every fit. If font-sizes might be changed etc, then amend
  }
}

function fitAllToText(part_id){
  //Fit all text boxes in the div part_id to their content
    var blocks = mainBlockList.getBlockIdsFromPartialID(part_id);
    for (var blockid in blocks){
      fitToText(blocks[blockid]);
    }
}

function toggleTypePopup(box_id, data){
  //Toggles existence of popup containing the items in data, attached to element block_id

  var box = document.getElementById(box_id);
  if(!box) return;

  has_selectors = (document.getElementsByName(box_id + "_drop")).length > 0;
  var div;
  if(has_selectors){
    div = document.getElementById(box_id+'_drop');
    div.remove();
    return;
  }
  //Create popup containing selector
  div = document.createElement("div");
  div.class = "popup";
  div.id = box_id+'_drop';

  var selector = document.createElement("select");
  selector.name = box_id + "_drop";
  selector.onchange = (function(){
      var box_in = box;
      var that = selector;
      return function(){
          fillFromDrop(that, box_in);
      };
  })();
  var current_selection = box.value;

  var set_sel = false;
  for(var item in data){
    var sel = false;
    if(data[item] == current_selection){
      sel = true;
      set_sel = true;
    }
    selector.add(new Option(data[item], data[item], false, sel));
  }
  if(!set_sel) selector.selectedIndex = data.indexOf("string");//Default to string

  div.appendChild(selector);
  var parent = box.parentNode;
  parent.appendChild(div);
  div.style.display = "block";
}

function createTypePopButtons(blocklist, options){

  for(var key in blocklist.blockList){
    var parts = key.split(id_delimiter);
    if(parts[parts.length - 1] == 'type'){
      createDOMPopButton(key.substr(1, key.length), options);
    }
  }
}

function createDOMPopButton(box_id, options){
  //Creates button to pop up the type selector

  var box = document.getElementById(box_id);
  if(!box) return;

  var span = box.parentNode;

  //Create button
  var butt = document.createElement("input");
  butt.type="button";
  butt.setAttribute('value',"Types");
  butt.id = "Types";
  butt.innerHTML = "Types";
  butt.title = "Click to toggle known types";
  butt.classList.add("button");
  butt.classList.add("types_button");
  butt.classList.add("input_sections");

  butt.onclick  = (function(){
      var box_id_in = box_id;
      var options_in = options;
      return function(){
          toggleTypePopup(box_id_in, options_in);
      };
  })();

  span.appendChild(butt);
}

//---------- End editor DOM creation -----------------------------
