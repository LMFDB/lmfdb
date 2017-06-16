from pymongo.collection import Collection
from lmfdb.artin_representations.databases import databases_logger


def bind_collection(name, type_conversion):
    database, collection = name

    def tmp(connection):
        return ExtendedCollection(connection[database], collection, type_conversion)
    return tmp


class ExtendedCollection(Collection):
    def __init__(self, database, collection_name, type_conversion):
        self._type_conversion = type_conversion
        Collection.__init__(self, database, collection_name)

    def find_and_convert(self, *args, **kwargs):
        databases_logger.debug(str(self) + " ASKED: " + str(args) + str(kwargs) + str(self._type_conversion))
        if len(args) == 0:
            iter_search = self.find(kwargs)
        else:
            iter_search = self.find(*args, **kwargs)
        for x in iter_search:
            # databases_logger.debug("found one:",x)
            yield self._type_conversion(x)

    def find_and_convert_one(self, *args, **kwargs):
        databases_logger.debug(str(self) + " ASKED: " + str(args) + str(kwargs) + str(self._type_conversion))
        ####
        # Watch out, subtle bugs can be introduced if using this from the sage command-line, due to the sage interpreter
        # The integers are all wrapped to be sage integers, which causes problems if you store int s in the database
        # POD
        if len(args) == 0:
            x = self.find_one(kwargs)
        else:
            x = self.find_one(*args, **kwargs)
        databases_logger.debug("GOT " + str(x))
        y = self._type_conversion(x)
        # databases_logger.debug("CONVERTED TO "+str(y))
        return y
