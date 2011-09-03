function parseJsonTable(url, out) {
	jQuery.get(url, function(txt) { parseJsonTable2(txt,out); });
}
function parseJsonTable2(txt, out) {
	var value = JSON.parse(txt.trim().replace(/\n/g, "\\n"));
	var html = '';
	for(var name in value) {
		html += '<h3>' + name + '</h3>';
		html += '<table id="thetable'+name+'" class="tablesorter display" cellpadding="0" cellspacing="0" border="0"></table>';
	}
	out.html(html);
	for(var name in value) {
		var data = value[name].split(/\n/);
		for(var i=0; i<data.length; i++) {
			data[i] = data[i].split(' ');
		}
		var columns = [];
		for(var i=0; i<data[0].length; i++) {
			columns[i] = { "sTitle": "Column " + (i+1) };
		}
		$('#thetable'+name).dataTable( {
		"aaData": data,
		"aoColumns": columns } );	
	}
}

function updateMetadata(id, property, value) {
  jQuery.get("/upload/updateMetadata", {id: id, property: property, value: value});
}

function updateMappingRules(data, id) {
  rules = $('#regexp'+id).val().split(/\n/).filter(function(x) { return x.trim() != ""})

  for(var i=0; i<data.length; i++) {
    data[i][3] = "";
    for(var j=0; j<rules.length/2; j++) {
      re = new RegExp(rules[j+j]);
      sub = rules[j+j+1];
      if(re.test(data[i][2])) {
        data[i][3]=data[i][2].replace(re, sub);
        break;
      }
    }
  }
  $('#table'+id).dataTable( {
    "aaData" : data,
    "aoColumns" : [ {"sTitle" : ""}, {"sTitle" : ""}, {"sTitle" : "Filename"}, {"sTitle" : "Related-to web page"} ],
    "bDestroy" : true
  });
}