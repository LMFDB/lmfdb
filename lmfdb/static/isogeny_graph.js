/**
 * Interactive isogeny graph rendering using Cytoscape.js
 *
 * Usage: initIsogenyGraph('container-id', elementsJSON, enabledLayouts, defaultLayout)
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

// Registry of all known layouts.  Keys are the display names used in
// the dropdown and passed from Python via graph_layouts.  To add a new
// layout, add an entry here and load its JS in cytoscape_scripts.html.
var LAYOUT_REGISTRY = {
    'Preset':     { name: 'preset' },
    'Elk-stress': { name: 'elk', animate: false, padding: 30, elk: { algorithm: 'stress' } },
    'Circle':     { name: 'circle', animate: false, padding: 30 },
    'Concentric': { name: 'concentric', animate: false, padding: 30,
                    concentric: function(node) { return node.degree(); },
                    levelWidth: function() { return 2; } },
    'Klay':       { name: 'klay', animate: false, padding: 30 },
    'Dagre':      { name: 'dagre', animate: false, padding: 30 },
    'Cola':       { name: 'cola', animate: false, padding: 30 }
};

function initIsogenyGraph(containerId, elements, enabledLayouts, defaultLayout) {
    var container = document.getElementById(containerId);
    if (!container || !elements || elements.length === 0) return;

    // Count nodes and check if preset positions are provided
    var nNodes = 0;
    var hasPositions = false;
    var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (var i = 0; i < elements.length; i++) {
        if (elements[i].group === 'nodes') {
            nNodes++;
            if (elements[i].position) {
                hasPositions = true;
                var p = elements[i].position;
                if (p.x < minX) minX = p.x;
                if (p.x > maxX) maxX = p.x;
                if (p.y < minY) minY = p.y;
                if (p.y > maxY) maxY = p.y;
            }
        }
    }

    if (nNodes === 1) {
        container.style.width = '200px';
        container.style.height = '80px';
    } else if (hasPositions) {
        var graphW = maxX - minX;
        var graphH = maxY - minY;
        container.style.width = Math.min(600, Math.max(200, graphW + 160)) + 'px';
        container.style.height = Math.min(400, Math.max(60, graphH + 100)) + 'px';
    } else {
        var side = Math.min(600, Math.max(250, nNodes * 40));
        container.style.width = side + 'px';
        container.style.height = side + 'px';
    }

    var layoutOpts = (defaultLayout && LAYOUT_REGISTRY[defaultLayout])
        ? LAYOUT_REGISTRY[defaultLayout]
        : { name: 'preset' };

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
                    'color': '#333'
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
                    'text-background-opacity': 1,
                    'text-background-padding': '2px',
                    'line-color': '#888',
                    'width': 1.5,
                    'curve-style': 'bezier',
                    'color': '#555'
                }
            }
        ]
    });

    if (nNodes === 1) {
        // Single node: match the apparent node size of small multi-node graphs
        cy.zoom(1.2);
        cy.center();
        cy.nodes().ungrabify();
    } else {
        cy.fit(30);

        // Minimum size enforcement: if the graph is too small, zoom out a bit
        var bb = cy.elements().boundingBox();
        if (bb.w < 80 && bb.h < 80) {
            cy.zoom(cy.zoom() * 0.7);
            cy.center();
        }
    }

    // Save original positions and container dimensions for preset restore
    var origPositions = {};
    for (var pi = 0; pi < elements.length; pi++) {
        if (elements[pi].group === 'nodes' && elements[pi].position) {
            origPositions[elements[pi].data.id] = {
                x: elements[pi].position.x,
                y: elements[pi].position.y
            };
        }
    }
    var origWidth = container.style.width;
    var origHeight = container.style.height;

    // Skip layout controls for trivial graphs
    if (nNodes <= 1) {
        // still set up tooltip and click handlers below
    } else {

    // Build layout map from the enabled list
    var layouts = {};
    if (enabledLayouts) {
        for (var ei = 0; ei < enabledLayouts.length; ei++) {
            var key = enabledLayouts[ei];
            if (LAYOUT_REGISTRY[key]) layouts[key] = LAYOUT_REGISTRY[key];
        }
    }

    var controls = document.createElement('div');
    controls.style.cssText = 'margin: 8px 0;';
    var label = document.createElement('label');
    label.textContent = 'Layout: ';
    label.style.fontWeight = 'bold';
    var select = document.createElement('select');
    defaultLayout = defaultLayout || 'Preset';
    var layoutNames = Object.keys(layouts);
    for (var li = 0; li < layoutNames.length; li++) {
        if (layoutNames[li] === 'Preset' && !hasPositions) continue;
        var opt = document.createElement('option');
        opt.value = layoutNames[li];
        opt.textContent = layoutNames[li];
        if (layoutNames[li] === defaultLayout) opt.selected = true;
        select.appendChild(opt);
    }
    select.addEventListener('change', function() {
        if (select.value === 'Preset') {
            // Restore original positions and container size
            var ids = Object.keys(origPositions);
            for (var ri = 0; ri < ids.length; ri++) {
                cy.getElementById(ids[ri]).position(origPositions[ids[ri]]);
            }
            container.style.width = origWidth;
            container.style.height = origHeight;
            cy.resize();
            cy.fit(30);
        } else {
            // Ensure enough room for computed layouts
            container.style.width = '500px';
            container.style.height = '400px';
            cy.resize();
            try {
                cy.layout(layouts[select.value]).run();
                cy.fit(30);
            } catch (e) {
                console.warn('Layout "' + select.value + '" failed:', e.message);
                // Show inline error
                var msg = document.createElement('div');
                msg.textContent = 'Layout "' + select.value + '" not available: ' + e.message;
                msg.style.cssText = 'color:#c00; font-size:13px; margin-top:4px;';
                if (controls.querySelector('.layout-error')) {
                    controls.removeChild(controls.querySelector('.layout-error'));
                }
                msg.className = 'layout-error';
                controls.appendChild(msg);
            }
        }
    });
    label.appendChild(select);
    controls.appendChild(label);
    container.parentNode.insertBefore(controls, container);

    } // end nNodes > 1

    // Create tooltip element (appended to document.body so it is not
    // clipped by the container's overflow)
    var tooltip = document.createElement('div');
    tooltip.className = 'isogeny-tooltip';
    tooltip.style.cssText = 'display:none; position:absolute; background:#fff; ' +
        'border:1px solid #ccc; border-radius:4px; padding:8px 12px; ' +
        'font-size:13px; line-height:1.5; box-shadow:0 2px 8px rgba(0,0,0,0.15); ' +
        'z-index:1000; pointer-events:none; white-space:nowrap;';
    document.body.appendChild(tooltip);

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
        if (d.cm !== undefined) _isoTooltipLine(tooltip, 'CM: ' + d.cm);
        if (d.optimal) _isoTooltipEmphasis(tooltip, 'Optimal curve');

        tooltip.style.display = 'block';

        // Position tooltip near the node using page coordinates
        var rect = container.getBoundingClientRect();
        var pos = node.renderedPosition();
        tooltip.style.left = (rect.left + window.scrollX + pos.x + 25) + 'px';
        tooltip.style.top = (rect.top + window.scrollY + pos.y - 10) + 'px';

        $('html,body').css('cursor', 'pointer');
    });

    cy.on('mouseout', 'node', function() {
        tooltip.style.display = 'none';
        $('html,body').css('cursor', 'default');
    });

    // Prevent dragging nodes outside the visible area
    cy.on('drag', 'node', function(evt) {
        var node = evt.target;
        var pos = node.position();
        var ext = cy.extent();
        var hw = node.width() / 2 + 10;
        var hh = node.height() / 2 + 10;
        var x = Math.max(ext.x1 + hw, Math.min(ext.x2 - hw, pos.x));
        var y = Math.max(ext.y1 + hh, Math.min(ext.y2 - hh, pos.y));
        if (x !== pos.x || y !== pos.y) {
            node.position({ x: x, y: y });
        }
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
