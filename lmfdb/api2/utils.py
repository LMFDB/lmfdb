import datetime
import lmfdb.api2

api_version = lmfdb.api2.__version__

def build_api_structure(api_key, record_count, view_start, view_count, record_list, \
                        max_count=None):
    """
    Build an API object from a set of records. Automatically calculates point to start view to get next record.
    'View' is the concept of which part of all of the records returned by a query is contained in _this_ api response

    Arguments:
    api_key -- Named API key as registered with register_search_function
    record_count -- Total number of records returned by the query
    view_start -- Point at which the current view starts in records
    view_count -- Number of records in the current view. Must be less than max_count if max_count is specified
    record_list -- Dictionary containing the records in the current view

    Keyword arguments:
    max_count -- The maximum number of records in a view that a client can request. This should be the same as
                 is returned in the main API page unless this value cannot be inferred without context

    """
    view_count = min(view_count, record_count-view_start)
    next_block = view_start + view_count if view_start + view_count < record_count else -1
    keys = {"key":api_key, "record_count":record_count, "view_start":view_start, "view_count":view_count, \
            "view_next":next_block,"records":record_list,'built_at':str(datetime.datetime.now()), 'api_version':api_version}
    if max_count: keys['api_max_count'] = max_count
    return keys

def default_projection(info):
    """
    Build a projection from an info dictionary as returned by flask. _id always excluded

    Keywords of info dict used:
    exclude -- logical for whether to build an inclusive or exclusive projection (default False)
    fields -- comma separated list of fields to include (exclude if keyword set)

    """
    try:
        fields = info['fields'].split(',')
        exclude = False
        try:
            info['exclude']
            exclude = True
        except:
            pass
        project = build_query_projection(fields, exclude = exclude)
    except KeyError:
        project = None
    return project

def build_query_projection(field_list, exclude=False):
    """
    Builds a PyMongo compatible query projection dictionary

    Arguments:
    field_list -- List of fields to include (exclude if keyword set)

    Keyword arguments:
    exclude -- logical for whether to build an inclusive or exclusive projection (default False)

    """
    keys = {"_id":0}
    val = 1
    if exclude: val = 0
    for el in field_list:
        keys[el] = val
    return keys
