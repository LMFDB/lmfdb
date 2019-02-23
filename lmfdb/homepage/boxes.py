import yaml
from sage.all import cached_function

class Box(object):
    def __init__(self, title):
        self.title = title
        self.content = None
        self.links = []
        self.target = "/"
        self.img = None

    def add_link(self, title, href):
        self.links.append((title, href))

@cached_function
def load_boxes():
    boxes = []
    listboxes = yaml.load_all(open(os.path.join(_curdir, "index_boxes.yaml")))
    for b in listboxes:
        B = Box(b['title'])
        B.content = b['content']
        if 'image' in b:
            B.img = url_for('static', filename='images/'+b['image']+'.png')
        for title, url in b['links']:
            B.add_link(title, url)
        boxes.append(B)
    return boxes
