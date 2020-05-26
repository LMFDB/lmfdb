function alignColumns()
{
  jQuery('col[align=char]', this).each(alignColumnChar);
  // jQuery('col[align=center]', this).each(alignColumnCenter);
  // jQuery('col[align=right]', this).each(alignColumnRight);
}

function alignColumnChar()
{
  // What're we aligning on?
  var achar = jQuery(this).attr('char');

  // Get the table that this column belongs to
  var table = jQuery(this).closest('table');

  // Find which table column this <col> tag is referring to (bearing in mind colspans in previous <col> tags)
  var index = 1;
  var coltags = jQuery(this).prevAll('col').each(function(){
    var span = jQuery(this).attr('colspan');
    index += span ? parseInt(span) : 1;
  });

  // Get all table cells in this column
  var widths = [];
  var colcells = jQuery('td', table).nthCol(index);

  // Build a list of content widths from the alignment point onward, and remember the largest
  colcells.each(calculateAlignWidth);
  
  // Add right-padding to each cell equivalent to the difference between its width and the maximum
  var maxwidth = 0;
  for(var i=0;i<widths.length;i++)
  {
    maxwidth = widths[i] > maxwidth ? widths[i] : maxwidth;
  }
  
  colcells.each(addAlignPadding);
  
  function addAlignPadding(i)
  {
    jQuery(this).css('padding-right', maxwidth-widths[i]+5+'px');
    jQuery(this).css('text-align', 'right');
  }
  
  function calculateAlignWidth(i)
  {
    var content = jQuery(this).text();
    //var strindex = content.lastIndexOf(achar);
    var strindex = content.indexOf(achar);
    //  alert(content,strindex);
    if (strindex == -1)
    {
      widths[i] = 0;
      return;
    }
    var remainder = content.substr(strindex);
    // Make a dummy element with the remainder to get its width
    var tag = jQuery('<span>'+remainder+'</span>').appendTo(this);
    widths[i] = tag.width();
    tag.remove();
  }
function calculateAlignWidthOld(i)
  {
    var content = jQuery(this).text();
    //var strindex = content.lastIndexOf(achar);
    var strindex = content.indexOf(achar);
    //  alert(content,strindex);
    if (strindex == -1)
    {
      widths[i] = 0;
      return;
    }
    var remainder = content.substr(strindex);
    // Make a dummy element with the remainder to get its width
    var tag = jQuery('<span>'+remainder+'</span>').appendTo(this);
    widths[i] = tag.width();
    tag.remove();
  }
}

$.fn.dataTableExt.afnFiltering.push(
    function( oSettings, aData, iDataIndex ) {
        var wtElt=document.getElementById('weight');
        var iWt;
        var thisWt;
        //alert("hrjj");
        // we only want to filter on weight
        var a = (oSettings.aoColumns[1].sTitle).toString().trim();
        var b = "Weight".toString();
        for (var i=0,n=Math.max(a.length, b.length); i<n && a.charAt(i) === b.charAt(i); ++i);
        if (i != n){
            //alert(a+":"+a.charAt(0)+"."+a.charAt(1)+":"+b.charAt(0));
            return true;
        } 

//        if (col_id.toString().localeCompare("Weight".toString())!=0) {
//            alert(col_id.toString().localeCompare("Weight".toString()));
//            return true;
//        }
        if (wtElt == null) {
            iWt=0; // default value
        }
        if (wtElt != null) {
            iWt = wtElt.value * 1;
        }         
        thisWt = aData[1];
        if ( iWt == thisWt)
        {
            return true;
        }
        return false;
    }
)

function set_browse_value(name,val) {
  document.forms.browse[name].value=val;
  document.forms.browse.submit();			   
}

//jQuery('table:has(col)').each(alignColumns);
  


