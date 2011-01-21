
from WebLfunction import *

def TestLfunction(dict):
    L1=WebLfunction({"type": "modularform", "level": 3, "weight": 6})
    L2=WebLfunction({"type": "lcalcurl", "url": "http://www.math.chalmers.se/~sj/pub/gl3Maass/Data/sl3Maass1.txt"})
    return [L1,L2]
