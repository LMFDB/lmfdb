
function isDisplayed(name){
  return record_fields.indexOf(name) != -1;
}

function isEditable(fieldname){
  return record_noedit.indexOf(fieldname) == -1;
}

function populateRecordEditorPage(blockList, startVisible=true){
  //Create the HTML elements using the blocklist

  setScanDate(blockList.date);

  var dataDiv = document.getElementById('dataDiv');
  var lastField = "";
  var fieldDiv;
  var keys = Object.keys(blockList.blockList).sort();


  var uniq_keys = {};
  for(var i=0; i<keys.length; i++){
    var str = keys[i];
    //Strip out field, leaving the 'Box_' bit
    var head = str.substr(1,str.lastIndexOf('_')-1 );
    uniq_keys[head] = 0;
  }
  fields = Object.keys(uniq_keys);
  var cnter = 1;
  for(var i=0; i<fields.length; i++){
    var block = blockList.getBlock('#'+fields[i]+'_count');
    var base = false;
    if(block && block.text == -1) base = true;
    if(base) continue;
    var h2 = createRecordTitle(cnter);
    cnter++;

    fieldDiv = document.createElement('div');
    fieldDiv.id = 'Box_'+lastField;
    fieldDiv.class = 'collapser';
    headerDiv = document.createElement('div');
    headerDiv.id = 'Header_'+lastField;
    headerDiv.class = 'header';
    var butt = createCollapserButt(lastField, open=startVisible);
    headerDiv.appendChild(butt);
    headerDiv.appendChild(h2);
    dataDiv.appendChild(headerDiv);

    for(var j=0; j<record_fields.length; j++){
      var label = record_fields[j];
      //Show entire schema here
      if(record_fields[j] == 'schema') label = 'oschema';
      var id = fields[i] +'_'+label;
      var block = blockList.getBlock('#'+id);
      if(block && isEditable(record_fields[j])){
        var item = createRecordDiv(block.fieldname, block.key);
        fieldDiv.appendChild(item);
      }else if (block){
        var item = createRecordLockedDiv(block.fieldname, block.key);
        fieldDiv.appendChild(item);
      }
    }
    var butt = createResetButt(lastField);
    fieldDiv.appendChild(butt);
    if(! startVisible) fieldDiv.classList.add('hide');
    dataDiv.appendChild(fieldDiv);
  }
  $( document ).trigger( "blockListReady");
}

function createRecordTitle(item){

  var h2 = document.createElement('h2');
  h2.classList.add("content_h2");
  h2.innerHTML = "Record Number: " + item;
  return h2;
}

function createRecordDiv(item, field){

  var docElementId = 'Box_'+item+'_'+field;

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
		}
	})();

  var span = document.createElement('span');
  span.appendChild(textBox);
  div.appendChild(span);
  return div;
}
function createRecordLockedDiv(item, field, special){

  var docElementId = 'Box_'+item+'_'+field;

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
  textBox.readOnly = true;
  textBox.classList.add("locked_input");

  var span = document.createElement('span');
  span.appendChild(textBox);
  div.appendChild(span);

  return div;
}
