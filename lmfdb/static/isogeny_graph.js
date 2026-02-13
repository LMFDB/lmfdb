/**
 * Interactive isogeny graph rendering using Cytoscape.js
 *
 * Usage: initIsogenyGraph('container-id', elementsJSON)
 */

function _isoTooltipLine(parent, text, isMath) {
    var span = document.createElement('span');
    span.textContent = text;
    parent.appendChild(span);
    parent.appendChild(document.createElement('br'));
}

function _isoTooltipBold(parent, text) {
    var b = document.createElement('strong');
    b.textContent = text;
    parent.appendChild(b);
    parent.appendChild(document.createElement('br'));
}

function _isoTooltipEmphasis(parent, text) {
    var em = document.createElement('em');
    em.textContent = text;
    parent.appendChild(em);
    parent.appendChild(document.createElement('br'));
}

function initIsogenyGraph(containerId, elements) {
    var container = document.getElementById(containerId);
    if (!container || !elements || elements.length === 0) return;

    // Check if positions are provided (preset layout) or need auto-layout
    var hasPositions = false;
    var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (var i = 0; i < elements.length; i++) {
        if (elements[i].group === 'nodes' && elements[i].position) {
            hasPositions = true;
            var p = elements[i].position;
            if (p.x < minX) minX = p.x;
            if (p.x > maxX) maxX = p.x;
            if (p.y < minY) minY = p.y;
            if (p.y > maxY) maxY = p.y;
        }
    }

    if (hasPositions) {
        var graphW = maxX - minX;
        var graphH = maxY - minY;
        container.style.width = Math.min(600, Math.max(200, graphW + 160)) + 'px';
        container.style.height = Math.min(400, Math.max(80, graphH + 100)) + 'px';
    } else {
        // Count nodes to scale container for auto-layout
        var nNodes = 0;
        for (var i = 0; i < elements.length; i++) {
            if (elements[i].group === 'nodes') nNodes++;
        }
        var side = Math.min(600, Math.max(250, nNodes * 40));
        container.style.width = side + 'px';
        container.style.height = side + 'px';
    }

    var layoutOpts = hasPositions
        ? { name: 'preset' }
        : { name: 'cose', animate: false, nodeRepulsion: function() { return 8000; },
            idealEdgeLength: function() { return 80; }, padding: 30 };

    var cy = cytoscape({
        container: container,
        elements: elements,
        layout: layoutOpts,
        userZoomingEnabled: false,
        userPanningEnabled: false,
        boxSelectionEnabled: false,
        style: [
            {
                selector: 'node',
                style: {
                    'label': 'data(label)',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'font-size': '12px',
                    'font-family': 'sans-serif',
                    'background-color': '#fff',
                    'border-width': 2,
                    'border-color': '#555',
                    'width': 60,
                    'height': 30,
                    'shape': 'round-rectangle',
                    'color': '#333',
                    'cursor': 'pointer'
                }
            },
            {
                selector: 'node[?optimal]',
                style: {
                    'border-width': 3,
                    'border-color': '#0055a2',
                    'background-color': '#e8f0fe'
                }
            },
            {
                selector: 'edge',
                style: {
                    'label': 'data(label)',
                    'font-size': '11px',
                    'text-background-color': '#fff',
                    'text-background-opacity': 0.85,
                    'text-background-padding': '2px',
                    'line-color': '#888',
                    'width': 1.5,
                    'curve-style': 'bezier',
                    'color': '#555'
                }
            }
        ]
    });

    cy.fit(30);

    // Minimum size enforcement: if the graph is too small, zoom out a bit
    var bb = cy.elements().boundingBox();
    if (bb.w < 80 && bb.h < 80) {
        cy.zoom(cy.zoom() * 0.7);
        cy.center();
    }

    // Create tooltip element
    var tooltip = document.createElement('div');
    tooltip.className = 'isogeny-tooltip';
    tooltip.style.cssText = 'display:none; position:absolute; background:#fff; ' +
        'border:1px solid #ccc; border-radius:4px; padding:8px 12px; ' +
        'font-size:13px; line-height:1.5; box-shadow:0 2px 8px rgba(0,0,0,0.15); ' +
        'z-index:1000; pointer-events:none; max-width:280px;';
    container.style.position = 'relative';
    container.appendChild(tooltip);

    // Hover: show tooltip with curve metadata
    cy.on('mouseover', 'node', function(evt) {
        var node = evt.target;
        var d = node.data();

        // Clear previous content safely
        while (tooltip.firstChild) tooltip.removeChild(tooltip.firstChild);

        _isoTooltipBold(tooltip, d.label);
        if (d.j_inv !== undefined) _isoTooltipLine(tooltip, 'j-invariant: ' + d.j_inv);
        if (d.torsion !== undefined) _isoTooltipLine(tooltip, 'Torsion: ' + d.torsion);
        if (d.degree !== undefined && d.degree !== 0) _isoTooltipLine(tooltip, 'Modular degree: ' + d.degree);
        if (d.faltings_height !== undefined) _isoTooltipLine(tooltip, 'Faltings height: ' + d.faltings_height);
        if (d.optimal) _isoTooltipEmphasis(tooltip, 'Optimal curve');

        tooltip.style.display = 'block';

        // Position tooltip near the node
        var pos = node.renderedPosition();
        tooltip.style.left = (pos.x + 15) + 'px';
        tooltip.style.top = (pos.y - 10) + 'px';
    });

    cy.on('mouseout', 'node', function() {
        tooltip.style.display = 'none';
    });

    // Click: navigate to curve page
    cy.on('tap', 'node', function(evt) {
        var url = evt.target.data('url');
        if (url) {
            window.location.href = url;
        }
    });

    return cy;
}
