function hide_tooltip(){
    document.getElementById("tooltipper").style.left=0;
    document.getElementById("tooltipper").style.top=0;
    document.getElementById("tooltipper").style.width= 1;
    document.getElementById("tooltipper").style.height =1;
    document.getElementById("tooltipper").innerHTML="" ;
}
function show_tooltip(event,txt){
    document.getElementById("tooltipper").style.left=event.clientX+20;
    document.getElementById("tooltipper").style.top=event.clientY+30;
    document.getElementById("tooltipper").style.width= 300;
    document.getElementById("tooltipper").style.height =150;
    document.getElementById("tooltipper").innerHTML=txt;
}




/*
 * Clear Default Text: functions for clearing and replacing default text in
 * <input> elements.
 *
 * by Ross Shannon, http://www.yourhtmlsource.com/
 */

addEvent(window, 'load', init, false);

function init() {
    var formInputs = document.getElementsByTagName('input');
    for (var i = 0; i < formInputs.length; i++) {
        var theInput = formInputs[i];
        
        if (theInput.type == 'text' && theInput.className.match(/\bcleardefault\b/)) {  
            /* Add event handlers */          
            addEvent(theInput, 'focus', clearDefaultText, false);
            addEvent(theInput, 'blur', replaceDefaultText, false);
            
            /* Save the current value */
            if (theInput.value != '') {
                theInput.defaultText = theInput.value;
            }
        }
    }
}



function clearDefaultText(e) {
    var target = window.event ? window.event.srcElement : e ? e.target : null;
    if (!target) return;
    
    if (target.value == target.defaultText) {
        target.value = '';
    }
}

function replaceDefaultText(e) {
    var target = window.event ? window.event.srcElement : e ? e.target : null;
    if (!target) return;
    
    if (target.value == '' && target.defaultText) {
        target.value = target.defaultText;
    }
}

function list_characters() {
    if(document.space_choice.level.value=='') {
	alert('Please give a level first!');
	return;
    } else {
	document.space_choice.character.value='';
	removeElement(document.space_choice,'select','level_list');
	removeElement(document.space_choice,'input','weight_list');
	document.space_choice.submit();
    }
}

function show_geometry() {
    if(document.space_choice.level.value=='') {
	alert('Please give a level first!');
	return;
    } else {
	document.space_choice.character.value='';
	document.space_choice.weight.value='';
	/*document.space_choice.weight.value=0;
	removeElement(document.space_choice,'select','level_list');
	removeElement(document.space_choice,'hidden','level');
	removeElement(document.space_choice,'text','character'); */
	document.space_choice.submit();
    }
}



function check_space_choice_Form() {
    if (document.space_choice.character.value == document.space_choice.character.defaultText) {
	document.space_choice.character.value=0;
    }
    var agree=true;
    var level_set=false;
    var weight_set=false;
    var form=document.space_choice;
    var weight;
    var N = document.space_choice.level.value;
    var k = document.space_choice.weight.value; 
    agree = true;
    if( (N>1000 || k >1000) || (N >30 && k > 30)) {
	s="This might take some time. Are you sure you want to use these parameters?";
	level_set=true;
	weight_set=true;
	agree=confirm(s);
    }
    if(agree) {
	if(k < 2) {
	    alert("Weight 1 (or less) modular forms are not implemented (yet)!");
	    weight_set=true;
	    document.space_choice.weight.value=document.space_choice.weight.defaultValue;
	}
    }
    if (agree) {
	document.space_choice.submit();
    } else {
	if(level_set) {
	    document.space_choice.level.value=document.space_choice.level.defaultValue;
	}
	if(weight_set) {
	    document.space_choice.weight.value=document.space_choice.weight.defaultValue;
	}
	return false;
    }
    
    /*alert(document.space_choice.character.value);*/
    if(document.space_choice.character.value=="Trivial character") {
	document.space_choice.character.value=0;
    }
}

function check_table_form() {
    s="This might take some time. Are you sure you want to use these parameters?";
    var agree=true;
    var level_set=false;
    var weight_set=false;
    var d= document.get_tables_of_stuff.level_max - document.get_tables_of_stuff.level_min;    
    if(d < 0 ||  d > 1000) {	
	agree=confirm(s);
    }
    if (agree) {
	var get_all=0;
	if(document.get_tables_of_stuff.list_chars[0].checked) {
	    get_all="0";
	} else {
	    get_all="1";
	}
	url="/ModularForm/GL2/Q/holomorphic/";
	url=url+"?level_min="+document.get_tables_of_stuff.level_min.value+"&level_max="+document.get_tables_of_stuff.level_max.value;    
	url=url+"&list_chars="+get_all+"&get_table=1"+"&weight="+document.space_choice.weight.value;
	mainWindow = window.open(url,'Tables of dimensions','width=400,height=400,scrollbars=yes,resizable=yes')
	    /*document.get_tables_of_stuff.submit();*/
    }
  }

function draw_fd() {
	url="/ModularForm/GL2/Q/holomorphic/";
	url=url+"?plot=1&level="+document.space_choice.level.value;
	mainWindow = window.open(url,'Plot of fundamental domain','width=400,height=400,scrollbars=yes,resizable=yes')
}


function eventTrigger (e) {
    if (! e)
        e = event;
    return e.target || e.srcElement;
}

function selectWeight(e) {
    var obj = eventTrigger (e);
    document.space_choice.weight.value = obj.value;
    document.get_tables_of_stuff.weight.value = obj.value;
    return true;
}

function selectLevel(e) {
    var obj = eventTrigger (e);
    /*elt=$(document.space_choice).find('hidden[name=level]');
    form = document.space_choice;
    alert(form.elements["weight"].value);
    elt.value=obj.value; */
    document.space_choice.level.value = obj.value;
    return true;
}




function getAbsolutePath() {
    var loc = window.location;
    var pathName = loc.pathname.substring(0, loc.pathname.lastIndexOf('/') + 1);
    return loc.href.substring(0, loc.href.length - ((loc.pathname + loc.search + loc.hash).length - pathName.length));
}
