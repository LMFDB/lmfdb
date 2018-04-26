searchers = {}

def register_search_function(name, info, search):
    """
    Register a search function with the contextual API system

    Arguments:
    name -- Name of the api_key. This is used to uniquely identify a search function
    info -- Function that is called to get information about a searcher. Returns JSON document
    search -- Search function to be called when a query is made through the API. Returns an api_structure (see api2/utils.py)

    """
    global searchers
    searchers[name] = (info, search)
