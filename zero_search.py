from base import app, C

@app.route("/zero_search")
@app.route("/zero_search/")
@app.route("/zero_search/<zero>")
def zero_search(zero = None):
    if not zero:
        return "zero search page"
    else:
        zero = float(zero)
        L = C.Lfunctions.first_zeros_testing.find({'zero' : {'$lt' : zero + .1, '$gt' : zero - .1 } }).sort('zero')
        result_string = ""
        printed_arrow = False
        for x in L:
            if x['zero'] > zero and printed_arrow == False:
                result_string = result_string + "-------->"
                printed_arrow = True
            result_string = result_string + str(x['zero']) + " " + str(x['modulus']) + " " + str(x['character']) + "<br>\n"
        return result_string
