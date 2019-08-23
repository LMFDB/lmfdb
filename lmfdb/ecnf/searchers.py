from urllib import unquote
from lmfdb.ecnf.WebEllipticCurve import convert_IQF_label
from lmfdb.utils import nf_string_to_label
def ecnf_simple_label_search(search, baseurl, label):

    label_bits = label.split('/')
    try:
        nf = label_bits[0]
        conductor_label = label_bits[1]
        class_label = label_bits[2]
        number = label_bits[3]
    except IndexError:
        search['query']={'label':'dummy'}
        return

    conductor_label = unquote(conductor_label)
    conductor_label = convert_IQF_label(nf,conductor_label)
    try:
        nf_label = nf_string_to_label(nf)
    except ValueError:
        search['query']={'label':'dummy'}
        return

    label = "".join(["-".join([nf_label, conductor_label, class_label]), number])

    search['query']={'label':label}
