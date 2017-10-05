
var tooltip_dict = {'dummy': 'Record does not exist', 'extends': 'Schema is displayed as diff from this record'}

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
        if( block.substr(block.length-5, block.length) == 'count' && blockList.blockList[block].text == '-1'){
          var part_id = block.substr(1, block.length-7);
          var blocks = blockList.getBlockIdsFromPartialID(part_id);
          var tmp_name = blockList.blockList['#'+part_id+'_name'].text;
          var tmp_num = part_id.substr(part_id.lastIndexOf('_')+1, part_id.length);
          return new BaseRecord(tmp_num, tmp_name);
        }
    }
    return new BaseRecord(-1, '');
}

function populateRecordViewerPage(blockList, startVisible=true){
  //Create the HTML elements using the blocklist
  //We create in two chunks

  setScanDate(blockList.date);
  var dataDiv = document.getElementById('dataDiv');

  var keys = Object.keys(blockList.blockList).sort();
  var uniq_keys = {};
  for(var i=0; i<keys.length; i++){
    var str = keys[i];
    //Strip out field, leaving the 'Box_' bit
    var head = str.substr(1,str.lastIndexOf('_')-1 );
    uniq_keys[head] = 0;
  }
  fields = Object.keys(uniq_keys);

  var table_div = document.createElement('div');
  var table = document.createElement('table');
  table.class = 'viewerTable';
  entry_styles = ['table_tag'];

  base_record = unpackBaseRecord(blockList);

  var row = createRecordRow(blockList, 'Key', '', base_record, header=true)
  table.appendChild(row);
  for(var i=0; i < fields.length; i++){
    row = createRecordRow(blockList, fields[i].substr(4, fields[i].length), '#'+fields[i]+'_', base_record);
    if(row){
      if(!row.classList.contains('viewerTableSpecial')){
        var clas = 'viewerTable';
        console.log(row.classList);
        if(row.classList.contains('viewerTableSole')) clas +='Sole';
         clas += (i%2 == 0 ? 'Even':'Odd');
         row.classList.add(clas);
      }
      table.appendChild(row);
    }
  }

  table_div.appendChild(table);
  dataDiv.appendChild(table_div);


  $( document ).trigger( "blockListReady");
}

function createRecordRow(blockList, field, id_start, base_record, header=false){

  var table_row = document.createElement('tr');
  var clas = header ? 'viewerTableHeaders' : 'viewerTableEls';
  var table_el = document.createElement('td');
  if(header){
    table_el.innerHTML = 'Record Num';
  }else{
    table_el.innerHTML = field;
  }
  table_el.classList.add(clas);
  table_row.appendChild(table_el);

  for(var j=0; j < record_fields.length; j++){
    var table_el = document.createElement('td');
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
      else if(record_fields[j] == 'count' && text == '-1'){
        text = 'Dummy Base';
        table_el.title = 'Record does not exist';
        table_row.classList.add('viewerTableSpecial');
      }else if(record_fields[j] == 'extends' && base_record && blockList.getBlock(id_start+'diffed').text){
        text = base_record.displayname;
      }

      if(text) table_el.innerHTML = text;
    }
    table_row.appendChild(table_el);
  }
  //Non-diffed rows flagged as sole
  if( !header && ! blockList.getBlock(id_start+'diffed').text) table_row.classList.add('viewerTableSole');

  return table_row;

}
