/*jshint esversion: 6 */
var recordHashMap; //Dummy in general, some pages use this

var id_delimiter = ':'; //Character(s) used to join sections of ids
//---------- General block and list handling ---------------------

function Block(field, key, text, docElementId){
  //A block is a single editable field
  //It has the field name (name of field in lmfdb table)
  //the key (e.g. description, type etc)
  //and both the original and new texts, plus an edited flag
  //Finally it is linked to a DOM element, by id string
  this.fieldname = field;
  this.key = key;
  this.text = text;
  this.newtext = text;
  this.edited = false;
  this.docElementId = docElementId;
  this.special = false;
  this.editable = true; //Whether field is editable, or not
  this.record = false;
}

function BlockList(db, table){
	//Construct block list object holding a list of blocks
  //The keys are the id's of DOM edit fields
  this.db = db;
  this.table = table;
  this.blockList = {};
  this.date = null;
  this.addBlock = addBlock;
  this.delBlock = delBlock;
  this.getBlock = getBlock;
  this.setSpecialById = setSpecialById;
  this.setRecordById = setRecordById;
  this.getBlockIdsFromPartialID = getBlockIdsFromPartialID;
}
function addBlock(field, key, text, docElementId){
	//Add a block to list
  if(text instanceof Array) text = text.join('; ');
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
  //Look up block where id matches the Prefix and id part
  //Block names are Prefix, demimiter, id, delimiter, suffix
  blocks =[];
  if(id[0] != '#') id = '#'+id;
  for(var key in this.blockList){
    var key_secs = key.split(id_delimiter);
    var new_key = key_secs.slice(0,2).join(id_delimiter);
    if(new_key === id){
      blocks.push(key);
    }
  }
  return blocks;
}

function setSpecialById(id){
    //Tag the block with id=id as a special
    this.getBlock(id).special = true;
}

function setRecordById(id){
    //Tag the block with id=id as a special
    this.getBlock(id).record = true;
}

function setNotEditableById(id){
    //Tag the block with id=id as a special
    this.getBlock(id).editable = false;
}

//---------- End general block and list handling -----------------

//---------- Helpers for some other block-wise tasks -------------

function getBoxTitles(blockList){
  //Returns all the unique box names. Assumes name is all the bit before the final
  var keys = Object.keys(blockList.blockList);
  var uniq_keys = {};
  for(var i=0; i<keys.length; i++){
    var str = keys[i];
    //Strip out field, leaving the 'Box_' bit
    var head = str.substr(1,str.lastIndexOf(id_delimiter)-1 );
    uniq_keys[head] = 0;
  }
  var fields = Object.keys(uniq_keys);
  return fields;
}

function getBoxKeys(blockList){
  //Returns all the unique field names. Assumes name is all the bit between BOX and final
  var keys = Object.keys(blockList.blockList).sort();
  var uniq_keys = {};
  for(var i=0; i<keys.length; i++){
    var str = keys[i];
    //Strip out field, leaving the 'Box_' bit
    var head = str.substring(str.indexOf(id_delimiter)+1,str.lastIndexOf(id_delimiter) );
    uniq_keys[head] = 0;
  }
  var fields = Object.keys(uniq_keys);
  return fields;
}


//---------- End helpers for some other block-wise tasks ---------

//---------- General data fetching  ------------------------------
function fetchAndDownloadData(pageType){
  //Fetch the json data for this page and trigger download
  var current_url = window.location.href;
  var data_url = current_url + 'data';
  var XHR = new XMLHttpRequest();
  XHR.open('GET', data_url);
  XHR.setRequestHeader('Content-Type', 'text/plain');

  XHR.addEventListener('load', function(event) {
    //On success return data
    console.log(XHR.response);
	  var data = JSON.parse(XHR.response);
    if(! jQuery.isEmptyObject(data)){
      var filename = pageKey.replace('.', '_') +'_'+ pageType+'_download.json';
      saveTextAsFile(XHR.response, filename, 'text/json');
    }else{
      alert("No data to download");
    }
  });

  // Define what happens in case of error
  XHR.addEventListener('error', function(event) {
    console.log("Failed to fetch data for download");
    alert("Failed to fetch data for download");
  });

  XHR.send('');
}

function fetchAndPopulateData(blockList, pageCreator, startVisible=true){
  //Fetch the json data for this page
  var current_url = window.location.href;
  var data_url = current_url + 'data';
  var XHR = new XMLHttpRequest();
  XHR.open('GET', data_url);
  XHR.setRequestHeader('Content-Type', 'text/plain');
  XHR.blockList = blockList;

  XHR.addEventListener('load', function(event) {
    //On success return data
    console.log(XHR.response);
	var data = JSON.parse(XHR.response);
	console.log(data, jQuery.isEmptyObject(data));
    if(jQuery.isEmptyObject(data)){
	    div = document.getElementById('dataDiv');
    	div.innerHTML = "<span class='err_text'>Failed to fetch page data. This is most likely due to a connection or authentication failure with the LMFDB backend.<p>Please check you  have an open tunnel (e.g. using warwick.sh) and have a passwords.yaml file in lmfdb root containing the appropriate passwords, or reload the page to try again.</p></span>";

    }else{
	    populateBlocklist(XHR.blockList, data);
    	pageCreator(XHR.blockList, startVisible=startVisible);
      $( document ).trigger("dataPopulated");
    }
  });

  // Define what happens in case of error
  XHR.addEventListener('error', function(event) {
    console.log("Failed to fetch page data");
    div = document.getElementById('dataDiv');
    div.class = 'err_text';
    div.innerHTML = "Failed to fetch page data. This is most likely due to a connection or authentication failure with the LMFDB backend.<p>Please check you  have an open tunnel (e.g. using warwick.sh) and have a passwords.yaml file in lmfdb root containing the appropriate passwords, or reload the page to try again.</p>";
  });

  XHR.send('');
}

function populateBlocklist(blockList, data){
  //Fill given blocklist from given data
  var contents = "";
  var docElementId = "";
  blockList.date = data.scrape_date;
  //Do specials and then do main data
  var special = false;
  //Data should contain 2 sections, specials and data
  var record = false;
  for(var item  of ['specials', 'data']){
    if( item == 'specials'){
      special = true;
    }else{
      special = false;
    }
    for(var field in data[item]){
      contents = data[item][field];
      record = ('hash' in contents && 'oschema' in contents);
      for(var tag in contents){
        var fieldname = field;
        docElementId = '#Box'+id_delimiter+fieldname+id_delimiter+tag;
        blockList.addBlock(fieldname, tag, contents[tag], docElementId);
        if(special) blockList.setSpecialById(docElementId);
        if(record) blockList.setRecordById(docElementId);
      }
    }
  }
  if(recordHashMap) fillRecordHashMap(data.data);

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
  //If passing db will always want to pass table too
  var response = pageId;
  console.log(ids.db, ids.table);
  console.log(response);
  if(ids.db) response.db = ids.db;
  if(ids.table) response.table = ids.table;
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
      window.location.replace(response.url);
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
    var box_id = 'Box'+id_delimiter+field;
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
		};
	})();
  butt.title = "Expand/Collapse Section";

  return butt;
}

function capitalise(str){
//Capitalise first letter of given string
  return str[0].toUpperCase() + str.slice(1);
}

function createBoxName(item, field){
  return "#Box"+id_delimiter+item+id_delimiter+field;
}

function setScanDate(date){
  var el = document.getElementById('scandate');
  el.innerHTML = date;
}

function setNiceTitle(blockList){
  var el = document.getElementById('nicename');
  var nameblock = blockList.getBlock('#Box'+id_delimiter+'INFO'+id_delimiter+'nice_name');
  if(nameblock && el) el.innerHTML = nameblock.text;

}

function escape_jq( myid ) {

    return myid.replace( /(:|\.|\[|\]|,|=|@)/g, "\\$1" );

}

function saveTextAsFile(textToWrite, filename, type_in){
    /* globals destroyClickedElement, Blob*/
    //Create file and offer for "download"
    //Borrowed and slightly adapted from internet postings
    function destroyClickedElement(event){
              document.body.removeChild(event.target);
          }
    if(typeof type_in == "undefined") type_in = 'text/plain';

    var textFileAsBlob = new Blob([textToWrite], {type:type_in});
    var downloadLink = document.createElement("a");
    downloadLink.download = filename;
    downloadLink.innerHTML = "Download File";
    downloadLink.href = window.URL.createObjectURL(textFileAsBlob);
    downloadLink.onclick = destroyClickedElement;
    downloadLink.style.display = "none";
    document.body.appendChild(downloadLink);
    downloadLink.click();
}
