null_type = 0
integer_type = 1
numeric_type = 2
string_type = 4
bool_type = 8
datetime_type = 16
comma_separated_list = 32
python_collection = 64
python_list = 128
python_dict = 256
python_tuple = 512
python_other = 1024
python_mixed = 2048

import datetime

def is_same_type(object1, object2, strict=True):

    if object1 == object2:
        return object1
    if object1 == python_other or object2 == python_other:
        return python_other
    if strict:
        raise TypeError
    #if doing weak testing then all numeric types are reals
    #because if both types were an integer then the first
    #condition would have matched them
    if object1 & numeric_type and object2 & numeric_type:
        return numeric_type
    raise TypeError

def is_collection(object):

    same_type = False
    subtype = None
    if type(object) is list:
        for el in object:
            t = get_object_id(el)
            if subtype == None:
                subtype = t
                continue
            try:
                subtype = is_same_type(subtype, t, strict = False)
            except TypeError:
                subtype = python_mixed
                break
            if subtype == python_other:
                break
        return python_list | python_collection | subtype

    if type(object) is tuple:
        for el in object:
            t = get_object_id(el)
            if subtype == None:
                subtype = t
                continue
            try:
                subtype = is_same_type(subtype, t, strict = False)
            except TypeError:
                subtype = python_mixed
                break
            if subtype == python_other:
                break
        return python_tuple | python_collection | subtype

    if type(object) is dict:
        for el in object:
            t = get_object_id(object[el])
            if subtype == None:
                subtype = t
                continue
            try:
                subtype = is_same_type(subtype, t, strict = False)
            except TypeError:
                subtype = python_mixed
                break
            if subtype == python_other:
                break
        return python_dict | python_collection | subtype

    raise TypeError

def is_base_type(object):

    bv = null_type
    if type(object) is bool:
        bv = bv | numeric_type
        bv = bv | bool_type
        return bv

    if type(object) is datetime.datetime or \
       type(object) is datetime.time or \
       type(object) is datetime.date:
        bv = bv | type_datetime
        return bv

    try:
        f = float(object)
        bv = bv | numeric_type
        if is_string(object):
            bv = bv | string_type
        if (f.is_integer()):
            bv = bv | integer_type
        return bv
    except:
        pass

    if is_string(object):
        return is_string_of(object)

    # At this point it isn't actually a basic object
    raise TypeError

def is_string(object):
    to = type(object)
    if to is str or to is unicode:
        return True
    return False

def is_string_of(object):

    splits=object.split(',')
    if splits[0] is object:
        return string_type

    sub_type = None
    for x in splits:
        try:
            r_type = is_base_type(x)
        except TypeError:
            sub_type = python_other
            break
        if sub_type is None:
            sub_type = r_type
            continue
        try:
            sub_type = is_same_type(r_type, sub_type, strict=False)
        except:
            sub_type = python_mixed
            break
    if sub_type == string_type:
        return string_type
    return string_type | comma_separated_list | sub_type

def get_object_id(object):
    try:
        rv = is_base_type(object)
    except TypeError:
        try:
            rv = is_collection(object)
        except TypeError:
            rv = python_other
    return rv

def get_description(object):
    rstring=''
    otype = get_object_id(object)
    if otype == python_other:
        return 'non-primitive type (' + str(type(object)) + ')'
    if otype & python_collection:
        rstring += 'collection of '
    if otype & string_type:
        if otype & comma_separated_list:
            rstring += 'comma separated list of '
        else:
            if not otype & numeric_type:
                rstring += 'string '
    if otype & numeric_type:
        if otype & integer_type:
            rstring += 'integer '
        elif otype & bool_type:
            rstring += 'boolean'
        else:
            rstring += 'real '
        if otype & string_type:
            rstring += 'stored as string '
    elif otype & datetime_type:
        rstring += 'tate and or time'
        if otype & string_type:
            rstring += 'stored as string '
    elif otype & python_mixed:
        rstring += 'mixed types '
        if otype & string_type:
            rstring += 'stored as string '
    elif otype & python_other:
        rstring += 'unidentifiable types '
    return rstring.strip()
