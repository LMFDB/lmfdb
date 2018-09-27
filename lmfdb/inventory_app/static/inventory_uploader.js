/*jshint esversion: 6 */

function importJson(){
  //Upload either by file drag-and-drop below the line, or typing/pasting text into the input and clicking the continue button

  //Disable drag-drop loading on window
  window.addEventListener('dragover', function(e) {
    e.preventDefault();
  },false);

  window.addEventListener('drop', function(e) {
    e.preventDefault();
  },false);

  //Disable import div expander button
  var butt = document.getElementById("importbutt");
  butt.className = "disabledbutton";
  butt.disabled = true;

  var div = document.getElementById("fileDropper");
  div.innerHTML = "<hr> Drag a file below the line above to import it, or type/paste into the box and click Go.<br>";

  var uploadText = document.createElement("textarea");
  uploadText.id = "UploadBox";
  uploadText.className = "upload_box";
  div.appendChild(uploadText);

  var contButton = document.createElement("button");
  contButton.title = "Import text into page";
  contButton.innerHTML = "Go";
  contButton.onclick = (function() {
		return function() {
      var box = document.getElementById("UploadBox");
      parseAndUpload("Box", box.value);
		};
	   })();

  div.appendChild(contButton);

  div.addEventListener('dragover', function(e) {
    e.stopPropagation();
    e.preventDefault();
  });

  div.addEventListener('drop', function(e) {
    e.stopPropagation();
    e.preventDefault();
    var files = e.dataTransfer.files;
    var reader = new FileReader();
    var myFile = files[0];
    reader.onload = function(e2){
      var fileContent = e2.target.result;
      var name = myFile.name;
      parseAndUpload(name, fileContent);
    };
    reader.readAsText(myFile);
  });

}

function parseAndUpload(name, content){
  //We're not going to check db/coll names explicitly, just that uploaded data
  //matches to expected block names. In particular, we warn if file contains "too many"
  //unknown keys, but offer to proceed with known ones

  if(!content) return;
  var dataObj = identifyJsonAndChain(content);
  //Now we know what format our data is in, and how to get to the actual data
  //DataObj has a fmt and a data field. Data contains parsed but not altered data
  //fmt contains a dict in form { fmt : 0, depth : 1, maxDepth : 4, chain: []};

  var data = dataObj.data;

  //Unpack the actual data using the info in fmt
  console.log(dataObj.fmt.chain);
  for(var item of dataObj.fmt.chain){
    console.log(item, data);
    data = data[item];
  }
  console.log(data, dataObj.fmt);

  //Get keys from page and file and find overlap
  var keysInFile = extractKeys(dataObj);
  var keysInPage = getBoxKeys(mainBlockList);
  var sharedKeys = keysInFile.filter(function (el){
          return keysInPage.indexOf(el) !== -1;
        });
  var unknownKeys = keysInFile.filter(function (el){
          return keysInPage.indexOf(el) === -1;
        });

  var cont = false;
  if(sharedKeys.length === 0){
    alert("No recognized keys in file, aborting upload.");
  }else if(unknownKeys.length > 0){
    cont = confirm("Found unrecognized keys: "+unknownKeys.join(';')+" ignore and continue?");
  }else{
    cont = true;
  }
  if( !cont) return;

  uploadItemsToPage(sharedKeys, data, dataObj.fmt.fmt);

}

function identifyJsonAndChain(text){
  //Formats:
  // 1: full downloaded diff
  // 2: Orph style, a list of name, data
  // 3: Key-data styled
  //Chain is the series of keys (if any) to reach expected format, and should be read backwards
  //E.g. may come wrapped in an extra dict layer
  var fmtInfo = { fmt : 0, depth : 1, maxDepth : 4, chain: []};
  var textAsJson = JSON.parse(text);
//  textAsJson = {"a": "nothing", "one" : {"three": "ab", "two": textAsJson}};
//  textAsJson = {a: {b: textAsJson}};
  //textAsJson = {"mykey":textAsJson[0].data}
  fmtInfo = checkAtLevel(textAsJson, fmtInfo);
  //Chain runs deep to shallow, want to address from start to end
  fmtInfo.chain.reverse();
  return {fmt: fmtInfo, data : textAsJson};
}

function checkAtLevel(textAsJson, fmtInfo){
  //console.log(fmtInfo, textAsJson);
  var currText = textAsJson;
  if(fmtInfo.fmt == 0 && fmtInfo.depth < fmtInfo.maxDepth && currText){
    if(currText.db == pageId.db && currText.table == pageId.table && currText.diffs){
      fmtInfo.fmt = 1;
    }else if(currText.name && currText.data){
      fmtInfo.fmt = 2;
    }else if(currText instanceof Array && currText.length > 0 && currText[0].name && currText[0].data){
      fmtInfo.fmt = 2;
    }else{
      var keys = [];
      var key;
      try{
        keys = Object.keys(currText);
        if(typeof currText === "string" || currText instanceof String) keys = [];
      }catch(error){
      }
      for(key of keys){
        //Is vital that these are triple-equals (or double not eq) because we distinguish absent from present-but-null
        if(currText[key] && currText[key].type !== undefined && currText[key].example !== undefined && currText[key].description !== undefined){
          fmtInfo.fmt = 3;
          break;
        }
      }
      if(fmtInfo.fmt == 0){
        fmtInfo.depth += 1;
        for(key of keys){
          if(fmtInfo.fmt == 0) fmtInfo = checkAtLevel(currText[key], fmtInfo);
          if(fmtInfo.fmt != 0){
            fmtInfo.chain.push(key);
            break;
          }
        }
      }
    }
    fmtInfo.depth -= 1;
    return fmtInfo;
  }else{
    return fmtInfo;
  }
}

function extractKeys(dataObj){
  //Extract the key names according to actual format

  var data = dataObj.data;
  var thing, key, ind;
  for(var item of dataObj.fmt.chain){
    data = data[item];
  }

  var keys = [];
  if(dataObj.fmt.fmt == 1){
    //Keys are all the things under the "item" key for each dict in list
    data = data.diffs;
    for(thing of data){
      keys.push(thing.item);
    }
  }else if(dataObj.fmt.fmt == 2){
    for(thing of data){
      keys.push(thing.name);
    }
  }else if(dataObj.fmt.fmt == 3){
    keys = Object.keys(data);
  }

  return keys;

}

function uploadItemsToPage(keys, data, fmt){
  //Fill the boxes named by keys from data, assuming format is fmt type
  //Fmt type 1 means {item:, field, content}
  //Others are both name:{type, description, example}
  //Keys should contain any keys wished to include, they MUST be valid page keys, but need not exist in data
  var item, blockName, block;
  if(fmt === 1){
    for(item of data.diffs){
      if(keys.indexOf(item.item) !== -1){
        blockName = createBoxName(item.item, item.field);
        block = mainBlockList.getBlock(blockName);
        updateBoxAndBlock(block, item.content);
      }
    }
  }else if(fmt === 2 || fmt === 3){
    for(item of data){
      if(keys.indexOf(item.name) !== -1){
        for(var key of table_fields){
          blockName = createBoxName(item.name, key);
          block = mainBlockList.getBlock(blockName);
          updateBoxAndBlock(block, item.data[key]);
        }
      }
    }
  }else{
    console.log("Format unknown or zero");
  }

}

function updateBoxAndBlock(block, content){
    //Handle updates page and block with content

    //If content is null, do nothing. To blank a field, set to empty string
    if(!content && content !=="") return;

    block.newtext = content;
    if(block.newtext != block.text){
      block.edited = true;
    }else{
      block.edited = false;
    }
    $(escape_jq(block.docElementId)).val(content);
    fitToText(block.docElementId);
}
