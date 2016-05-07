// This is the snap.svg script way of controlling the files.
var s = Snap("#lmdfb_map");
var svg_desc = "svg_description" // CSS selector for description div box
var svg_examples = "svg_examples";
var svg_element_currently_clicked = 0;
var svg_element_currently_clicked_ID = "";

// JSON object list for editing the SVG descriptions easily
// opaque_id is the id of the element that gets its opacity turned down
// No more than three list items!



// This loads the SVG file and loops through the json objects to
// create all of the interactive SVG elements.
var tux = Snap.load("lmfdbmap/lmfdbmap.svg", function ( loadedFragment )
{
    s.append( loadedFragment );

    var JSON_entries, IDList = "";
    for( i = 0; i < svg.json.length; i++)
    {
        //This allows you to have multiple elements that trigger the description text
        JSON_entries = svg.json[i].id.split(",");
        //This catalogs the list of all clickable elements
        IDList += svg.json[i].id + ", ";

        for(var j = 0; j < JSON_entries.length; j++)
        {
            s.select(JSON_entries[j]).mouseover( svg_element_mouse_in(
                svg.json[i].opaque_id, svg.json[i].description, svg.json[i].list, svg.json[i].list_link
            ) );
            s.select(JSON_entries[j]).mouseout( svg_element_mouse_out(
                svg.json[i].opaque_id
            ) );
            s.select(JSON_entries[j]).click( svg_element_mouse_click(
                svg.json[i].opaque_id, svg.json[i].description, svg.json[i].list, svg.json[i].list_link, svg.json[i].url
            ) );
            s.select(JSON_entries[j]).dblclick( svg_element_mouse_dblclick(
                svg.json[i].url
            ) );
        }
    }
    //Gets rid of the extra ", " at the end.
    IDList = IDList.substring(0,IDList.length - 2);


    // This jQuery function clears the infoboxes and selection when not clicking
    // an element in the SVG.
    $(document).ready(function()
    {
        $(document).click(function(event)
        {
            if(!$(event.target).is(IDList))
            {
                svg_element_currently_clicked = 0;
                if(svg_element_currently_clicked_ID != "")
                {
                    //Changes the opacity of group of svg objects
                    change_opacity(svg_element_currently_clicked_ID, 1.0, true);
                    svg_element_currently_clicked_ID = "";
                }
                fillNewInformation( "", "", "");
            }
        });
    });

});



// This function fills the description and examples boxes with information.
var fillNewInformation = function ( description_text, description_list, description_list_link)
{
    //Fills description DIV
    document.getElementById( svg_desc ).innerHTML = "<p></p>";
    document.getElementById( svg_desc ).innerHTML += "<p>" + description_text + "</p>";

    //Fills related objects list/DIV
    split_list = description_list.split(",");
    split_list_links = description_list_link.split(",");
    var list_html = document.getElementById( svg_examples );

    if(split_list.length > 1)
    {
        //If more than one item, i.e. a single space.
        list_html.innerHTML = "<p>Examples</p>";

        var temp_string = "";
        for(i = 0; i < split_list.length; i++)
        {
      //      temp_string = temp_string + "<a href=\"" + split_list_links[i] + "\">\n" + "<li>" + split_list[i] + "</li>\n" + "</a>\n";
            temp_string = temp_string + "<li>" + split_list[i] + "</li>\n";
        };
        list_html.innerHTML += "<ul>" + temp_string + "</ul>"

    }
    else
    {
        list_html.innerHTML = " ";
    }
};


// This function changes the opacity for a group of elements
var change_opacity = function ( elements, opacity, bypass_if_statement = false )
{
    var opaque_elements = elements.split(",");
    for(i = 0; i < opaque_elements.length; i++)
    {
    if( svg_element_currently_clicked_ID != elements || bypass_if_statement)
        {
            s.select( opaque_elements[i] ).attr({"fill-opacity": opacity});
        }
    }
};


// Function for what happens when the mouse goes over an object.
var svg_element_mouse_in = function ( svg_element_id, description_text, description_list, description_list_link )
{
    return function()
    {
        //Changes the opacity of group of svg objects
        change_opacity(svg_element_id, 0.5)

        //If a button has not been clicked fill info
        if( !svg_element_currently_clicked )
        {
            fillNewInformation( description_text, description_list, description_list_link);
        }
    };
};

// Function for what happens when the mouse stops being over an object.
var svg_element_mouse_out = function ( svg_element_id )
{
    return function()
    {
        //Changes the opacity of group of svg objects.
        change_opacity(svg_element_id, 1.0)

        //If a button has not been clicked clear info
        if( !svg_element_currently_clicked )
        {
            fillNewInformation( "", "", "");
        }
    };
};

// Function for what happens when you click an object.
var svg_element_mouse_click = function (  svg_element_id, description_text, description_list, description_list_link, url  )
{
    return function()
    {

        if( !svg_element_currently_clicked )
        {
            //If nothing is currently clicked
            svg_element_currently_clicked = 1;
            svg_element_currently_clicked_ID = svg_element_id;

            change_opacity(svg_element_id, 0.5)
            fillNewInformation( description_text, description_list, description_list_link);
        }
        else if( svg_element_currently_clicked
        && svg_element_currently_clicked_ID == svg_element_id)
        {
            //If the same element is clicked twice
            svg_element_currently_clicked = 0;
            svg_element_currently_clicked_ID = "";

            change_opacity(svg_element_id, 1.0)
            fillNewInformation( "", "", "");
        }
        else if( svg_element_currently_clicked
        && svg_element_currently_clicked_ID != svg_element_id)
        {
            //If one element is clicked then a different one is clicked.

            //Reset old clicked element
            change_opacity(svg_element_currently_clicked_ID, 1.0, true);

            //Set the new element as current and update the old information
            svg_element_currently_clicked_ID = svg_element_id;
            change_opacity(svg_element_id, 0.5, true);
            fillNewInformation( description_text, description_list, description_list_link);
        }
    };
};

// Function for what happens when you click an object.
var svg_element_mouse_dblclick = function ( url )
{
    return function()
    {
        //Goes to URL on click
        //window.location.href = url;
    };
};
