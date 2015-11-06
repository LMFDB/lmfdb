# -*- coding: utf-8 -*-

import os
import yaml
from flask import url_for

def linked_name(item, level=""):
    """ take the dictionary describing a TOC entry and return the
    title wrapped in an appropriate href link.
    """
    if level == "heading":
        if 'url_for' in item:
            url = url_for(item['url_for'],**item.get('url_args',dict()))
            return ''.join(['<h2 class="link"><a href="',url,'">',item['title'],'</a></h2>\n'])
        else:
            return ''.join(['<h2>',item['title'],'</h2>\n'])

    else:
        if 'url_for' in item and not ('status' in item and item['status'] == 'future'):
            url = url_for(item['url_for'],**item.get('url_args',dict()))
            this_entry = ''.join(['<a href="',url,'">',item['title'],'</a>'])
        else:
            this_entry = item['title']
        if this_entry == 'dummy':
            this_entry = '&nbsp;'
        if 'status' in item and item['status'] == 'future':
            this_entry = ''.join(['<div class="future">',this_entry,'</div>'])
	if 'status' in item and item['status'] == 'beta':
            this_entry = ''.join(['<div class="beta">',this_entry,'</div>'])
        return this_entry

# The unique instance of the class SideBar:

the_sidebar = None

# Function to create the unique SideBar instance if necessary, and return it:

def get_sidebar():
    global the_sidebar
    if the_sidebar is None:
        the_sidebar = SideBar()
    return the_sidebar

# The SideBar class, created by reading the file sidebar.yaml

class SideBar(object):
    """
    Class for holding the sidebar content.
    """
    def __init__(self):
        _curdir = os.path.dirname(os.path.abspath(__file__))
        self.toc_dic =  yaml.load(open(os.path.join(_curdir, "sidebar.yaml")))
        self.main_headings = self.toc_dic.keys()
        self.main_headings.sort()
        heading = lambda k: linked_name(self.toc_dic[k]['heading'],'heading')
        self.data = [(k,heading(k),self.toc_dic[k]) for k in self.main_headings]

        for key, head, data in self.data:
            if data['type'] == 'L':
                for item in data['firstpart']['entries']:
                    item['url'] = linked_name(item)
                for item in data['secondpart']['parts']:
                    item['url'] = linked_name(item)

            if data['type'] == '2 column':
                for entry in data['parts']:
                    entry['url'] = linked_name(entry)
                if 'part2' in entry:
                    for pt2 in entry['part2']:
                        pt2['url'] = linked_name(pt2)
                        for item in pt2['parts']:
                            item['url'] = linked_name(item)

            if data['type'] in ['multilevel', 'simple']:
                for entry in data['parts']:
                    entry['url'] = linked_name(entry)
                    if 'part2' in entry:
                        for pt2 in entry['part2']:
                            pt2['url'] = linked_name(pt2)
                            if 'part3' in pt2:
                                for item in pt2['part3']:
                                    item['url'] = linked_name(item)
