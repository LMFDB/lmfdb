
from . import utils

searchers = {}
singletons = {}

class searcher:

    def get_name(self):
        return self.human_name

    def get_description(self):
        return self.desc

    def get_info(self):
        if (self._full_info):
            return self._full_info()
        return utils.get_filtered_fields(self._inv)

    def get_inventory(self):
        if(self._full_inventory):
            return self._full_inventory()
        return utils.get_filtered_fields(self._inv)

    def auto_search(self, request):
        info = self.get_info()
        sd = utils.create_search_dict(self.auto, request = request)
        cnames = utils.get_cname_list(info)
        for el in request.args:
            try:
                itt = info[el]['type']
            except KeyError:
                itt = None
            if (el in cnames):
                utils.interpret(sd['query'], cnames[el], request.args[el], itt)
            else:
                utils.interpret(sd['query'], el, request.args[el], itt)
        proj = utils.default_projection(request,cnames=cnames)
        return self.get_search(sd, proj)

    def get_search(self, query, projection):
        if(self._full_search):
            return self._full_search(query, projection)
        return utils.simple_search(query, projection)

    def __init__(self, human_name, desc, auto_search = None, full_info=None, full_inventory=None, full_search=None, inv=None ):
        self.human_name = human_name
        self.desc = desc
        self.auto = auto_search
        self._inv = inv
        if not self._inv and self.auto:
            self._inv = [self.auto.split("_", 1)[0], self.auto]
        self._full_info = full_info
        self._full_inventory = full_inventory
        self._full_search = full_search

def register_search_function(name, human_name, description, auto_search=None, full_info=None, full_inventory=None, full_search=None, inv=None):
    """
    Register a search function with the contextual API system

    Arguments:
    name -- Name of the api_key. This is used to uniquely identify a search function
    human_name -- Name of the API entry presented to users
    description -- Description of the search feature that is enabled by this API key
    auto_search -- Table name to search in. Should be filled if this searcher is just an
    inventory mediated search on a single database and collection
    full_info -- Function that is called to get information about a searcher. Returns JSON document. Only populate if you
    need to have full control over the info
    full_inventory -- Function that is called to get information about what keys can be returned by a searcher. Only populate if you
    need to have full control over the keys that can be returned
    full_search -- Search function to be called when a query is made through the API. Returns an api_structure (see api2/utils.py).
    Only populate if you want to have full control over the search return

    """
    global searchers
    searchers[name] = searcher(human_name, description, auto_search = auto_search, full_info = full_info, full_inventory = full_inventory, full_search = full_search, inv=inv)

def register_singleton(url, table, key = None, simple_search = None, full_search = None):
    """
    Register an API singleton. This is a search that should find a single item
    from a label or similar key

    Arguments:
    url -- The URL of the singleton in the main LMFDB. This will become /api2/singletons/{url}
    table -- The table to search in
    key -- The field in the table to search in
    simple_search -- A function that modifies a query object to make it search for the requested object
    full_search -- A function that performs a search itself and returns the results
    """

    global singletons
    singletons[url] = {'table':table, 'key':key,
        'simple_search':simple_search, 'full_search':full_search}
