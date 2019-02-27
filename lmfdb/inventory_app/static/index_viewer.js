
/*jshint esversion: 6 */

var tooltip_dict = {'keys': '-1: descending, 1: ascending, 2d: using 2d ordering'};


function populateIndexViewerPage(blockList, startVisible=true){
  //Create the HTML elements using the blocklist
  //We create in two chunks

  //setScanDate(blockList.date);
  setNiceTitle(blockList);

  console.log(blockList);
  var dataDiv = document.getElementById('dataDiv');

  var fields = sortTitles(getBoxTitles(blockList));

  var table_div = document.createElement('div');
  var table = document.createElement('table');
  table.class = 'viewerTable';
  entry_styles = ['table_tag'];

  var row = createIndexRow(blockList, 'Key', '', header=true);
  table.appendChild(row);
  for(var i=0; i < fields.length; i++){
    row = createIndexRow(blockList, fields[i].substr(4, fields[i].length), '#'+fields[i]+id_delimiter);
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

function createIndexRow(blockList, field, id_start, header=false){
//field is the set id, in this case sequential numbers, used as record Num
  var table_row = document.createElement('tr');
  var clas = header ? 'viewerTableHeaders' : 'viewerTableEls';
  var table_el = document.createElement('td');
  if(header){
    table_el.innerHTML = 'Number';
  }else{
    table_el.innerHTML = field;
  }
  table_el.classList.add(clas);
  table_row.appendChild(table_el);
  for(var j=0; j < index_fields.length; j++){
    table_el = document.createElement('td');
    table_el.classList.add(clas);
    if(header){
      table_el.innerHTML = capitalise(index_fields[j]);
      if(index_fields[j] in tooltip_dict) table_el.title = tooltip_dict[index_fields[j]];
    }else{
      var block = blockList.getBlock(id_start+index_fields[j]);
      var text = block ? block.text: '';
      if(text) table_el.innerHTML = text;
    }
    table_row.appendChild(table_el);
  }
  //Non-diffed rows flagged as sole
  return table_row;

}

function sortTitles(array){

  n_array = array.map((a) => a.substr(4, a.length)/1).sort(function(a,b){return a - b;});
  array = n_array.map((a) => 'Box'+id_delimiter+a);
  return array;
}
