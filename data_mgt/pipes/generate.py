from lfunctions import *


up = populator("test","l_main")

def char_db():
    for x in dirichlet_l_iterator(max_conductor = 20):
        up(lf_data(x))

def artin_db():
    for x in artin_l_iterator(max_conductor = 5):
        up(lf_data(x))

def ec_db():
    for x in ec_l_iterator(min_conductor = 1, max_conductor = 30):
        up(lf_data(x))

def hgm_db():
    for x in hypergeometric_l_iterator(max_conductor = 30):
        up(lf_data(x))

