/*  Graph JavaScript framework, version 0.0.1
 *  (c) 2006 Aslak Hellesoy <aslak.hellesoy@gmail.com>
 *  (c) 2006 Dave Hoover <dave.hoover@gmail.com>
 *
 *  Ported from Graph::Layouter::Spring in
 *    http://search.cpan.org/~pasky/Graph-Layderer-0.02/
 *  The algorithm is based on a spring-style layouter of a Java-based social
 *  network tracker PieSpy written by Paul Mutton E<lt>paul@jibble.orgE<gt>.
 *
 *  Removed prototype dependency, added images for nodes and layered
 *  layout, John Jones.
 *
 *  Graph is freely distributable under the terms of an MIT-style license.
 *  For details, see the Graph web site: http://dev.buildpatternd.com/trac
 *
 /*--------------------------------------------------------------------------*/

/* Make some parts global variables 

   These are needed for code which gets positions
   We still need to adjust this bit to the difference between regular
   and aut diagrams.
*/
var ourg;
var ambientlabel;
var whoisshowing;
var type="C"; // C for conjugacy class, A for up to aut

/* The rest of the global variables are for debugging or page colors,
   so they should be ok when 2 diagrams are on the page */

/* For debugging, it can hold a value to be inspected in the console */
var dbug = '';
var dbug2 = '';

// Highlight colors: these were for testing
var selected_color = 'deepskyblue';
var highlit_color = 'yellowgreen';

// Figure out the highlight color for activesubgp
var classes = document.styleSheets[0].rules || document.styleSheets[0].cssRules;
for (var j = 0; j < classes.length; j++) {
  if (classes[j].selectorText == 'span.activesubgp') {
    var classtext = (classes[j].cssText) ? classes[j].cssText : classes[j].style.cssText;
    highlit_color = classtext.replace(/^.*rgb/,"rgb");
    highlit_color = highlit_color.replace(/\).*$/,")");
    //highlit_color = highlit_color.replace(/;/,"");
  }
}

// This is moved later because of some issue with load order
// selected_color = $("#group-diagram-selected").css('background-color');

var can_move_vertically = false;

Graph = class {
  constructor(ambient) {
    this.nodeSet = {};
    this.nodes = [];
    this.edges = [];
    this.ambient = ambient;
    this.highlit = null;
    this.order_border_x = 0;
    this.order_border_y = 0;
  }

  setOrderBorder(obx,oby) {
    this.order_border_x = obx;
    this.order_border_y = oby;
  }

  addNode(value, posnx, order_lookup, options) {
    var key = value[1].toString();
    var node = this.nodeSet[key];
    //dbug = [value, posn, orders, this.nodes, node];
    //dbug = [key, this.nodeSet, node, this.nodeSet[key]];
    if(node == undefined) {
      node = new Node(key);
      this.nodeSet[key] = node;
      this.nodes.push(node);
      options['raw'] = value[2];
      node.label = value[0];
      node.ccsize = value[3];
      node.level = order_lookup.get(value[4]); // a pair
      node.image = new Image();
      node.image.src = value[5];
      node.key = key;

      node.posn = posnx;
      node.setOptions(options);
      //console.log(options['raw']);
    }
    return node;
  }

  addNodes(values, order_lookup, xlocation) {
    for(var j=0, item; item = values[j]; j++) {
      var myx = Math.max(j, item[xlocation]);
	  //console.log("Node ", myx, " ", item);
      this.addNode(item, myx, order_lookup, {});
    }
  }

  // Uniqueness must be ensured by caller
  addEdge(source, target) {
    var s = this.addNode(['',source,'']);
    var t = this.addNode(['',target,'']);
    var edge = {source: s, target: t};
    this.edges.push(edge);
    return edge;
  }
}

class Node {
  constructor(value) {
    this.value = value;
    this.style = {};
    this.selected = false;
    this.highlit = false;
    this.label = '';
    this.image = null;
    this.level = [0,0];
  }

  setOptions(options) {
    this.options = {};
    this.options.type = 'normal';
    for (var k in options) {
      this.options[k] = options[k];
    }
  }

  highlight() {
    this.highlit = true;
  }

  unhighlight() {
    this.highlit = false;
  }

  select() {
    this.selected = true;
  }

  unselect() {
    this.selected = false;
  }
}

class Renderer {
  constructor(element, graph, options) {
    this.element = element;
    this.graph = graph;
    this.setOptions(options);

    this.ctx = element.getContext("2d");
    this.radius = 20;  // if nodes were circles, this would be their radius
    this.arrowAngle = Math.PI/10;

    this.setSize();
  }

  setSize() {
    this.factorX = (this.ctx.canvas.width - 2 * this.radius - this.graph.order_border_x) / (this.graph.layoutMaxX - this.graph.layoutMinX+1);
    this.factorY = (this.ctx.canvas.height - 2 * this.radius - this.graph.order_border_y) / (this.graph.layoutMaxY - this.graph.layoutMinY+1);
    this.reposition();
  }


  setOptions(options) {
    this.options = {
      arrowAngle: Math.PI/10,
      //font: tahoma8,
      edgeColor: 'blue'
    }
    for (var k in options) {
      this.options[k] = options[k];
    }
  }

  // virtual coordinates to pixels
  translate(point) {
    return [
      (point[0] - this.graph.layoutMinX) * this.factorX + this.radius + this.graph.order_border_x,
      (point[1] - this.graph.layoutMinY) * this.factorY + this.radius + this.graph.order_border_y
    ];
  }

  // pixels to virtual coordinates
  untranslate(point) {
    return [
      (point[0] - this.radius - this.graph.order_border_x)/ this.factorX +this.graph.layoutMinX,
      (point[1] - this.radius - this.graph.order_border_y)/ this.factorY +this.graph.layoutMinY
    ];
  }

  rotate(point, length, angle, wid, ht) {
    var dx = length * Math.cos(angle);
    var dy = length * Math.sin(angle);
    //var sgn = length/Math.abs(length);
    //var dx,dy;
    //var tangle = Math.tan(angle);
    //var width = wid || 16;
    //var height = ht || 12;
    //var ssin = Math.sin(angle)< 0 ? -1 : 1;
    //var scos = Math.cos(angle)< 0 ? -1 : 1;
    //    console.log([tangle,ht, wid, ht/wid]);
    //if(Math.abs(angle-Math.PI/2)< .1 || tangle < height/width) {
    //console.log(angle);
    //dx = scos*sgn*(width/2+5);
    //dy = ssin*dx * tangle;
    //} else {
    //console.log(`2nd ${angle}`);
    //dy = scos*sgn*(height/2+5);
    //dx = ssin*dy/tangle;
    //}
    return [point[0]+dx, point[1]+dy];
  }

  newgraph(g) {
    this.graph = g;
    this.reposition();
    this.draw();
    ourg = g;
    var found = false;
    for (var i = 0; i < g.nodes.length; i++) {
      if(g.nodes[i].selected) {
        showsubinfo(g.nodes[i], g.ambient);
        found = true;
      }
    }
    if (! found) {
      clearsubinfo();
    }
  }

  clear() {
    this.ctx.clearRect(0,0, this.element.width, this.element.height);
  }

  draw() {
    this.ctx.clearRect(0,0, this.element.width, this.element.height);
    for (var i = 0; i < this.graph.nodes.length; i++) {
      this.drawNode(this.graph.nodes[i]);
    }
    for (var i = 0; i < this.graph.edges.length; i++) {
      this.drawEdge(this.graph.edges[i]);
    }
    if(whoisshowing > 1) { // heights are by order
      var orderlist = this.options.orderlist;
      for (var i = 0; i<orderlist.length; i++) {
        var coords = this.translate([this.graph.layoutMinX+150, -10*(i-1)-6.5]);
        coords[0] -= this.graph.order_border_x;
        //this.drawOrder(orderlist[i], coords);
      }
    }
  }

  drawOrder(ord, posn) {
    this.ctx.moveTo(0,0);
    this.ctx.strokeStyle = 'black';
    this.ctx.fillStyle = 'black';
    this.ctx.font = "16px Arial";
    var textwidth = this.ctx.measureText(ord).width;
    this.ctx.fillText(ord, posn[0]-textwidth, posn[1]);
  }

  drawNode(node) {
    var point = this.translate([node.layoutPosX, node.layoutPosY]);

    node.style.position = 'absolute';
    node.style.top      = point[1] + 'px';
    node.style.left     = point[0] + 'px';

    this.ctx.moveTo(0,0);
    this.ctx.strokeStyle = 'black';
    this.ctx.fillStyle = 'black';
    this.ctx.font = "10px Arial";
    var ctxt = this.ctx;
    var img = node.image;

    var textwidth = ctxt.measureText(node.ccsize).width;
    if(! img.complete) {
      img.onload = function() {
        ctxt.drawImage(img,node.center[0]-0.5*img.width,node.center[1]-4);
        if(node.ccsize>1) {
          ctxt.fillText(node.ccsize, node.center[0]-0.5*img.width-textwidth, 12+node.center[1]);
        };
      };
    } else {
      var lft = node.center[0]-0.5*img.width;

      if(node.selected) {
        // Just set it here, used to be at the start
        selected_color = $("#group-diagram-selected").css('background-color');

        ctxt.fillStyle= selected_color;
        ctxt.fillRect(lft-2, node.center[1]-6, img.width+2, img.height+3);
      } else if(node.highlit) {
        ctxt.fillStyle= highlit_color;
        ctxt.fillRect(lft-2, node.center[1]-6, img.width+2, img.height+3);
      }
      ctxt.drawImage(node.image,lft,node.center[1]-4);
      this.ctx.strokeStyle = 'black';
      this.ctx.fillStyle = 'black';
      if(node.ccsize>1) {
        ctxt.fillText(node.ccsize, node.center[0]-0.5*img.width-textwidth, 12+node.center[1]);
      }
    }
  }

  drawEdge(edge) {
    var source = edge.source.center;
    var target = edge.target.center;

    var tan = (target[1] - source[1]) / (target[0] - source[0]);
    var extra = Math.abs(tan)< 0.7 ? 4 : -4;
    var theta = Math.atan(tan);
    if(source[0] <= target[0]) {theta = Math.PI+theta}
    var img = edge.source.image
    source = this.rotate(source, -this.radius-extra, theta, img.width, img.height);
    target = this.rotate(target, this.radius+extra, theta, img.width, img.height);

    // draw the edge
    this.ctx.strokeStyle = 'grey';
    this.ctx.fillStyle = 'grey';
    this.ctx.lineWidth = 1.0;
    this.ctx.beginPath();
    this.ctx.moveTo(source[0], source[1]);
    this.ctx.lineTo(target[0], target[1]);
    this.ctx.stroke();
  }

  nodeAt(point) {
    var node = undefined;
    var mind = Infinity;
    var rsquared = this.radius*this.radius;
    for (var i = 0, n; n=this.graph.nodes[i]; i++) {
      var np = this.translate([n.layoutPosX, n.layoutPosY]);
      var dx = point[0] - np[0];
      var dy = point[1] - np[1];
      var d = dx * dx + dy * dy;
      if(d < mind && d <= rsquared) {
        mind = d;
        node = n;
      }
    }
    return node;
  }

  unselectNodes() {
    for (var i = 0, node; node= this.graph.nodes[i]; i++) {
      node.unselect();
    }
  }

  selectedSub() {
    for (var i = 0, node; node= this.graph.nodes[i]; i++) {
      if(node.selected) { return(node); }
    }
    //alert('Could not find selected subgroup from diagram');
    return(null);
  }

  reposition() {
    for (var i = 0; i < this.graph.nodes.length; i++) {
      var node = this.graph.nodes[i];
      node.center = this.translate([node.layoutPosX, node.layoutPosY]);
      //console.log("newcenter="+newcenter);
    }
  }

  highlight(subid) {
    var node = this.graph.nodeSet[subid];
    if(node) {
      node.highlight();
      this.graph.highlit = node;
      this.draw();
    }
  }

  unhighlight(subid){
    var node = this.graph.nodeSet[subid];
    if(node) {
      node.unhighlight();
      this.graph.highlit = null;
      this.draw();
    }
  }
}

class Layout {
  constructor(graph) {
    this.graph = graph;
    //this.iterations = 10;
    this.maxRepulsiveForceDistance = 200;
    this.k = 3; // 2;
    this.c = 0.01; //0.01;
    this.maxVertexMovement = 10;
    this.margin = 5;
    this.doiter = false;
  }

  setiter(val) {
    this.doiter=val;
  }

  islinear() {
    var g = this.graph;
    if(g.nodes.length == g.edges.length+1) return true;
    return false;
  }

  layout() {
    if (this.islinear()) {
      this.linearPrepare();
      this.layoutCalcBounds();
      // force it to center on the canvas
      this.graph.layoutMinX = -20;
      this.graph.layoutMaxX = 20;
    } else {
      this.layoutPrepare();
      /*if (this.doiter) {
        this.layoutIteration();
        this.spread();
        for (var i = 0; i < this.iterations; i++) {
        this.layoutIteration();
        }
        }*/
      ////this.centering();
      this.layoutCalcBounds();
    }
  }

  linearPrepare() {
    this.levs = new Map();
    for (var i = 0, node; node = this.graph.nodes[i]; i++) {
      var thisLevel = node.level || [0,0];
      if (!this.levs.has(thisLevel)) {
        this.levs.set(thisLevel, new Array());
      }
      this.levs.get(thisLevel).push(node);
      node.layoutPosX = 0;
      node.layoutPosY = -10*thisLevel[0] - thisLevel[1]; // can subtract thisLevel[1] to get separation by order
      node.layoutForceX = 0;
    }
    this.numlevs = this.levs.size;

    //for (var i=0, node; node = this.graph.nodes[i]; i++) {
    //node.connected = new Array();
    //}
    //for (var i=0, edge; edge = this.graph.edges[i]; i++) {
    //edge.source.connected.push(edge.target);
    //edge.target.connected.push(edge.source);
    //}
  }

  layoutPrepare() {
    this.levs = new Map();
    var totx = 0;
    for (var i = 0, node; node = this.graph.nodes[i]; i++) {
      var thisLevel = node.level || [0,0];
      if(!this.levs.has(thisLevel)) {
        this.levs.set(thisLevel, new Array());
      }
      this.levs.get(thisLevel).push(node);
      node.layoutPosX = node.posn;
      totx += node.posn;
      node.layoutPosY = -10*thisLevel[0] - thisLevel[1]; // can subtract thisLevel[1] to get separation by order
      node.layoutForceX = 0;
    }
    this.numlevs = this.levs.size;

    // Make trivial and whole group come at the start and end
    /*var wholeg = this.levs[this.numlevs-1][0];
      var triv = this.levs[0][0];
      for (var i = 0; i < this.graph.nodes.length; i++) {
      if(this.graph.nodes[i].label==wholeg.label) {
      this.graph.nodes[i] = this.graph.nodes[0];
      this.graph.nodes[0]=wholeg;
      }
      if(this.graph.nodes[i].label==triv.label) {
      this.graph.nodes[i] = this.graph.nodes[this.graph.nodes.length-1];
      this.graph.nodes[this.graph.nodes.length-1]=triv;
      }
      }*/
    //for (var i = 0, lev; lev = this.levs[i]; i++) {
    //    for(var k=0, len=lev.length; k<len; k++) {
    //            var node = lev[k];
    //            node.layoutPosX = 20*k-10*len +10;/* 0.1*Math.random(); */
    //       }
    //  }
    // Center <e> and G
    /*var wholeg = this.levs[this.numlevs-1][0];
      var triv = this.levs[0][0];
      totx -= triv.layoutPosX;
      totx -= wholeg.layoutPosX;
      // Trvial group and Z/p are linear graphs, so won't be here
      totx = totx/(this.graph.nodes.length-2);
      triv.layoutPosX = totx;
      wholeg.layoutPosX = totx;*/

    // Could be used to optimize layout
    //for (var i=0, node; node = this.graph.nodes[i]; i++) {
    //node.connected = new Array();
    //}
    //for (var i=0, edge; edge = this.graph.edges[i]; i++) {
    //edge.source.connected.push(edge.target);
    //edge.target.connected.push(edge.source);
    //}
  }

  /*centering() {
  // Find average of x-coords
  var maxx=-100, minx=100, cnt=0;
  for(var i=1; i<this.numlevs-1; i++) {
  for(var k=0, len=this.levs[i].length; k<len; k++) {
  var nx = this.levs[i][k].layoutPosX;
  if(nx<minx) { minx = nx; }
  if(nx>maxx) { maxx = nx; }
  }
  }
  var dx = (maxx+minx)/2;
  // Move everyone -dx
  for(var i=1; i<this.numlevs-1; i++) {
  for(var k=0, len=this.levs[i].length; k<len; k++) {
  this.levs[i][k].layoutPosX -= dx;
  }
  }
  this.levs[0][0].layoutPosX = dx;
  this.levs[this.levs.length - 1][0].layoutPosX = dx;
  }*/

  layoutCalcBounds() {
    var minx = Infinity, maxx = -Infinity, miny = Infinity, maxy = -Infinity;

    for (var i = 0; i < this.graph.nodes.length; i++) {
      var x = this.graph.nodes[i].layoutPosX;
      var y = this.graph.nodes[i].layoutPosY;

      if(x > maxx) maxx = x;
      if(x < minx) minx = x;
      if(y > maxy) maxy = y;
      if(y < miny) miny = y;
    }

    this.graph.layoutMinX = minx;
    this.graph.layoutMaxX = maxx;
    this.graph.layoutMinY = miny;
    this.graph.layoutMaxY = maxy;
  }

  /*layoutIteration() {
  // Forces on nodes due to node-node repulsions
  for (var i = 0; i < this.graph.nodes.length; i++) {
  var node1 = this.graph.nodes[i];
  for (var j = i + 1; j < this.graph.nodes.length; j++) {
  var node2 = this.graph.nodes[j];
  this.layoutRepulsive(node1, node2,1);
  }
  }

  // Forces on nodes due to edge attractions
  for (var i = 0; i < this.graph.edges.length; i++) {
  var edge = this.graph.edges[i];
  this.layoutAttractive(edge);
  }

  // Move by the given force, but not first or last
  for (var i = 1; i < this.graph.nodes.length-1; i++) {
  var node = this.graph.nodes[i];
  var xmove = this.c * node.layoutForceX;

  var max = this.maxVertexMovement;
  if(xmove > max) xmove = max;
  if(xmove < -max) xmove = -max;

  node.layoutPosX += xmove;
  node.layoutForceX = 0;
  }
  }

  layoutRepulsive(node1, node2, factor) {
  var dx = node2.layoutPosX - node1.layoutPosX;
  var dy = node2.layoutPosY - node1.layoutPosY;
  var d2 = dx * dx + dy * dy;
  if(d2 < 0.01) {
  dx = 0.1 * Math.random() + 0.1;
  dy = 0.1 * Math.random() + 0.1;
  d2 = dx * dx + dy * dy;
  }
  var d = Math.sqrt(d2);
  if(d < this.maxRepulsiveForceDistance) {
  var repulsiveForce = this.k * this.k;
  if(Math.abs(dx)<0.5) {
  //if(node1.level < node2.level) factor *= -1;
  dx = 1;
  }
  node2.layoutForceX += factor*repulsiveForce * dx / d2;
  node1.layoutForceX -= factor*repulsiveForce * dx / d2;
  }
  }

  layoutAttractive(edge) {
  var node1 = edge.source;
  var node2 = edge.target;

  // Undo the repulsion
  this.layoutRepulsive(node1,node2,-1);

  var dx = node2.layoutPosX - node1.layoutPosX;
  var dy = node2.layoutPosY - node1.layoutPosY;
  var d2 = dx * dx + dy * dy;
  if(d2 < 0.01) {
  dx = 0.1 * Math.random() + 0.1;
  dy = 0.1 * Math.random() + 0.1;
  d2 = dx * dx + dy * dy;
  }
  var d = Math.sqrt(d2);
  if(d > this.maxRepulsiveForceDistance) {
  d = this.maxRepulsiveForceDistance;
  d2 = d * d;
  }
  var attractiveForce = 8*(d - this.k * this.k) / this.k;

  node2.layoutForceX -= attractiveForce * dx/10 ; // / d;
  node1.layoutForceX += attractiveForce * dx/10; //  / d;
  }

  spread() {
  var width = 100;
  var maxabs=0;
  for(var i=0; i<this.numlevs; i++) {
  for(var k=0, len=this.levs[i].length; k<len; k++) {
  var thisone = Math.abs(this.levs[i][k].layoutPosX);
  if(thisone > maxabs) maxabs = thisone;
  }
  }
  if(maxabs>0) {
  maxabs = width/maxabs;
  for(var i=0; i<this.numlevs; i++) {
  for(var k=0, len=this.levs[i].length; k<len; k++) {
  this.levs[i][k].layoutPosX *= maxabs;
  }
  }
  }
  }*/
}

function nullfunc() { ; }

class EventHandler {
  constructor(renderer, options) {
    this.renderer = renderer;
    this.setOptions(options);
    var handlerinit = function(event){ event.data.initDrag(event) };
    var handlerupdrag = function(event){ event.data.updateDrag(event) };
    var handlerenddrag = function(event){ event.data.endDrag(event) };
    var handlermousemove = function(event) { event.data.mouseMove(event)};
    var handlertouchstart = function(event) {
      var touch = event.touches[0];
      var mouseEvent = new MouseEvent("mousedown", {
        clientX: touch.clientX,
        clientY: touch.clientY
      });
      renderer.element.dispatchEvent(mouseEvent);
    };
    var handlertouchmove = function(event) {
      var touch = event.touches[0];
      var mouseEvent = new MouseEvent("mousemove", {
        clientX: touch.clientX,
        clientY: touch.clientY
      });
      renderer.element.dispatchEvent(mouseEvent);
    };
    var handlertouchend = function(event) {
      var touch = event.touches[0];
      var mouseEvent = new MouseEvent("mouseup", {
        clientX: touch.clientX,
        clientY: touch.clientY
      });
      renderer.element.dispatchEvent(mouseEvent);
    };
    $(renderer.element).bind('mousedown', this, handlerinit);
    $(renderer.element).bind('mousemove', this, handlerupdrag);
    $(renderer.element).bind('mouseup', this, handlerenddrag);
    $(renderer.element).bind('mousemove', this, handlermousemove);
    $(renderer.element).bind('touchstart', this, handlertouchstart);
    $(renderer.element).bind('touchmove', this, handlertouchmove);
    $(renderer.element).bind('touchend', this, handlertouchend);
  }

  setOptions(options) {
    this.options = {
      initNodeDrag:   nullfunc,
      updateNodeDrag: nullfunc,
      endNodeDrag:    nullfunc,
      initEdgeDrag:   nullfunc,
      updateEdgeDrag: nullfunc,
      endEdgeDrag:    nullfunc,
      mouseMove:    nullfunc,
      moveNodeOnDrag: true
    }
    for (var k in options) {
      this.options[k] = options[k];
    }
  }

  offset(event) {
    //var pointer = [event.clientX, event.clientY];
    //var el = this.renderer.element;
    //var pos     = Position.cumulativeOffset(this.renderer.element);
    //var pos     = $(el).offset();
    var r = this.renderer.element.getBoundingClientRect();
    return [event.clientX-r.x, event.clientY-r.y];
  }

  mouseMove(event) {
    var overnode = this.renderer.nodeAt(this.offset(event));
    // this.renderer
    // this.renderer.graph
    // this.renderer.element
    if(overnode) {
      if(overnode != this.renderer.graph.highlit) {
        if(this.renderer.graph.highlit)
          this.renderer.graph.highlit.unhighlight();
        this.renderer.graph.highlit = overnode;
        this.renderer.highlight(overnode.value);
        // Turn on the lights
        var subid = overnode.value;
        $(`span[data-sgid="${subid}"]`).addClass("activesubgp");
      }
    } else if(this.renderer.graph.highlit) {
      var val = this.renderer.graph.highlit.value;
      this.renderer.unhighlight(val);
      // Turn off the lights
      var subid = val;
      $(`span[data-sgid="${subid}"]`).removeClass("activesubgp");
    }
  }

  initDrag(event) {
    if(isleftclick(event)) {
      this.activeNode = this.renderer.nodeAt(this.offset(event));
      if(this.activeNode != null) {
        this.options.initNodeDrag(this.activeNode);
        showsubinfo(this.activeNode, this.renderer.graph.ambient);
        this.renderer.unselectNodes();
        this.activeNode.select();
        this.renderer.draw();
      } else {
        clearsubinfo();
        this.renderer.unselectNodes();
        this.renderer.draw();
      }
      event.stopPropagation();
      event.preventDefault();
    }
  }

  updateDrag(event) {
    if(this.activeNode) {
      if(this.options.moveNodeOnDrag) {
        this.activeNode.center[0] = this.offset(event)[0];
        if(can_move_vertically) {
          this.activeNode.center[1] = this.offset(event)[1];
        }
      }
      this.options.updateNodeDrag(this.activeNode, event);
    }
  }

  endDrag(event) {
    if(this.activeNode) {
      var node = this.activeNode;
      var position = this.renderer.untranslate(this.offset(event));
      node.layoutPosX = position[0];
      // node.layoutPosY = position[1];
      this.options.endNodeDrag(this.activeNode);
      this.activeNode = null;
    }
  }
}

// Install event listeners
// Don't think this does anything
//var onClickHandler = function(event) {
//  var pos = this.eventPos(event);

//  var node = this.nodeAt(pos);
//  if(node && this.options.onnodeclick) {
//    this.options.onnodeclick(node);
//    return;
//  }
//};

// Utility from the web
function isleftclick(e) {
  var isLeftMB = false;
  e = e || window.event;

  if ("which" in e)  // Gecko (Firefox), WebKit (Safari/Chrome) & Opera
    isLeftMB = e.which == 1; 
  else if ("button" in e)  // IE, Opera 
    isLeftMB = e.button == 1; 
  return isLeftMB;
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

function newheight(rendr, numrows) {
  if (numrows>6) {
    var ctx = $("#subdiagram")[0].getContext('2d').canvas;
    var h = ctx.height;
    var w = ctx.width;
    ctx.height = 50*numrows;
    ctx.width = w;
  }
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

function redraw() {
  sdiagram.draw();
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
