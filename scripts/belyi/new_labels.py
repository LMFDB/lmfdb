convert_label(rec):
    """
    Convert old labels (with square brackets) to new shorter labels.
    """
    old_label = rec['label']
    spl = old_label.split('-')
    return "{}-{}-{}-{}-{}".format(spl[0],spl[2],spl[3],spl[4],spl[6])

update_label(rec):
    rec['old_label'] = rec['label']
    rec['label'] = convert_label(rec)
    return rec
