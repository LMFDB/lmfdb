# Guess how to parse an arbitrary file.
# 1) If the file isn't mostly [a-zA-Z0-9 .-_] then ignore it
# 2) Ignore lines beginning with '#' or '//'
# 3) If one of the first 20 lines begins with [ or { start parsing as an array or map from that point
#    Assume lines before are comments
#    Strings may or may not be surrounded by '', or "", or `'
# 4) Otherwise it must either be csv comma seperated, tab seperated, or space seperated
#    If at least 75% of lines contain a comma then csv
#    If at least 75% of lines contain a tab then tsv
#    Otherwise, space seperated
# The individual items are attempted to be parsed progressively as an int,
# a float, and a string, skipped if empty


from curses.ascii import isgraph, isspace
import csv
import re
import sys
import json

from pymongo.connection import Connection
try:
  from bson.objectid import ObjectId
except ImportError:
  from pymongo.objectid import ObjectId

from gridfs import GridFS

# Try to parse each element progressively as an int, a float, and a string


def parseSingle(i):
    try:
        assert abs(i) < 1000000000000000000
        return int(i)
    except:
        try:
            return float(i)
        except:
            i = i.strip()
            l = len(i)
            if l >= 2 and i[0] == '"' and i[l - 1] == '"':
                return i[1:-1]
            if l >= 2 and i[0] == "'" and i[l - 1] == "'":
                return i[1:-1]
            if l >= 2 and i[0] == "`" and i[l - 1] == "'":
                return i[1:-1]
            return i

# def myJsonishParse(r):


# Take all non-empty lines not beginning with '#' or '//'
def Lines(r):
    for line in r:
        line = line.strip()
        if not line.startswith("#") and not line.startswith("//") and len(line) > 0:
            yield line


def guessParsing(file1):
    # Look at the lines in the first 10000 chars for clues on the type.
    # disabled /*If the lines are around at least 1000 chars longs, assume it is binary*/
    # If there are unprintable characters then binary
    if not all([isgraph(c) or isspace(c) for c in file1.read(10000)]):
        print "Binary file"
        parsed_as = 'Binary file'
        return parsed_as, None
    file1.seek(0)
    firstlines = file1.read(10000).splitlines()
    # if len(''.join(firstlines))/len(firstlines) >= 1000:
        # print "IGNORE"
    # print firstlines
    # file1.seek(0)

    # ret = json.loads(file1)

    percentContainingComma = len([1 for line in firstlines if line.find(',') != -1]) * 100 / len(firstlines)
    # numberOfSquareBrackets = len([1 for line in firstlines if line.find('[')!=-1])

    file1.seek(0)

    lines = list(Lines(file1.read().splitlines()))
    # print lines

    if len(lines) == 0:
        print "Empty file"
        parsed_as = 'Empty file'
        return parsed_as, []

    beginsWithBrackets = [line.startswith('{') or line.startswith('[') for line in lines[0:20]]

    if any(beginsWithBrackets):
        text = ' '.join(lines[beginsWithBrackets.index(True):])
        text = re.sub(r', *([\]\}])', '\\1', text)
        if re.search(r'} *{', text) is not None:
            print "List of json maps"
            text = re.sub(r'} *{', '},{', text)
            text = '[' + text + ']'
        if re.search(r'\] *\[', text) is not None:
            print "List of json maps"
            text = re.sub(r'\] *\[', '],[', text)
            text = '[' + text + ']'

        try:
            print text
            ret = json.loads(text)
            print "Valid JSON"
            parsed_as = 'Valid JSON'
            return parsed_as, ret
        except:
            pass
        # print text
        text = re.sub(r'([\[\{,]) *([^" ])', '\\1"\\2', text)
        text = re.sub(r'([^" ]) *([\]\},])', '\\1"\\2', text)
        text = re.sub(r'"([0-9]+\.?[0-9]*e?[0-9]*)"', '\\1', text)
        # print text
        try:
            # print text
            ret = json.loads(text)
            print "Almost valid JSON"
            parsed_as = 'Almost valid JSON (multiple entries not explicitly in an array)'
            return parsed_as, ret
        except:
            pass

        # ParseArrayOrMap(text)

    # try:
    #  ParseArrayOrMap(' '.join(lines))
    # except:
    # print lines

    if percentContainingComma > 50:
        print "CSV"
        parsed_as = 'CSV (does not begin with bracket, most lines contain a comma)'
        ret = csv.reader(lines, delimiter=',')
        # ret = [line.split(',') for line in lines]
    else:
        parsed_as = 'SSV (does not begin with bracket, most lines do not contain a comma)'
        print "SSV"
        # print lines
        ret = csv.reader(lines, delimiter=' ', skipinitialspace=True)
        # ret = [line.split(' ') for line in lines]

    ret = [[parseSingle(i) for i in row] for row in ret]

    if len(ret) == 1:
        ret = ret[0]
    elif all([len(row) == 1 for row in ret]):
        ret = [row[0] for row in ret]

    return parsed_as, ret

if len(sys.argv) == 2:
    file1 = open(sys.argv[1], "r")
    print guessParsing(file1)[1]
    quit()

from lmfdb.website import DEFAULT_DB_PORT as dbport
db = Connection(port=dbport)
fs = GridFS(db.upload)
for entry in db.upload.fs.files.find({"$or": [{"metadata.status": "approved"}, {"metadata.status": "approvedchild"}]}, sort=[("uploadDate", -1)]):
    print '%s: %s (%s)' % (entry['_id'], entry['filename'], str(entry['uploadDate']))
    name = entry['metadata']['uploader_id'] + str(entry['_id'])
    file = fs.get(entry['_id'])
    # print list(Lines(file.read(1000).splitlines()))
    # file.seek(0)
    # print list(Lines(file.read(1000).splitlines()))
    # file.seek(0)
    parsed_as, data = guessParsing(file)
    db.upload.fs.files.update({"_id": ObjectId(entry['_id'])}, {"$set": {"metadata.parsed_as": parsed_as}})
    if data is None:
        continue
    if type(data) is dict:
        data = [data]
    # for row in data:
        # print row
    c = db.contrib.create_collection(name)  # db.contrib[entry['metadata']['uploader_id']+str(entry['_id'])]
    c.remove()
    for row in data:
        if type(row) is not dict:
            row = {"data": row}
        c.insert(row)
