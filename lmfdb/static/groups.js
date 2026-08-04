
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

  // The following is to make two graphs for each entry in gdatalist
  // which have two sets of coordinates
  // console.log(gdatalist[0]);
  for(var j=0; j<gdatalist.length; j++) {
    var order_lookup = new Map();
    var simpleorder = new Map();
    for (var k=0; k < orderdata[j].length; k++) {
      var trip = orderdata[j][k];
      order_lookup.set(trip[0], [trip[1], trip[2]]);
      simpleorder.set(trip[0], [k,0]);
    }
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
      // x-coord for by order is in 7
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

  renderer = new Renderer(document.getElementById(canv),ourg, {});

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

function mytogglevert(use_big_on_top) {
  for(var g=0; g < glist.length; g++) {
    if (!glist[g] || glist[g].layoutMinY == undefined) continue;
    var miny = glist[g].layoutMinY;
    var maxy = glist[g].layoutMaxY;
    for(var i=0; i< sdiagram.graph.nodes.length; i++) {
      glist[g].nodes[i].layoutPosY = maxy + miny - glist[g].nodes[i].layoutPosY;
    }
  }
  sdiagram.setSize();
  sdiagram.draw();
}

function mytoggleheights(use_order_for_height) {
  var who_old = whoisshowing;
  if (use_order_for_height && (whoisshowing < 4)) {
    whoisshowing += 4;
  }
  if ((! use_order_for_height) && whoisshowing > 3) {
    whoisshowing -= 4;
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

var styles=['subgroup_diagram', 'subgroup_profile', 'subgroup_autdiagram', 'subgroup_autprofile', 'normal_diagram', 'normal_profile', 'normal_autdiagram', 'normal_autprofile'];
var mode_pairs = [['subgroup', 'normal'], ['', 'aut'], ['diagram', 'profile']];
function select_subgroup_mode(mode) {
  var cls, thismode, opposite_mode, piece;
  cls = "";
  for (var i = 0; i < mode_pairs.length; i++) {
    for (var j = 0; j < 2; j++) {
      thismode = mode_pairs[i][j];
      if (thismode == mode) {
        opposite_mode = mode_pairs[i][1-j];
        if ($("button.sub_" + mode).hasClass("sub_active")) {
          return; // already active
        }
        piece = mode;
        break;
      }
      if ($("button.sub_" + thismode).hasClass("sub_active")){
        piece = thismode;
      }
    }
    cls += piece;
    if (i == 0) {
      cls += "_";
    }
  }
  $("button.sub_" + mode).removeClass("sub_inactive");
  $("button.sub_" + mode).addClass("sub_active");
  $("button.sub_" + opposite_mode).removeClass("sub_active");
  $("button.sub_" + opposite_mode).addClass("sub_inactive");
  show_info(cls);
}

var heightstyle='div'; // alternative is 'order'
function show_info(style) {
  for (var i = 0; i < styles.length; i++) {
    $('div.' + styles[i]).hide();
  }
  $('div.'+style).show();
  if (style.endsWith("diagram")) {
    whoisshowing = 0;
    if (style.endsWith("autdiagram")) {
      whoisshowing += 1;
    }
    if (heightstyle=='order') {
      whoisshowing += 4;
    }
    if (style.startsWith("normal")) {
      whoisshowing += 2;
    }
    sdiagram.newgraph(glist[whoisshowing]);
    sdiagram.setSize();
    sdiagram.draw();
  }
  for (var i = 0; i < styles.length; i++) {
    $('button.' + styles[i]).show();
  }
}
function toggleheight()
{
  if (heightstyle=='div') {
    heightstyle = 'order';
  } else {
    heightstyle = 'div';
  }
  mytoggleheights($("#orderForHeight").prop('checked'));
}



