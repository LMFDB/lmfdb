import shutil
import re

def fix_quotes(filename,tmpfile):
    sublist_finder = re.compile(r"(\[[^\]]*\])")
    with open(filename) as infile:
        with open(tmpfile,'w') as fixedfile:
            for L in infile.readlines():
                parts = sublist_finder.split(L[1:-2].replace(" ",""))
                #parts[5] = '["' + parts[5][1:-1].replace(',','","') + '"]'
                #parts[11] = '[[' + parts[11][1:-1] + ',1]]'
                parts[13] = '["' + parts[13][1:-1].replace(',','","') + '"]'
                fixedfile.write('[' + ''.join(parts) + ']\n')
    shutil.move(tmpfile,filename)
