from sage.all import *
import tempfile, os

# in the webserver py file you have to :
# @app.route("/plot")
# @cached()
# def plot():
#     data = lib.plotit(**request.args)
#     response = make_response(data)
#     response.headers['Content-type'] = 'image/png'
#     return response



def plotit(k):
    k = int(k[0])
    #FIXME there could be a filename collission
    fn = tempfile.mktemp(suffix=".png")
    x = var('x')
    p = plot(sin(k*x))
    p.save(filename = fn)
    data = file(fn).read()
    os.remove(fn)
    return data

