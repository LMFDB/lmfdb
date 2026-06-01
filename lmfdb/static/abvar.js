function make_sdiagram(canv, ambient, gdatalist, orderdata, num_layers) {
  var order_lookup = new Map();
  var simpleorder = new Map();
  for (var k=0; k < orderdata.length; k++) {
    var trip = orderdata[k];
    order_lookup.set(trip[0], [trip[1], trip[2]]);
    simpleorder.set(trip[0], [k,0]);
  }
  var nodes, edges;
  [nodes, edges] = gdatalist;
  var grph = new Graph(ambient);
  // x-coord for by # primes is in 6
  console.log("make_sdiagram", nodes);
  grph.addNodes(nodes, order_lookup, 6);
  // x-coord for by # primes is in 7
  // grph.addNodes(nodes, simpleorder, 7);
  for(var k=0, edge; edge=edges[k]; k++) {
    grph.addEdge(edge[0],edge[1]);
  }
  var layout = new Layout(grph);
  layout.layout();

  renderer = new Renderer(document.getElementById(canv), grph);

  // Need to call Event.Handler here
  new EventHandler(renderer, {
    updateNodeDrag: function(node, event) {
      renderer.draw();
    }
  });
  newheight(renderer, num_layers);
  renderer.setSize();
  // The renderer is stored in sdiagram by the web page
  return [renderer,grph];
}

function showsubinfo(node, isocls) {
  $.get(`/Variety/Abelian/Fq/endringinfo/${isocls}/${node.value}`,
        function(data){
          $(".selectedsub").map(function() {
            this.innerHTML = data;
            renderMathInElement(this, katexOpts);
            return;
          });
        });
}

function clearsubinfo() {
  $.get(`/Variety/Abelian/Fq/endringinfo/`,
        function(data){
          $(".selectedsub").map(function() {
            this.innerHTML = data;
            renderMathInElement(this, katexOpts);
            return;
          });
        });
}
