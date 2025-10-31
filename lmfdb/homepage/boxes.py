import os
import yaml
from flask import url_for
from sage.all import cached_function


class Box():
    def __init__(self, data):
        self.title = data["title"]
        self.img = url_for('static', filename=f'images/{data["image"]}.png')
        if self.title == "Announcements":
            # Dynamic content generated from knowl
            from lmfdb.knowledge.knowl import knowldb
            from lmfdb.knowledge.main import md
            max_entries = 3
            content = [line.strip() for line in
                       knowldb.get_knowl("content.announcements", ["content"])["content"].split("\n")]
            # Only keep lines that are part of an unordered list
            content = [line for line in content if line.startswith("* ") or line.startswith("- ") or line.startswith("+ ")]
            overflow = len(content) > max_entries
            content = content[:max_entries]
            content = "\n".join(content)
            if overflow:
                content += "\n* [More...](/announcements)&nbsp;&nbsp;&nbsp;&nbsp;(and [ongoing projects](/ongoing))"
            else:
                content += "\n* See also [ongoing projects](/ongoing)"
            self.content = md.convert(content)
        else:
            self.content = data["content"]

@cached_function
def load_boxes():
    _curdir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(_curdir, "index_boxes.yaml")) as boxfile:
        return [Box(b) for b in yaml.load_all(boxfile, Loader=yaml.FullLoader)]
