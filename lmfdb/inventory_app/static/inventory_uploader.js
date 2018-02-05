

function importJson(){
  //Upload either by file drag-and-drop below the line, or typing/pasting text into the input and clicking the continue button

  //Disable drag-drop loading on window
  window.addEventListener('dragover', function(e) {
    e.preventDefault();
  },false);

  window.addEventListener('drop', function(e) {
    e.preventDefault();
  },false);

  var div = document.getElementById("fileDropper");
  div.innerHTML = "<hr> Drag a file here, or type/paste into the box and click continue.<br>";

  var uploadText = document.createElement("textarea");
  div.appendChild(uploadText);

  var contButton = document.createElement("button");
  contButton.title = "Continue";
  contButton.innerHTML = "Continue";

  div.appendChild(contButton);

  div.addEventListener('dragover', function(e) {
    e.stopPropagation();
    e.preventDefault();
  });

  div.addEventListener('drop', function(e) {
    e.stopPropagation();
    e.preventDefault();
    var files = e.dataTransfer.files;
    console.log(files);
    var reader = new FileReader();
    var myFile = files[0];
    reader.onload = function(e2){
      var fileContent = e2.target.result;
      var name = myFile.name;
      parseAndUpload(name, fileContent);
    }
    reader.readAsText(myFile);
  });

}

function parseAndUpload(name, content){

  identifyJsonAndChain(content);

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
  textAsJson = {"mykey":textAsJson[0].data}
  console.log(textAsJson);
  fmtInfo = checkAtLevel(textAsJson, fmtInfo);
  console.log(fmtInfo, fmtInfo.chain, fmtInfo.fmt !=0);
  var data = textAsJson;
  for(item in fmtInfo.chain){
    data = data[item];
  }
  console.log(data);
}

function checkAtLevel(textAsJson, fmtInfo){
  console.log(fmtInfo);
  var currText = textAsJson;
  if(fmtInfo.fmt == 0 && fmtInfo.depth < fmtInfo.maxDepth && currText){
    if(currText.db == pageId.db && currText.collection == pageId.collection && currText.diffs){
      fmtInfo.fmt = 1;
    }
    else if(currText.name && currText.data){
      fmtInfo.fmt = 2;
    }else{
      var keys = [];
      try{
        keys = Object.keys(currText);
        if(typeof currText === "string" || currText instanceof String) keys = [];
      }catch(error){
      }
      for(var key of keys){
        //Is vital that these are triple-equals (or double not eq) because we distinguish absent from present-but-null
        if(currText[key] && currText[key].type !== undefined && currText[key].example !== undefined && currText[key].description !== undefined){
          fmtInfo.fmt = 3;
          break;
        }
      }
      if(fmtInfo.fmt == 0){
        fmtInfo.depth += 1;
        for(var key of keys){
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
