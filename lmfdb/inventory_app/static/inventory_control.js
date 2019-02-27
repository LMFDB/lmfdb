/*jshint esversion: 6 */

function sendControlRequest(action){

  var conf = verifyProceed(action);
  if(conf){
    var callback = getCallback(action);
    sendToServer(action, callback);
  }
}

function verifyProceed(action){
  //All actions will be confirmed by popup except the following list:
  //ONLY put things here that are cheap and/or frequent and
  //you don't want to annoy user with too many dialogs

  var noConf = ['mark_gone', 'download_orphans'];
  if(noConf.indexOf(action) != -1){
    return true;
  }else{
    conf = confirm('This action may take some time or alter inventory data. Are you sure?' );
    return conf;
  }
}
function saveJSON(data){
  console.log(data);
  saveTextAsFile(JSON.stringify(data), 'ExportedData.json');
}
function getCallback(action){

  var doDownload = ['download_orphans'];
  if(doDownload.indexOf(action) != -1){
    return saveJSON;
  }
  return null;
}

function sendToServer(action, callback=null){

  var info = {'action':action};
  var responseText = JSON.stringify(info);
  var XHR = new XMLHttpRequest();
  XHR.open('POST', dest);
  XHR.setRequestHeader('Content-Type', 'text/plain');

  XHR.addEventListener('load', function(event) {
    //On response alert with answer
    var response = JSON.parse(XHR.response);
    console.log(response, response.data, callback);
    if(callback) callback(response.data);
    if(response.err){
      alert('An error occurred processing request. '+response.reply);
    }else{
      alert('Operation Completed!');
    }
  });
  // Define what happens in case of error
  XHR.addEventListener('error', function(event) {
    alert('Error submitting request. Please try again.');
  });
  XHR.send(responseText);
}
