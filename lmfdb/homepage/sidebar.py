
import os
import yaml
from flask import url_for

def linked_name(item, level=""):
    """ take the dictionary describing a TOC entry and return the
    title wrapped in an appropriate href link.
    """
    if 'url_for' in item and not ('status' in item and item['status'] == 'future'):
        url = url_for(item['url_for'],**item.get('url_args',{}))
        this_entry = ''.join(['<a href="',url,'">',item['title'],'</a>'])
    else:
        this_entry = item['title']

    if this_entry == 'dummy':
        this_entry = '&nbsp;'

    if 'status' in item and item['status'] == 'beta':
        this_entry = ''.join(['<div class="beta">', this_entry, '</div>'])
    elif item['show'] and 'status' in item and item['status'] == 'future':
        if item['show']:
            this_entry = ''.join(['<div class="alpha">', this_entry, '</div>'])
        else:
            this_entry = ''.join(['<div class="future">',this_entry,'</div>'])

    # headings should be wrapped in h2's:
    if level == "heading":
        this_entry = ''.join(['<h2>', this_entry,'</h2>\n'])

    return this_entry

def set_url(item):
    from lmfdb.app import is_beta, is_alpha, alpha_blueprints
    if is_alpha():
        sections = alpha_blueprints()
        if "url_for" in item:
            u = item["url_for"]
            item['show'] = (u == "l_functions.contents") or ("." not in u) or (u in sections)
        else:
            item["show"] = False
    else:
        item['show'] = (not item.get('status')) or (is_beta() and item['status'] == 'beta')
    item['url'] = linked_name(item)

# The unique instance of the class SideBar:

the_sidebar = None

# Function to create the unique SideBar instance if necessary, and return it:

def get_sidebar():
    global the_sidebar
    if the_sidebar is None:
        the_sidebar = SideBar()
    return the_sidebar

# The SideBar class, created by reading the file sidebar.yaml

class SideBar():
    """
    Class for holding the sidebar content.
    """
    def __init__(self):

        _curdir = os.path.dirname(os.path.abspath(__file__))
        self.toc_dic = yaml.load(open(os.path.join(_curdir, "sidebar.yaml")), Loader=yaml.FullLoader)
        self.main_headings = list(self.toc_dic)
        self.main_headings.sort()
        def heading(k): return linked_name(self.toc_dic[k]['heading'],'heading')
        self.data = [(k,heading(k),self.toc_dic[k]) for k in self.main_headings]

        for _, _, data in self.data:
            if 'parts' in data:
                for entry in data['parts']:
                    set_url(entry)
                    if 'part2' in entry:
                        for pt2 in entry['part2']:
                            set_url(pt2)
                            if 'part3' in pt2:
                                for item in pt2['part3']:
                                    set_url(item)
