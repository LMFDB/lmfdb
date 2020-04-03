def add_dot_seps(string):
    new = ""
    for c in string[:-1]:
        new += c+"."
    new+=string[-1]
    return new

def convert_label(rec):
    """
    Convert old labels (with square brackets) to new shorter labels.
    """
    old_label = rec['label']
    spl = old_label.split('-')
    return "{}-{}_{}_{}-{}".format(spl[0],add_dot_seps(spl[2]),add_dot_seps(spl[3]),add_dot_seps(spl[4]),spl[6])

def update_label(rec):
    rec['old_label'] = rec['label']
    rec['label'] = convert_label(rec)
    return rec
