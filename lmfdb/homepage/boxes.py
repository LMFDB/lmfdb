import os
import yaml
import re
from flask import url_for
from sage.all import cached_function


class Box():
    def __init__(self, data):
        self.title = data["title"]
        self.img = url_for('static', filename=f'images/{data["image"]}.png')
        self.active = False
        if self.title == "Announcements":
            # Dynamic content generated from knowl
            from lmfdb.knowledge.knowl import knowldb
            from lmfdb.knowledge.main import md
            from lmfdb.utils.datetime_utils import utc_now_naive
            now = utc_now_naive()
            now_month = 12*now.year + now.month
            # We change the background color of the Announcements title bar if one of the displayed announcements is close to now (defined as this month or an adjacent month)
            def check_month(line):
                m = re.match(r".*\(\s*(\d+)\s*/\s*(\d+)\s*\)", line)
                if m:
                    month, year = int(m.group(1)), int(m.group(2))
                    if year < 100:
                        year += 2000
                    total_month = 12*year + month
                    if abs(now_month - total_month) <= 1:
                        self.active = True
            max_entries = 4
            content = [line.strip() for line in
                       knowldb.get_knowl("content.announcements", ["content"])["content"].split("\n")]
            with open(os.path.expanduser("~/blue.txt"), "w") as F:
                _ = F.write(str(content))
            # Only keep lines that are part of an unordered list
            content = [line for line in content if line.startswith("* ") or line.startswith("- ") or line.startswith("+ ")]
            overflow = len(content) > max_entries
            content = content[:max_entries]
            for line in content:
                check_month(line)
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
