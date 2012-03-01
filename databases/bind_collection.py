from base import getDBConnection
from pymongo.collection import Collection
from databases import databases_logger

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
        databases_logger.debug(str(self)+ " ASKED: "+str(args)+str(kwargs)+str( self._type_conversion))
        for x in self.find(*args, **kwargs):
            databases_logger.debug("found one:",x)
            yield self._type_conversion(x)

    def find_and_convert_one(self, *args, **kwargs):
        databases_logger.debug( str(self) + " ASKED: " + str( args) +str( kwargs)+str( self._type_conversion))
        print  self, "ASKED: ", args, kwargs, self._type_conversion
        x = self.find_one(*args,**kwargs)
        databases_logger.debug("GOT " +str( x))
        y = self._type_conversion(x)
        databases_logger.debug("CONVERTED TO "+str(y))
        return y
