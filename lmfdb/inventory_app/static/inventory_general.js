
//---------- General block and list handling ---------------------

function Block(field, key, text, docElementId){
  //A block is a single editable field
  //It has the field name (name of field in lmfdb collection)
  //the key (e.g. description, type etc)
  //and both the original and new texts, plus an edited flag
  //Finally it is linked to a DOM element, a textinput, by id string
  this.fieldname = field;
  this.key = key;
  this.text = text;
  this.newtext = text;
  this.edited = false;
  this.docElementId = docElementId;
  this.special = false;
}

function BlockList(db, coll){
	//Construct block list object holding a list of blocks
  //The keys are the id's of DOM edit fields
  this.db = db;
  this.coll = coll;
  this.blockList = {};
  this.addBlock = addBlock;
  this.delBlock = delBlock;
  this.getBlock = getBlock;
  this.setSpecialById = setSpecialById;
  this.getBlockIdsFromPartialID = getBlockIdsFromPartialID;
}
function addBlock(field, key, text, docElementId){
	//Add a block to list
	var myBlock = new Block(field, key, text, docElementId);
  this.blockList[docElementId] = myBlock;
}

function delBlock(id){
	//Delete block from list
	this.blockList.splice(id, 1);
}

function getBlock(id){
  //Look up block from ID
  return this.blockList[id];
}

function getBlockIdsFromPartialID(id){
  //Look up block where id matches the beginning
  blocks =[];
  if(id[0] != '#') id = '#'+id;
  for(key in this.blockList){
    if(key.indexOf(id) != -1){
      blocks.push(key);
    }
  }
  return blocks;
}

function setSpecialById(id){
    //Tag the block with id=id as a special
    this.getBlock(id).special = true;
}

//---------- End general block and list handling -----------------

//---------- Helpers for some other block-wise tasks -------------


//---------- End helpers for some other block-wise tasks ---------

//---------- General data fetching  ------------------------------

function fetchAndPopulateData(blockList, pageCreator, startVisible=startVisible){
  //Fetch the json data for this page
  var current_url = window.location.href;
  var data_url = current_url + 'data';
  var XHR = new XMLHttpRequest();
  XHR.open('GET', data_url);
  XHR.setRequestHeader('Content-Type', 'text/plain');
  XHR.blockList = blockList;

  XHR.addEventListener('load', function(event) {
    //On success return data
    var data = JSON.parse(XHR.response);
    populateBlocklist(XHR.blockList, data);
    pageCreator(XHR.blockList, startVisible=startVisible);
  });

  // Define what happens in case of error
  XHR.addEventListener('error', function(event) {
    console.log("Failed to fetch page data");
  });

  XHR.send('');
}

function populateBlocklist(blockList, data){
  //Fill given blocklist from given data
  var contents = "";
  var docElementId = "";

  //Do specials and then do main data
  var special = false;
  //Data should contain 2 sections, specials and data
  for(var item  of ['specials', 'data']){
    if( item == 'specials'){
      special = true;
    }else{
      special = false;
    }
    for(var field in data[item]){
      contents = data[item][field];
      for(tag in contents){
        docElementId = '#Box_'+field+'_'+tag;
        blockList.addBlock(field, tag, contents[tag], docElementId);
        if(special) blockList.setSpecialById(docElementId);
      }
    }
  }
}

//---------- End general data fetching  --------------------------
//---------- General data descriptions and submit ---------------------------
function ResponseBlock(field, key, text){
  //Minimal description of data suitable for Jsonifying
    this.item = field;
    this.field = key;
	this.content = text;
}

function makeDiff(editedBlocks, ids){
  //Make a diff from a list of ResponseBlocks
  //If passing db will always want to pass collection too
  var response = pageId;
  console.log(ids.db, ids.collection);
  console.log(response);
  if(ids.db) response.db = ids.db;
  if(ids.collection) response.collection = ids.collection;
  console.log(response);
  response.diffs = editedBlocks;
  return  JSON.stringify(response);
}

function genSubmitEdits(dest, diff, info){

  if(info.debug) console.log("Submitting");
  if(!diff) return;

  var XHR = new XMLHttpRequest();
  XHR.open('POST', dest);
  XHR.setRequestHeader('Content-Type', 'text/plain');

  if(info.redirect){
    XHR.addEventListener('load', function(event) {
      //On success redirect to a success page
      var response = JSON.parse(XHR.response);
      window.location.replace(response['url']);
    });
  }else if(info.refresh){
      XHR.addEventListener('load', function(event) {
      //On success refresh the page
      var response = JSON.parse(XHR.response);
      location.reload();
    });
  }else if(info.call){
      XHR.addEventListener('load', function(event) {
      //On success call given function
      var response = JSON.parse(XHR.response);
      info.call();
    });
  }else{
    XHR.addEventListener('load', function(event) {
      //On success redirect to a success page
      var response = JSON.parse(XHR.response);
    });
  }
  // Define what happens in case of error
  XHR.addEventListener('error', function(event) {
    alert('Error submitting edits. Please try again.');
  });

  XHR.send(diff);
}


//---------- End general data descriptions ---------------------------

//---------- General page construction --------------------------------
function createKeyTitle(item){

  var h2 = document.createElement('h2');
  h2.classList.add("content_h2");
  h2.innerHTML = "Key name: " + item;
  return h2;
}

function createCollapserButt(field, open=true){

  var butt = document.createElement('input');
  butt.setAttribute('type', 'button');
  butt.className = "expanderbutt";
  butt.style='float:inherit;display:inline;';
  butt.value = open ? "-" : "+";
  butt.onclick = (function() {
    var box_id = 'Box_'+field;
		return function() {
			this.blur();
      var div = document.getElementById(box_id);
      if(div.classList.contains('hide')){
          div.classList.remove('hide');
          this.value = "-";
          fitAllToText(box_id);
      }else{
        div.classList.add('hide');
        this.value = "+";
      }
		}
	})();
  butt.title = "Expand/Collapse Section";

  return butt;
}

function capitalise(str){
//Capitalise first letter of given string
  return str[0].toUpperCase() + str.slice(1);

}
