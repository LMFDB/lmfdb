
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

//---------- General data fetching  ------------------------------

function fetchAndPopulateData(blockList, pageCreator){
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
    pageCreator(XHR.blockList);
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

