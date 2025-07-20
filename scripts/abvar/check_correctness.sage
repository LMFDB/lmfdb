from collections import defaultdict
sys.path.append("../..") 
from lmfdb import db

counts_filenames = ["counts23_0_1728.txt", "counts.txt"]

counts  = defaultdict(int)

def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False
    
for filename in counts_filenames:
    with open(filename, "r") as file:
        for line in file:
            line = line.strip()
            line = line.replace(" ", "")
            if not line: 
                continue
            tokens = line.split(",")
            
            if all(is_int(token) for token in tokens) and len(tokens)>1:
                counts[int(tokens[0])] += int(tokens[1])
                
lmfdb_counts = db.av_fq_isog.stats.column_counts(["g", "q"])

for key in sorted(counts.keys()):
    assert lmfdb_counts[(1, key)] == counts[key]

print("SUCCESS: we just verified that the number of labels in our output matches the lmfdb data.")
    