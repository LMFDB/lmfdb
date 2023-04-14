
function highlight_group(evt) {
    var subseries = $(this).attr("data-sgseries");
    var subid = $(this).attr("data-sgid");
    if (subseries == null) {
        $(`span[data-sgid="${subid}"]`).addClass("activesubgp");
        if (typeof sdiagram !== "undefined") {sdiagram.highlight(subid);}
        if (typeof sautdiagram !== "undefined") {sautdiagram.highlight(subid);}
    } else {
        $(`span[data-sgseries="${subseries}"]`).addClass("activesubgp");
        subids = subseries.split("-");
        for (i = 0; i < subids.length; i++) {
            sid = subids[i];
            $(`span[data-sgid="${sid}"]`).not('.series').addClass("activesubgp");
            if (typeof sdiagram !== "undefined") {sdiagram.highlight(subid);}
            if (typeof sautdiagram !== "undefined") {sautdiagram.highlight(subid);}
        }
    }
}

function unhighlight_group(evt) {
    var subseries = $(this).attr("data-sgseries");
    var subid = $(this).attr("data-sgid");
    if (subseries == null) {
        $(`span[data-sgid="${subid}"]`).removeClass("activesubgp");
        if (typeof sdiagram !== "undefined") {sdiagram.unhighlight(subid);}
        if (typeof sautdiagram !== "undefined") {sautdiagram.unhighlight(subid);}
    } else {
        $(`span[data-sgseries="${subseries}"]`).removeClass("activesubgp");
        subids = subseries.split("-");
        for (i = 0; i < subids.length; i++) {
            sid = subids[i];
            $(`span[data-sgid="${sid}"]`).not('.series').removeClass("activesubgp");
            if (typeof sdiagram !== "undefined") {sdiagram.unhighlight(subid);}
            if (typeof sautdiagram !== "undefined") {sautdiagram.unhighlight(subid);}
        }
    }
}

function showsubinfo(node, ambient) {
  $.get(`/Groups/Abstract/subinfo/${ambient}/${node.value}`, 
        function(data){
          $(".selectedsub").map(function() { 
            this.innerHTML= data; 
            renderMathInElement(this, katexOpts);
            return;
          });
          $(".subgp").hover(highlight_group, unhighlight_group);
        });
}

function clearsubinfo() {
  $(".selectedsub").map(function() { 
    return this.innerHTML='Click on a subgroup in the diagram to see information about it.';
  });
}

function make_sdiagram(canv, ambient, gdatalist, orderdata, num_layers) {
  // gdatalist is a list of [nodes, edges, orders]
  // Now make a list of graphs
  var glist = Array(2 * gdatalist.length);
  var order_lookup = new Map();
  var simpleorder = new Map();
  for (var k=0; k < orderdata.length; k++) {
    var trip = orderdata[k];
    order_lookup.set(trip[0], [trip[1], trip[2]]);
    simpleorder.set(trip[0], [k,0]);
  }
  var order_list = orderdata.map(function(z) {return (z[0]);});
  // The following is to make two graphs for each entry in gdatalist
  // which have two sets of coordinates
  // console.log(gdatalist[0]);
  for(var j=0; j<gdatalist.length; j++) {
    var nodes, edges;
    [nodes, edges] = gdatalist[j];
    glist[j] = new Graph(ambient);
    if(gdatalist[j].length>0) {
      // x-coord for by # primes is in 6
      glist[j].addNodes(nodes, order_lookup, 6);
      for(var k=0, edge; edge=edges[k]; k++) {
        glist[j].addEdge(edge[0],edge[1]);
      }
      var layout = new Layout(glist[j]);
      layout.layout();
    }
    // Now repeat for the other graph
    jj = gdatalist.length+j;
    glist[jj] = new Graph(ambient);
    //glist[jj].setOrderBorder(100, -100);
    if(gdatalist[j].length>0) {
      // x-coord for by # primes is in 7
      glist[jj].addNodes(nodes, simpleorder, 7);
      for(var k=0, edge; edge=edges[k]; k++) {
        glist[jj].addEdge(edge[0],edge[1]);
      }
      var layout = new Layout(glist[jj]);
      layout.layout();
    }
  }
  ourg = glist[glist.length-1];
  ambientlabel=ambient;

  renderer = new Renderer(document.getElementById(canv),ourg, {'orderlist': order_list});

  // Need to call Event.Handler here
  new EventHandler(renderer, {
    updateNodeDrag: function(node, event) {
      renderer.draw();
    }
  });
  newheight(renderer, num_layers);
  renderer.setSize();
  // The renderer is stored in sdiagram by the web page
  return [renderer,glist];
}

function mytoggleheights(use_order_for_height) {
  var who_old = whoisshowing;
  if (use_order_for_height && (whoisshowing < 2)) {
    whoisshowing += 2;
  } 
  if ((! use_order_for_height) && whoisshowing > 1) {
    whoisshowing -= 2;
  }
  if(who_old != whoisshowing) {
    glist[whoisshowing].highlit = null;
    for(var i=0; i< sdiagram.graph.nodes.length; i++) {
      glist[whoisshowing].nodes[i].selected = glist[who_old].nodes[i].selected;
    }
  }
  sdiagram.newgraph(glist[whoisshowing]);
  sdiagram.setSize();
  sdiagram.draw();
}

function getpositions() {
  var mylist="[\""+ambientlabel+"\",[";
  for (var i = 0; i < ourg.nodes.length; i++) {
    mylist +=  i>0 ? ',' : '';
    mylist +="[\""+ourg.nodes[i].value+"\","+ ourg.nodes[i].layoutPosX+"]";
  }
  mylist += "]]";
  var mydiv = document.getElementById("positions");
  mydiv.innerHTML = type+"<br>"+mylist;

  return mylist;
}
