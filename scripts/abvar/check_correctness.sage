sys.path.append("../..") 
from collections import defaultdict
from lmfdb import db

'''
Reads files from counts_filenames, and for each prime power q,
add the number of isogeny labels of genus 1 over F_q
from each of the files. Then we check if it matches the LMFDB data.
'''

counts_filenames = ["counts23_0_1728.txt", "counts.txt"]

counts  = defaultdict(int)
    
for filename in counts_filenames:
    with open(filename, "r") as file:
        for line in file:
            line = line.replace(" ", "")
            if not line: 
                continue
            tokens = line.split(",")
            
            if all(token.isdigit() for token in tokens) and len(tokens)>1:
                counts[int(tokens[0])] += int(tokens[1])
                
lmfdb_counts = db.av_fq_isog.stats.column_counts(["g", "q"])

for key in sorted(counts):
    assert lmfdb_counts[(1, key)] == counts[key], "Number of labels for q=%s does not match." % (key)

print("SUCCESS: we just verified that the number of labels in our output matches the lmfdb data.")