    function validate() {
	var col = eval("(" + document.getElementById("col_select").value + ")");
	var args = document.getElementById("args_field").value;

	var e = "\\s*(\\d{1,4})\\s*"
	var p1 = "^" + e;
	var p2 = "^\\s*(\\d{1,4})\\s*\\+\\s*(\\d{1,2})\\s*";

	for (var i=1; i < col['args'].length; i++) {
	    p1 += "\\s+" + e;
	    p2 += "\\s+" + e;	    
	}
	p1 += "$";
	p2 += "$";
	var opt1 = new RegExp(p1);
	var opt2 = new RegExp(p2);

	var result = p1;

	if ( m = args.match(opt1)) {
	    result = "[range(" + m[1] + "," + (eval(m[1])+19) + ")";
	    for (var i = 2; i < m.length; i++) {
		result += "," + m[i];
	    }
	    result += "]";
	    document.getElementById("col_name").value = col['name']
	    document.getElementById("dim_args").value = result;
	    return true
	}
	else if ( m = args.match(opt2)) {
	    result = "[range(" + m[1] + "," + (eval(m[1])+eval(m[2])+1) + ")";
	    for (var i = 3; i < m.length; i++) {
		result += "," + m[i];
	    }
	    result += "]";
	    document.getElementById("col_name").value = col['name'];
	    document.getElementById("dim_args").value = result;
	    return true
	}
	else {
	    alert( "Submit white space separated values (< 9999) representing '" + col["args"] + "'\n(first one can be of the form 'dddd+dd').");
	    return false;
	}
	alert( "Too big");
	return false
    }
