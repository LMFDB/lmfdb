
function rescanAll(db){

  var info = {'db':db, 'coll':null};
  console.log(info);
  sendRescanRequest(info, scrapeDest);

}

function rescan(db, coll){

  var info = {'db':db, 'coll':coll};
  console.log(info);
  sendRescanRequest(info, scrapeDest);

}

function sendRescanRequest(info, dest){

  var responseText = JSON.stringify({'data':info});

  var XHR = new XMLHttpRequest();
  XHR.open('POST', dest);
  XHR.setRequestHeader('Content-Type', 'text/plain');

  XHR.addEventListener('load', function(event) {
    //On success redirect to a success page
    console.log(XHR.response);
    var response = JSON.parse(XHR.response);
    console.log(response);
    window.location.href=response.url;
  });

  // Define what happens in case of error
  XHR.addEventListener('error', function(event) {
    alert('Error submitting edits. Please try again.');
  });

  XHR.send(responseText);
}

function getProgress(){

  var current_url = window.location.href;
  var data_url = current_url + 'monitor';
  var XHR = new XMLHttpRequest();
  XHR.open('GET', data_url);
  XHR.setRequestHeader('Content-Type', 'text/plain');

  XHR.addEventListener('load', function(event) {
    //On success fill in progress
    var data = JSON.parse(XHR.response);
    showProgress(data);
  });

  XHR.send('');
}

function isComplete(progress){

//  if(progress['curr_coll'] == progress['n_colls'] && progress['progress_in_current'] >= 100) return true;
  if(progress['progress_in_current'] >= 100) return true;
  return false;
}

function addSummary(){

  var div = document.getElementById('meter');
  div.classList.add('hidden');

  fetchScrapeSummaryData();

}

function fillSummary(data){

  var div = document.getElementById('summaryDiv');

  var h2 = document.createElement('h2');
  h2.innerHTML = 'Scan of database <b>' + data.db + '</b> complete</br>';
  div.appendChild(h2);

  for(var coll in data.orphan){
    var innerDiv = document.createElement('div');
    h2 = document.createElement('h2');
    h2.innerHTML = 'Collection ' + coll + ':</br>';
    innerDiv.appendChild(h2);

    if(data.gone[coll] == {}){
      var keyDiv = document.createElement('div');
      keyDiv.innerHTML = 'The following keys were removed:</br>';
      for(var key of data.gone[coll]){
        keyDiv.innerHTML = keyDiv.innerHTML + key +'</br>';
      }
      innerDiv.appendChild(keyDiv);
    }

    if(data.orphan[coll]){
      var keyDiv = document.createElement('div');
      keyDiv.innerHTML = 'The following keys were removed and had data:</br>';
      for(var key of data.orphan[coll]){
        keyDiv.innerHTML = keyDiv.innerHTML + key.name + '</br>';
      }
      innerDiv.appendChild(keyDiv);
    }
  }
  var butt = document.createElement('button');
  butt.innerHTML = "Download All Data";
  butt.title = "Download all invalidated key data as json";
  var filename = 'Orphan_keys_'+data.db+'.json';
  butt.onclick = (function() {
    filename = filename;
    data = JSON.stringify(data.orphan, null, 4);
    return function() {
      this.blur();
      saveTextAsFile(data, filename, 'application/json');
    };
  })();
  innerDiv.appendChild(butt);

  div.appendChild(innerDiv);

}

function fetchScrapeSummaryData(){

  var current_url = window.location.href;
  var data_url = current_url + 'complete';
  var XHR = new XMLHttpRequest();
  XHR.open('GET', data_url);
  XHR.setRequestHeader('Content-Type', 'text/plain');

  XHR.addEventListener('load', function(event) {
    //On success fill in progress
    var data = JSON.parse(XHR.response);
    fillSummary(data);
  });

  XHR.send('');
}
