#!/usr/bin/env python

import sys
import re
import os
import json
import yaml
import math

import toc_utils

stream = open("sidebar.yaml", 'r')
toc_dic =  yaml.load(stream)

# print toc_dic

tocfile = open("thetoc1",'w')

tocfile.write('<link href="http://beta.lmfdb.org/style.css" rel="stylesheet" type="text/css" /> \n')

tocfile.write(toc_utils.toc_css())

# tocfile.write(toc_utils.mathjax_header())

tocfile.write('<div id="sidebar">\n')

mainheadings = toc_dic.keys()
mainheadings.sort()

print "\n\n",mainheadings

for head in mainheadings:
    top_group = toc_dic[head]
    group_type = top_group['type']
    group_heading = top_group['heading']
    
    this_heading = toc_utils.linked_name(group_heading,"heading")
    tocfile.write(this_heading)

    if group_type == "L":
       firstpart = top_group['firstpart']
       this_row = '<div class="L">'
       this_row += '<span class="heading">'+firstpart['heading']+'</span>'
       for item in firstpart['entries']:
          this_item = toc_utils.linked_name(item)
          this_row += '<span class="L">'+this_item+'</span>'
       this_row += '</div>\n'
       tocfile.write(this_row)

       secondpart = top_group['secondpart']
       this_row = '<div class="L">'
       for item in secondpart['parts']:
          this_item = toc_utils.linked_name(item)
          this_row += '<span class="L">'+this_item +'</span>'
          this_row += ' '
       this_row += '</div>\n'
       tocfile.write(this_row)

       thirdpart = top_group['thirdpart']
       this_row = '<div class="L">'
       for item in thirdpart['parts']:
          this_item = toc_utils.linked_name(item)
          this_row += '<span class="L">'+this_item +'</span>'
          this_row += ' '
       this_row += '</div>\n'
       tocfile.write(this_row)


    if group_type == "2 column":
       parts = top_group['parts']
       num_items = len(parts)
       num_half = int(math.ceil(num_items/2.0))

       print "there are",num_items,"and half is",num_half

       tocfile.write('<table class="short">\n')
       tocfile.write('<tr>\n')

       # first column
       tocfile.write('<td width="100"><ul class="list">\n')
       for j in range(num_half):  # items in the first column
           this_entry = parts[j]
           try:
              status = this_entry['status']
           except KeyError:
              status = ""
           this_entry_html = '<li>'

           this_heading = toc_utils.linked_name(this_entry)
           this_entry_html += this_heading

           ### use status in linked_name insteadl of here
           if status == 'future':
               this_entry_html = '<div class="future">' + this_entry_html + '</div>\n'
           if status == 'beta':
               this_entry_html = '{% if BETA %}\n' + this_entry_html + '{% endif %}\n'
           tocfile.write(this_entry_html)

       tocfile.write('</ul></td>\n')

       # hack to put space between columns
       tocfile.write('<td>&nbsp;</td>\n')
       # second column
       tocfile.write('<td width="100"><ul class="list">\n')
       for j in range(num_half,num_items):  # items in the second column
           this_entry = parts[j]
           try:
              status = this_entry['status']
           except KeyError:
              status = ""
           this_entry_html = '<li>'

           this_heading = toc_utils.linked_name(this_entry)
           this_entry_html += this_heading

           if status == 'future':
               this_entry_html = '<div class="future">' + this_entry_html + '</div>\n'
           if status == 'beta':
               this_entry_html = '{% if BETA %}\n' + this_entry_html + '{% endif %}\n'
           tocfile.write(this_entry_html)

       tocfile.write('</ul></td>\n')
       tocfile.write('</tr>\n</table>\n')

    if group_type == "multilevel":
       tocfile.write('<table class="short">\n')
       parts = top_group['parts']
 #      print "the parts are",parts
       for index,entry in enumerate(parts):
          if index % 2 == 1:
              tocfile.write('<tr bgcolor="#fff">\n')
          else:
              tocfile.write('<tr>\n')
   #       print entry
   #       print "xxxx"
          # part_title = entry['title']
          part_title = toc_utils.linked_name(entry)
          if 'style' in entry and entry['style'] == "rotate":
          #    tocfile.write(' <td width="15" class="borc"><p class="test rotation">')
              tocfile.write(' <td width="40" class="borc rotation"><p class="test rotation">')
          elif 'style' in entry and entry['style'] == "full":
            #  tocfile.write(' <td scope="col" colspan="2" width="200" class="full"><p>')
            #  tocfile.write(' <td scope="col" colspan="2" class="full"><p>A')
              tocfile.write(' <td scope="col" colspan="2" class="full">')
          else:
            #  tocfile.write(' <td width="15" class="borc"><p>')
              tocfile.write(' <td class="borc"><p>')
          tocfile.write(part_title)
          if not ('style' in entry and entry['style'] == "full"):
              tocfile.write('</p>')
          tocfile.write('</td>')
          if not ('style' in entry and entry['style'] == "full"):
            #  tocfile.write('<td width="185" class="bor">\n')
              tocfile.write('<td class="bor">\n')

          if not 'part2' in entry:
              continue
          else:
              tocfile.write('<ul class="list">\n')
          for part2 in entry['part2']:
             tocfile.write('<li>')
             this_title = toc_utils.linked_name(part2)
             this_title = '<span class="subtitle">'+this_title+'</span>'
          #   tocfile.write(part2['title'])
             tocfile.write(this_title)

             these_parts = ""
             if 'parts' in part2:
                 for item in part2['parts']:
                    item_title = toc_utils.linked_name(item)
                    these_parts += '<span class="subitem">' 
                    these_parts += item_title
                    these_parts += '</span>'
                    these_parts += ' '
              #   these_parts = "\n<br>\n"+these_parts
                 these_parts = '\n<div class="parts">'+these_parts+'</div>'
            
             tocfile.write(these_parts)
             tocfile.write('</li>\n')

          tocfile.write('</ul>')
          tocfile.write('</td>')
          tocfile.write('</tr>')
       tocfile.write('</table>\n')

tocfile.write('</div>\n')

