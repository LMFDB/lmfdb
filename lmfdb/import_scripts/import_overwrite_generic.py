# File importing a json file to the mongodb database
# Usage: python import_generic.py filename.json database_name.collection_name
# A safeguard is currently inserted, making sure database_name == "limbo"
# because there is a risk of overwriting an already existing collection

import sys

def main(argv):
    file_name = argv[0]
    database_collection = argv[1]
    assert "." in database_collection
    database_name, collection_name = database_collection.split(".")
    # If you know what you are doing, remove the line below.
    # In general you should just avoid using this with an existing collection as it might overwrite information
    assert database_name == "limbo"

    print "Importing file ", file_name, " to database ", database_name, " and collection ", collection_name
    import json
    import sys
    sys.path.append("../")
    import base
    print "getting connection"
    base._init(37010, "")
    print "I have it"

    C = base.getDBConnection()
    
    collection = C[database_name][collection_name]
    print "Got a collectiopn: ", collection
    with open(file_name, "r") as f:
        print "Loading data in memory"
        data = json.load(f)
        print "Done"
	print "There are ", len(data), " items "
        import sys
        sys.path.append("../")
        print "Uploading"
        for x in data:
            try:
                collection.save(x)
            except OverflowError:
                print x
                raise OverflowError
        print "Done"

if __name__ == "__main__":
   main(sys.argv[1:])
