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
  for(i=0;i<widths.length;i++)
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
    var strindex = content.lastIndexOf(achar);
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



//jQuery('table:has(col)').each(alignColumns);
  
