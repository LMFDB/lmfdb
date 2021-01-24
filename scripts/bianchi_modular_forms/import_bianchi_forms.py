# -*- coding: utf-8 -*-
r""" Import newforms to Bianchi database of newforms

Initial version (Warwick June 2017): John Cremona
Revised for postgres (2020)

The LMFDB database has two tables for Bianchi Modular Form data, "bmf_dims" and "bmf_forms".

The "bmf_forms" table has the following 21 columns:

   - 'id':             (bigint): unique identifier
   - 'field_label':    (text) label of the number field, e.g. '2.0.4.1'
   - 'field_disc':     (smallint) absolute value of discriminant of the number field, e.g. 4
   - 'field_deg':      (smallint) degree of the number field, namely 2
   - 'level_label':    (text)  label of the level ideal, e.g. '[1,0,1]'
   - 'level_norm':     (bigint)  norm of the level ideal, e.g. 65
   - 'level_ideal':    (text)  defining data of the level ideal, e.g. [25,25,4*w-3]
   - 'level_gen':      (text)  generator of the level ideal, e.g. 7+4i
   - 'label_suffix':   (text) letter code for the newform at fixed level: a, b, c, ...
   - 'label_nsuffix':  (smallint) numerical version of label_suffix (1 for a, 2 for b etc)
   - 'short_label':    (text) 'level_label' + '-' + 'label_suffix' (= label without the field part)
   - 'label':          (text) 'field_label' + '-' + 'level_label'
   - 'dimension':      (smallint) degree of Hecke field (e.g. 1)
   - 'hecke_poly':     (text) min poly in x of Hecke field (e.g. 'x')
   - 'weight':         (smallint) weight (e.g. 2)
   - 'sfe':            (smallint) sign of functional equation (+1 or -1)
   - 'Lratio':         (text) rational L(1)/period as a string (e.g. '0')
   - 'bc':             (smallint) d>0 if form is base change from Q with eigs in Q(sqrt(d)),
                                  0 if not base-change,
                                  d<0 if form is twist of base change from Q with eigs in Q(sqrt(|d|))
   - 'CM':             (smallint) d<0 if CM by Q(sqrt(d)), 0 or None if not CM
   - 'AL_eigs':        (jsonb) (list of ints or strings) Atkin-Lehner eigenvalues: list of +1/-1, or list of '?'

   - 'hecke_eigs':     (jsonb) (list of ints or strings) Hecke eigenvalues:
                                ints for dimension 1, else strings giving eigs as polynomials of degree dim-1 in z.

NB 1. Both AL_eigs and hecke_eigs are indexed by the primes in standard order
   2. hecke_eigs are ints if dimension=1, else strings

   3. Fields agree with those for Hilbert modular forms except:
     (a) bc is int, not is_base_change as string ("yes"/"no")
     (b) CM is int, not is_CM as string ("yes"/"no")
     (c) parallel_weight is not used as we only have one infinite place
     (d) field_disc replaces disc
     (e) field_deg replaces deg
     (f) hecke_eigs replaces hecke_eigenvalues
     (g) AL_eigs replaces AL_eigenvalues
     (h) hecke_poly replaces hecke_polynomial
     (i) sfe does not exist for HMFs
     (j) Lratio does not exist for HMFs
"""
from __future__ import print_function
from sage.all import polygen, QQ, ZZ, NumberField, PolynomialRing
import re

from lmfdb import db
print("setting dims")
dims = db.bmf_dims
print("setting forms")
forms = db.bmf_forms

whitespace = re.compile(r'\s+')
Qx = PolynomialRing(QQ,'x')

def split(line):
    return whitespace.split(line.strip())

from lmfdb.nfutils.psort import ideal_label

the_labels = {}

def convert_ideal_label(K, lab):
    """An ideal label of the form N.c.d is converted to N.i.  Here N.c.d
    defines the ideal I with Z-basis [a, c+d*w] where w is the standard
    generator of K, N=N(I) and a=N/d.  The standard label is N.i where I is the i'th ideal of norm N in the standard ordering.
    """
    global the_labels
    if K in the_labels:
        if lab in the_labels[K]:
            return the_labels[K][lab]
        else:
            pass
    else:
        the_labels[K] = {}

    comps = lab.split(".")
    # test for labels which do not need any conversion
    if len(comps)==2:
        return lab
    assert len(comps)==3
    N, c, d = [int(x) for x in comps]
    a = N//d
    I = K.ideal(a, c+d*K.gen())
    newlab = ideal_label(I)
    #print("Ideal label converted from {} to {} over {}".format(lab,newlab,K))
    the_labels[K][lab] = newlab
    return newlab

the_fields = {}

def field_from_label(lab):
    r"""
    Returns a number field from its LMFDB label.  Only for 5 IQFs at present.
    """
    global the_fields
    if lab in the_fields:
        return the_fields[lab]
    x = polygen(QQ)
    deg, s, abs_disc, _ = lab.split(".")
    assert deg == '2'
    assert s == '0'
    d = -ZZ(abs_disc)
    t = d%4
    assert t in [0,1]
    pol = x**2 - t*x + (t-d)//4
    K = NumberField(pol, 'a')
    print("Created field from label %s: %s" % (lab,K))
    the_fields[lab] = K
    return K

def numerify_iso_label(lab):
    from sage.databases.cremona import class_to_int
    return class_to_int(lab.lower())


def parse_newforms_line(line):
    r""" Parses one line from a newforms file.  Returns a complete entry
    for the forms collection. This is only for rational newforms of
    weight 2.

    Input line fields:

    field_label level_label level_suffix level_ideal wt bc cm sign Lratio AL_eigs pol hecke_eigs

    Sample input line:

    2.0.4.1 65.18.1 a (7+4i) 2 0 ? 1 1 [1,-1] x [0,0,-1,-2,1,-4,0,6,6,-6,2,2,6,0,-4,6,-6,-10,-10,2,2,6,6,-10,8]

    NB We expect 3-component HNF-style labels for ideals (N.c.d) but will convert to LMFDB labels N.i on input.
    """
    # skip comment lines
    if line[0] == '#':  return '', {}
    if 'Primes' in line:  return '', {}
    if '...' in line:  return '', {}
    data = split(line)
    # base field
    field_label = data[0]
    K = field_from_label(field_label)
    field_disc = - int(field_label.split(".")[2])
    field_deg = 2
    # Hecke field degree (=dimension)
    hecke_poly = data[10]
    dimension = 1 if hecke_poly == 'x' else int(Qx(hecke_poly).degree())
    # level
    level_label = convert_ideal_label(K, data[1])
    level_norm = int(level_label.split(".")[0])
    level_ideal = data[3]
    level_gen =  level_ideal[1:-1] # strip (,)

    label_suffix = data[2]
    label_nsuffix = numerify_iso_label(label_suffix)
    if dimension>1:
        label_suffix = label_suffix+str(dimension)
    short_label = '-'.join([level_label, label_suffix])
    label = '-'.join([field_label, short_label])
    weight = int(data[4])
    bc = data[5]
    if bc!='?': bc=int(bc)
    cm = data[6]
    if cm!='?': cm=int(cm)
    sfe = data[7] # sign
    if sfe!='?': sfe = int(sfe) # sign
    Lratio = data[8]   # string representing rational number
    try:
        AL_eigs = [int(x) for x in data[9][1:-1].split(",")]
    except ValueError:
        AL_eigs = [x for x in data[9][1:-1].split(",")]
    try:
        hecke_eigs = [int(x) for x in data[11][1:-1].split(",")]
    except ValueError:
        hecke_eigs = [x for x in data[11][1:-1].split(",")]

    return label, {
        'label': label,
        'field_label': field_label,
        'field_disc': field_disc,
        'field_deg': field_deg,
        'level_label': level_label,
        'level_norm': level_norm,
        'level_ideal': level_ideal,
        'level_gen': level_gen,
        'label_suffix': label_suffix,
        'label_nsuffix': label_nsuffix,
        'short_label': short_label,
        'dimension': dimension,
        'hecke_poly': hecke_poly,
        'weight': weight,
        'sfe': sfe,
        'Lratio': Lratio,
        'bc': bc,
        'CM': cm,
        'AL_eigs': AL_eigs,
        'hecke_eigs': hecke_eigs,
    }

BIANCHI_DATA_DIR = "/scratch/home/jcremona/bianchi-data"
NEWFORM_DIR      = "/".join([BIANCHI_DATA_DIR,'newforms'])

def read_forms(filename_suffix, base_path=NEWFORM_DIR):
    """Reads newforms from bianchi-data repository.  The data file in
    directory NEWFORM_DIR is of the form "newforms.*"
    (e.g. "newforms.1.1-10000") and only the suffix after "newforms."
    needs to be given.

    Parsing of individual lines is handled by the function parse_newforms_line().

    Returns a dict with keys complete labels and values complete dicts
    with 20 keys one for each column in the table (excluding "id").

    These dicts can be used directly to insert into the table, or to
    update an existing row, or can be output to a file to be read in
    using copy_from() or update_from_file().
    """
    forms_filename = filename_suffix if 'newforms' in filename_suffix else ".".join(["newforms",filename_suffix])
    forms_filename = "/".join([base_path, forms_filename])
    with open(forms_filename) as formfile:
        print("opened {}".format(forms_filename))
        alldata = {}
        count = 0
        for line in formfile.readlines():
            label, data = parse_newforms_line(line)
            if label=='':
                continue
            count += 1
            if count%1000==0:
                print("read {} lines, last label = {}".format(count, label))
            if label in alldata:
                print("Duplicate data for {}".format(label))
            else:
                alldata[label] = data
        print("finished reading {} lines from file {}".format(count, forms_filename))

    return alldata

COL_NAMES = ['field_disc', 'sfe', 'level_gen', 'weight', 'CM', 'bc',
             'field_deg', 'label', 'label_suffix', 'hecke_poly', 'field_label',
             'AL_eigs', 'Lratio', 'level_norm', 'hecke_eigs', 'short_label',
             'level_label', 'label_nsuffix', 'dimension', 'level_ideal'] 

COL_TYPES = ['bigint', 'smallint', 'smallint', 'text', 'smallint',
             'smallint', 'smallint', 'smallint', 'text', 'text', 'text', 'text',
             'jsonb', 'text', 'bigint', 'jsonb', 'text', 'text', 'smallint',
             'smallint', 'text']

def bmf_to_string(id, F):
    """Given a dict F containing the columns of a BMF, return a string
    encoding F in a format suitable for uploading into the database.

    """
    cols = [str(id)] + [str(F[k]) for k in COL_NAMES]    
    return "|".join(cols)

def write_form_data(alldata, filename_suffix, base_path=NEWFORM_DIR, headers=True):
    filename = base_path + "/bmf_forms." + filename_suffix
    with open(filename, 'w') as outfile:
        if headers:
            outfile.write("|".join(['id'] + COL_NAMES) + "\n")
            outfile.write("|".join(COL_TYPES) + "\n\n")
        id = 1
        for data in alldata.values():
            outfile.write(bmf_to_string(id, data) + "\n")
            id +=1
    s = "3 header lines and " if headers else ""
    print("output {}{} data lines to {}".format(s, id-1, filename))


def upload_to_db(filename_suffix, base_path=NEWFORM_DIR, update=True, test=True):
    """Read data from a newforms file and insert it into the database.  If
    update==True (default) this is done using forms.update() so that
    old rows will be updated with the input data.  Otherwise
    (update==False) new rows will be added.

    """
    # read the newforms file
    alldata = read_forms(filename_suffix, base_path)

    # write it to a temporary file in current directory
    tempfilename = filename_suffix+".temp"
    write_form_data(alldata, tempfilename, base_path=".")

    # update the database
    if test:
        print("Table bmf_forms unchanged.  Input data dumped to {}".format(tempfilename))
    else:
        if update:
            print("Updating {} rows from input data".format(len(alldata)))
            for label, data in alldata:
                forms.update({'label': label}, data)
        else:
            print("Inserting {} rows from input data".format(len(alldata)))
            forms.insert_many(alldata.values())
        
def upload_to_db_old(filename_suffix, base_path=NEWFORM_DIR, insert=True, test=True):
    """The old way to upload data.  Better now is to use read_forms() to
    read the newforms file into a dict D and then
    write_form_data(D,...) to output to a file and then
    db.bmf_forms.update_from_file() to do the upload.

    """
    data_to_insert = read_forms(filename_suffix, base_path)
    vals = data_to_insert.values()
    if test:
        print("Test mode: not inserting any data ({} items)".format(len(vals)))
        return vals
    
    if insert:
        print("inserting all data")
        forms.insert_many(vals)
    else:
        count = 0
        print("inserting data one at a time...")
        for val in vals:
            #print val
            forms.update_one({'label': val['label']}, {"$set": val}, upsert=True)
            count += 1
            if count % 100 == 0:
                print("inserted %s" % (val['label']))

# function to compare newforms and curves:
def curve_check(fld, min_norm=1, max_norm=None):
    nfcurves = db.ec_nfcurves
    # first check numbers
    norm_range = {}
    norm_range['$gte'] = min_norm
    if max_norm is not None:
        norm_range['$lte'] = max_norm
    print("Checking field {}, norm range {}".format(fld, norm_range))
    form_query = {'field_label':fld, 'dimension':1, 'level_norm':norm_range}
    curve_query = {'field_label':fld, 'number':1, 'conductor_norm':norm_range}
    nforms = forms.count(form_query)
    ncurves = len([c for c in nfcurves.search(curve_query) if not 'CM' in c['label']])
    if nforms==ncurves:
        print("# curves = # forms = {}".format(ncurves))
    else:
        print("# curves = {} but # forms = {}".format(ncurves, nforms))
    if nforms>ncurves:
        print("{} curves missing".format(nforms-ncurves))
    print("Checking whether there is a curve for each newform...")
    n = 0
    for f in forms.search(form_query):
        lab = f['label']
        nc = nfcurves.count({'class_label':lab})
        if nc==0:
            print("newform {} has no curve (bc={}, cm={})".format(lab,f['bc'],f['CM']))
            n +=1
    if n==0:
        print("no missing curves")
    else:
        print("{} missing curves listed".format(n))
    print("Checking whether there is a newform for each non-CM curve...")
    n = 0
    for f in nfcurves.search(curve_query):
        lab = f['class_label']
        if 'CM' in lab:
            continue
        nf = forms.count({'label':lab})
        if nf==0:
            print("curve class {} has no newform".format(lab))
            n +=1
    if n==0:
        print("no missing newforms")
    else:
        print("{} missing newforms listed".format(n))


def update_ap(field, base_path=NEWFORM_DIR, table=None, check=False):
    # field = 1, 2, 3, 7 or 11 The next line is a lazy way to use old
    # code, though we do not need all the data, this is one way to
    # read it in.
    vals = upload_to_db("{}.all".format(field))
    D = dict([(v['label'], v['hecke_eigs']) for v in vals])
    print("Finished reading data for field {}: {} entries".format(field, len(D)))

    if check:
        # Some db entries have more ap already and we do not want to
        # overwrite these.  At the same time we check for consistency
        # between old and new:
        print("Checking old and new eigs for consistency")
        for label, eigs in D.items():
            old_eigs = forms.lucky({'label':label})['hecke_eigs']
            consistent = all([ap==bp for ap,bp in zip(old_eigs,eigs)])
            if not consistent:
                print("Old and new eigs do not agree for form {}".format(label))
            n_old = len(old_eigs)
            n_new = len(eigs)
            if n_old > n_new:
                print("Old eig list for {} has {} entries, new has {}".format(label, n_old, n_new), end=": ")
                print("Keeping old eigs")
                D[label] = old_eigs

    filename=NEWFORM_DIR+'/temp_{}'.format(field)
    with open(filename, 'w') as F:
        F.write("label|hecke_eigs\ntext|jsonb\n\n")
        for label, eigs in D.items():
            F.write("%s|%s\n" % (label, eigs))
    print("Finished writing data for field {} to {}".format(field, filename))
    if table:
        table.update_from_file(filename)        
    else:
        print("test run: database unchanged")
