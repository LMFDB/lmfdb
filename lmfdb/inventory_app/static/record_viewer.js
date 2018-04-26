/*jshint esversion: 6 */
var tooltip_dict = {'dummy': 'Record does not exist', 'extends': 'Schema is displayed as diff from numbered record', 'base' : 'This is the base record which others extend'};

function BaseRecord(num, name){
  //Holds the info about the base record for the diffed record types
  //Contains both the list number, the name, and the display name used by
  //other blocks to refer to it in page
  this.name = name;
  this.num = num;
  if(name && name != ''){
    this.displayname = name;
  }else{
    this.displayname = 'Record '+num;
  }
}
function unpackBaseRecord(blockList){

    for( var block in blockList.blockList){
        //Base record has count = -1 if not present, or empty schema, and not oschema, if is present
        if( block.substr(block.length-4, block.length) == 'base' && blockList.blockList[block].text){
          var part_id = block.substr(1, block.length-6); //Remove '_base'
          var blocks = blockList.getBlockIdsFromPartialID(part_id);
          var blockCont = blockList.getBlock('#'+part_id+id_delimiter+'name');
          var tmp_name = blockCont ? blockCont.text: '';
          var tmp_num = part_id.substr(part_id.lastIndexOf(id_delimiter)+1, part_id.length);
          return new BaseRecord(tmp_num, tmp_name);
        }
    }
    return new BaseRecord(0, '');
}

function populateRecordViewerPage(blockList, startVisible=true){
  //Create the HTML elements using the blocklist
  //We create in two chunks

  setScanDate(blockList.date);
  setNiceTitle(blockList);

  var dataDiv = document.getElementById('dataDiv');

  var fields = getBoxTitles(blockList);

  var table_div = document.createElement('div');
  var table = document.createElement('table');
  //table.class = 'viewerTable';
  table.classList.add('tablesorter');
  table.id = 'viewerTable';
  entry_styles = ['table_tag'];
  var table_head = document.createElement('thead');

  base_record = unpackBaseRecord(blockList);
  var row = createRecordRow(blockList, 'Key', '', base_record, header=true);
  table_head.appendChild(row);

  var row0 = createRecordRow(blockList, fields[0].substr(4, fields[0].length), '#'+fields[0]+id_delimiter, base_record);
  table_head.appendChild(row0);

  table.appendChild(table_head);

  var table_body = document.createElement('tbody');
  for(var i=1; i < fields.length; i++){
    row = createRecordRow(blockList, fields[i].substr(4, fields[i].length), '#'+fields[i]+id_delimiter, base_record);
    if(row){
      if(!row.classList.contains('viewerTableSpecial')){
        var clas = 'viewerTable';
        if(row.classList.contains('viewerTableSole')) clas +='Sole';
         clas += (i%2 == 0 ? 'Even':'Odd');
         row.classList.add(clas);
      }
      table_body.appendChild(row);
    }
  }
  table.appendChild(table_body);

  table_div.appendChild(table);
  dataDiv.appendChild(table_div);


  $( document ).trigger( "blockListReady");
}

function createRecordRow(blockList, field, id_start, base_record, header=false){
//field is the set id, in this case sequential numbers, used as record Num
  var table_row = document.createElement('tr');
  var clas = header ? 'viewerTableHeaders' : 'viewerTableEls';
  if(header){
    var table_el = document.createElement('th');
    table_el.innerHTML = 'Record Num';
  }else{
    var table_el = document.createElement('td');
    table_el.innerHTML = field;
  }
  table_el.classList.add(clas);
  table_row.appendChild(table_el);
  var is_base = (blockList.getBlock(id_start+'base') ? blockList.getBlock(id_start+'base').text : false);
  for(var j=0; j < record_fields.length; j++){
    if(header){
      table_el = document.createElement('th');
    }else{
      table_el = document.createElement('td');
    }
    table_el.classList.add(clas);
    if(header){
      table_el.innerHTML = capitalise(record_fields[j]);
      if(record_fields[j] in tooltip_dict) table_el.title = tooltip_dict[record_fields[j]];
    }else{
      var block = blockList.getBlock(id_start+record_fields[j]);
      var text = block ? block.text: '';
      if(record_fields[j] == 'schema' && typeof text == 'object'){
        text = text.join('; ');
      }
      else if(record_fields[j] == 'count' && text == '0'){
        text = 'Dummy Base';
        table_el.title = tooltip_dict.dummy;
        table_row.classList.add('viewerTableSpecial');
      }else if(record_fields[j] == 'extends' && base_record && blockList.getBlock(id_start+'diffed').text && ! is_base){
        text = base_record.displayname;
      }else if(record_fields[j] == 'extends' && is_base){
        text = '[Is base record]';
        table_el.title = tooltip_dict.base;
      }
      if(text) table_el.innerHTML = text;
    }
    table_row.appendChild(table_el);
  }
  //Non-diffed rows flagged as sole
  if( !header && ! blockList.getBlock(id_start+'diffed').text) table_row.classList.add('viewerTableSole');
  if( is_base) table_row.classList.add('viewerTableSpecial');
  return table_row;

}


function fillRecordHashMap(data){
  //Record blocks are numbered for ordering but we want to preserve the hashes linked to a given block for edit submissions

  for(var field in data){
    contents = data[field];
    //If this is records, we add entry to the map linking the field to the hash
    var records = ('hash' in contents && 'oschema' in contents);
    recordHashMap.set(field, contents.hash);
  }
}
