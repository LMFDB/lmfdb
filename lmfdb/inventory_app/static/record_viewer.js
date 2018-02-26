/*jshint esversion: 6 */
var tooltip_dict = {'dummy': 'Record does not exist', 'extends': 'Schema is displayed as diff from numbered record', 'base' : 'This is the base record which others extend'};
var vals_to_sort = ['count'];

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
  table.class = 'viewerTable';
  table.id = 'viewerTable';
  entry_styles = ['table_tag'];

  base_record = unpackBaseRecord(blockList);
  var row = createRecordRow(blockList, 'Key', '', base_record, header=true);
  table.appendChild(row);
  for(var i=0; i < fields.length; i++){
    row = createRecordRow(blockList, fields[i].substr(4, fields[i].length), '#'+fields[i]+id_delimiter, base_record);
    if(row){
      if(!row.classList.contains('viewerTableSpecial')){
        var clas = 'viewerTable';
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
//field is the set id, in this case sequential numbers, used as record Num
  var table_row = document.createElement('tr');
  var clas = header ? 'viewerTableHeaders' : 'viewerTableEls';
  if(header){
    var table_el = document.createElement('th');
    table_el.innerHTML = 'Record Num';
    table_el.onclick = function() {sortTable(0) };
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
      if(vals_to_sort.includes(record_fields[j])){
        table_el.onclick = function() { sortTable(j) };
      }
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

function sortTable(n) {
  var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
  table = document.getElementById("viewerTable");
  switching = true;
  // Set the sorting direction to ascending:
  dir = "asc";
  /* Make a loop that will continue until
  no switching has been done: */
  while (switching) {
    // Start by saying: no switching is done:
    switching = false;
    rows = table.getElementsByTagName("TR");
    /* Loop through all table rows (except the
    first two, which contains table headers and dummy row): */
    for (i = 2; i < (rows.length - 1); i++) {
      // Start by saying there should be no switching:
      shouldSwitch = false;
      /* Get the two elements you want to compare,
      one from current row and one from the next: */
      x = rows[i].getElementsByTagName("TD")[n];
      y = rows[i + 1].getElementsByTagName("TD")[n];
      /* Check if the two rows should switch place,
      based on the direction, asc or desc: */
      if (dir == "asc") {
        if (Number(x.innerHTML) > Number(y.innerHTML)) {
          // If so, mark as a switch and break the loop:
          shouldSwitch= true;
          break;
        }
      } else if (dir == "desc") {
        if (Number(x.innerHTML) < Number(y.innerHTML)) {
          // If so, mark as a switch and break the loop:
          shouldSwitch= true;
          break;
        }
      }
    }
    if (shouldSwitch) {
      /* If a switch has been marked, make the switch
      and mark that a switch has been done: */
      rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
      switching = true;
      // Each time a switch is done, increase this count by 1:
      switchcount ++;
    } else {
      /* If no switching has been done AND the direction is "asc",
      set the direction to "desc" and run the while loop again. */
      if (switchcount == 0 && dir == "asc") {
        dir = "desc";
        switching = true;
      }
    }
  }
}
