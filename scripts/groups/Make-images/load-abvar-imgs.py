import sys, os, json
HOME=os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'sage', 'lmfdb'))
from lmfdb import db

import base64

imdict = {}

# load the old images
for ent in db.av_fq_teximages.search():
    imdict[ent['label']] = ent['image']


# load the new ones, overwriting the old where applicable
with open("prettyindex", "r") as fn:
    for line in fn:
        l = json.loads(line.strip().replace("\\", "\\\\"))
        with open('images/eq%d.png'% l[0], "rb") as fn2:
            imdict[l[1]] = 'data:image/png;base64,'+base64.b64encode(fn2.read()).decode("utf-8")

# Have all the image loaded

with open("imagereloader", "w") as afile:
    _ = afile.write('label|image\ntext|text\n\n')
    for key, value in imdict.items():
        _ = afile.write(key.replace('\\', '\\\\') + '|' + value.replace('\\','\\\\') + '\n')

db.av_fq_teximages.reload('imagereloader')
