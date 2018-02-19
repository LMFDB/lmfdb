
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

function showSummary(){

  var div = document.getElementById('spinner');
  div.classList.add('hidden');

  div = document.getElementById('summaryDiv');

  var span = document.createElement('span');
  span.innerHTML='DONE!</br>';
  div.appendChild(span);
  span = document.createElement('span');
  span.innerHTML = 'The following keys were removed:</br>';
  div.appendChild(span);

  span = document.createElement('span');
  span.innerHTML = 'Download this data...:</br>';
  div.appendChild(span);


}
