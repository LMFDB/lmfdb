# Written by Paul to inject L-functions into db
# Never tested


    ############################################################################
    ### Injects into the database of all the L-functions
    ############################################################################

    # def inject_database(self, relevant_info, time_limit = None):
    #    #   relevant_methods are text strings
    #    #    desired_database_fields = [Lfunction.original_mathematical_object, Lfunction.level]
    #    #    also zeros, degree, conductor, type, real_coeff, rational_coeff, algebraic_coeff, critical_value, value_at_1, sign
    #    #    ok_methods = [Lfunction.math_id, Lfunction.level]
    #    #
    #    # Is used to inject the data in relevant_fields
    #
    #    logger.info("Trying to inject")
    #    import base
    #    db = base.getDBConnection().Lfunctions
    #    Lfunctions = db.full_collection
    #    update_dict = dict([(method_name,get_attr_or_method(self,method_name)) for method_name in relevant_info])
    #
    #    logger.info("injecting " + str(update_dict))
    #    search_dict = {"original_mathematical_object()": get_attr_or_method(self, "original_mathematical_object()")}
    #
    #    my_find_update(Lfunctions, search_dict, update_dict)


def my_find_update(the_coll, search_dict, update_dict):
    """ This performs a search using search_dict, and updates each find in
    the_coll using update_dict. If there are none, update_dict is actually inserted.
    """
    x = the_coll.find(search_dict, limit=1)
    if x.count() == 0:
        the_coll.insert(update_dict)
    else:
        for x in the_coll.find(search_dict):
            x.update(update_dict)
            the_coll.save(x)
