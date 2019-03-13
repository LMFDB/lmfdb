/*jshint esversion: 6 */

function rescanAll(db){

  var info = {'db':db, 'table':null};
  console.log(info);
  cont = confirm('This action may take some time. Are you sure?');
  if(cont){
    sendRescanRequest(info, scrapeDest);
  }
}

function rescan(db, table){

  var info = {'db':db, 'table':table};
  console.log(info);
  cont = confirm('This action may take some time. Are you sure?');
  if(cont){
    sendRescanRequest(info, scrapeDest);
  }
}

function sendRescanRequest(info, dest){

  var responseText = JSON.stringify({'data':info});

  var XHR = new XMLHttpRequest();
  XHR.open('POST', dest);
  XHR.setRequestHeader('Content-Type', 'text/plain');

  XHR.addEventListener('load', function(event) {
    //On successful response, either redirect to success page or
    //show lock message
    console.log(XHR.response);
    var response = JSON.parse(XHR.response);
    if(response.locks){
      alert('Scraping already in progress on (some of) requested table(s). Try again later.');
    }else if(response.err){
      alert('Error submitting request. Please try again.');
    }else{
      window.location.href=response.url;
    }
  });

  // Define what happens in case of error
  XHR.addEventListener('error', function(event) {
    alert('Error submitting request. Please try again.');
  });

  XHR.send(responseText);
}

function startProgressMeter(){
  getProgress();
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
    checkCompletion(data);
    tickMeter(data);
    showProgress(data);
  });

  XHR.send('');
}

function tickMeter(progress){
  //Queue next progress check if needed
  if(isComplete(progress)) return;

  waitTime = waitTime * 2;
  if(waitTime >= maxWait) waitTime = maxWait;
  setTimeout(getProgress, waitTime*1000);
}

function checkCompletion(progress){

   if(isComplete(progress)) addSummary();
}

function showProgress(progress){
  var span = document.getElementById('progressSpan');
  console.log(progress);
  span.innerHTML = progress.progress_in_current+"% done on table "+progress.curr_table+" of "+progress.n_tables;
}

function isComplete(progress){

//  if(progress['curr_table'] == progress['n_tables'] && progress['progress_in_current'] >= 100) return true;
  if(progress.progress_in_current >= 100) return true;
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
  var db = Object.keys(data)[0];
  h2.innerHTML = 'Scan of database <b>' + db + '</b> complete</br>';
  div.appendChild(h2);

  var key, keyDiv;
  for(var table in data.orphan){
    var innerDiv = document.createElement('div');
    h2 = document.createElement('h2');
    h2.innerHTML = 'Table ' + table + ':</br>';
    innerDiv.appendChild(h2);
    if(data.gone[table] == {}){
      keyDiv = document.createElement('div');
      keyDiv.innerHTML = 'The following keys were removed:</br>';
      for(key of data.gone[table]){
        keyDiv.innerHTML = keyDiv.innerHTML + key +'</br>';
      }
      innerDiv.appendChild(keyDiv);
    }

    if(data.orphan[table]){
      keyDiv = document.createElement('div');
      keyDiv.innerHTML = 'The following keys were removed and had data:</br>';
      for(key of data.orphan[table]){
        keyDiv.innerHTML = keyDiv.innerHTML + key.name + '</br>';
      }
      innerDiv.appendChild(keyDiv);
    }
    div.appendChild(innerDiv);
  }
  if(! data.gone && !data.orphan){
    var tmpDiv = document.createElement('div');
    tmpDiv.innerHTML = "Nothing to report";
    div.appendChild(tmpDiv);
  }else{
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
    div.appendChild(butt);
  }
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
