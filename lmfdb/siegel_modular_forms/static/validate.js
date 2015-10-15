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
	alert( "Error: invalid input: " + args + "\n\n Valid input: x for scalar valued and x j for vector valued modular forms. Here x is a non-negative integer k <= 9999 or a range in the form k+n, where k and n are non-negative integers <= 9999 and <= 99, respectively. Moreover, 'j' is a non-negative integer <= 99.\n\n The short hand 'k+n' stands for 'k plus n more succesive integers'.");
	return false;
    }
    alert( "Error: input too big");
    return false;
}


function prepare_query() {
    
    var fields = [ "weight", "degree_of_field", "degree", "representation"]
    var queryObj = new Object();

    var opt1 = "^\\s*([1-9][0-9]*)\\s*$";
    var opt2 = "^\\s*[1-9][0-9]*(\\s+[1-9][0-9]*)+\\s*$";
    var opt3 = "^\\s*([1-9][0-9]*)\\s*\\+\\s*([1-9][0-9]*)\\s*$";
    var c = 0;
    
    try {
	for (var i=0; i<fields.length; i++) {

	    if ("representation" == fields[i] | "weight" == fields[i]) {
		opt1 = "^\\s*([0-9]+)\\s*$";
		opt2 = "^\\s*[0-9]+(\\s+[0-9]+)+\\s*$";
		opt3 = "^\\s*([0-9]+)\\s*\\+\\s*([1-9][0-9]*)\\s*$";
	    }
	    else {
		opt1 = "^\\s*([1-9][0-9]*)\\s*$";
		opt2 = "^\\s*[1-9][0-9]*(\\s+[1-9][0-9]*)+\\s*$";
		opt3 = "^\\s*([1-9][0-9]*)\\s*\\+\\s*([1-9][0-9]*)\\s*$";
	    }
	    
	    var input = document.getElementById(fields[i]).value.trim()

	    if ( "" == input) {
		c++;
		continue;
	    }
	    else if ( m = input.match( opt1)) {
		a = String( parseInt(m[1]))
		eval( "queryObj." + fields[i] + "=a")
		continue;
	    }
	    else if ( m = input.match( opt2)) {
		a = input.split(/\s+/);
		for( var j=0; j < a.length; j++) {
		    a[j] = String( parseInt(a[j]));
		}
		eval( "queryObj." + fields[i] + "=new Object( {'$in': a})");
		continue;
	    }
	    else if ( m = input.match( opt3)) {
		a = m[1];
		b = m[2];
		c = [];
		for ( var j=0; j<=b; j++) {
		    c[j] = String( parseInt(a) + j);
		}
		eval( "queryObj." + fields[i] + "=new Object( {'$in': c})");
		continue;
	    }
	    else {
		alert( "Error: confusing input: '" + input + "'.\n\nValid input: one ore more space separated non-negative integers, or a range in the form 'k+n' (meaning 'k plus n more integers').\n\nDo not complain when you ask for degree '0' and have to read this message.");
		return false;
	    }
	    
	}
    }
    catch( err) {
	alert( err + "\n\nError: confusing input: '" + input + "'.\n\nValid input: one ore more space separated non-negative integers, or a range in the form 'k+n' (meaning 'k plus n more integers').\n\nDo not complain when you ask for degree '0' and have to read this message.");
	return false;
    }
    if ( 4 == c) return false;
    // q_dict = JSON.stringify( queryObj);
    // alert( '<'+q_dict+'>');
    document.getElementById("query").value = JSON.stringify( queryObj);
    return true;
}
