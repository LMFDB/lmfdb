##import sys
##sys.path.append("C:\Users\Stefan\Documents\Python")
from pymongo import Connection

##info = {'title': 'L-functions corresponding to \(GL(3)\) Maass forms, level 4'}
##info['id'] = 'L/ModularForm/GL3/Q/maass/4'
##info['objecttitle'] = 'L - functions'
##info['credit'] = 'Created by David Farmer, Sally Koutsoliotas and Stefan Lemurell'
##info['degree'] = 3
##info['friends_data'] = [('\(GL(3)\) Maass forms', 'ModularForm/GL3/Q/maass/4')]
##info['sibling_data'] = [('\(GL(3)\), level 4', 'L/ModularForm/GL3/Q/maass/1')]
##info['parent_data'] = [('L-functions, degree 3', 'L?degree=3')]
##info['children_data'] = []
##info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-functions') ]
##info['downloads'] = [('Spectral parameters', '/L/TODO') ,('Coefficients', '/L/TODO') \
##                   ,('The computation', '/L/TODO')]
##info['properties'] = ['Degree = ' + str(info['degree']), 'Primitive' , 'Non-selfdual']
##f = open('contentGL3Level4.html')
##info['contents'] =f.read()
##f.close()
##
##connection = Connection()
##db = connection.Lfunction
##collection = db.LNavigation
##collection.insert(info)

########----------------------------------------------
info = {'title': 'L-functions corresponding to \(GL(3)\) Maass forms, level 1'}
info['id'] = 'L/ModularForm/GL3/Q/maass/1'
info['objecttitle'] = 'L - functions'
info['credit'] = 'Created by David Farmer, Sally Koutsoliotas and Stefan Lemurell'
info['degree'] = 3
info['friends_data'] = [('\(GL(3)\) Maass forms', 'ModularForm/GL3/Q/maass/1')]
info['sibling_data'] = [('\(GL(3)\), level 4', 'L/ModularForm/GL3/Q/maass/4')]
info['parent_data'] = [('L-functions, degree 3', 'L?degree=3')]
info['children_data'] = []
info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-functions') ]
info['downloads'] = [('Spectral parameters', '/L/TODO') ,('Coefficients', '/L/TODO') \
                   ,('The computation', '/L/TODO')]
info['properties'] = ['Degree = ' + str(info['degree']), 'Primitive' , 'Non-selfdual']
f = open('plotOfEigenvalues.html')
info['contents'] =f.read()
f.close()

connection = Connection(port=37010)
db = connection.Lfunction
collection = db.LNavigation
collection.insert(info)

########----------------------------------------------

info = {'title': 'Dirichlet L-functions'}
info['id'] = 'L/Character/Dirichlet'
info['objecttitle'] = 'L - functions'
info['credit'] = 'Computed using SAGE and lcalc'
info['degree'] = 1
info['friends_data'] = [('Dirichlet characters', 'Character/Dirichlet')]
info['sibling_data'] = [('Zeta-function', 'L/Zeta')]
info['parent_data'] = [('L-functions, degree 1', 'L?degree=1')]
info['children_data'] = []
info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-functions') ]
info['downloads'] = []
info['properties'] = ['Degree = ' + str(info['degree']), 'Primitive' ]
info['contents'] = ''

connection = Connection(port=37010)
db = connection.Lfunction
collection = db.LNavigation
collection.insert(info)

########----------------------------------------------

info = {'title': 'L-functions'}
info['id'] = 'L'
info['objecttitle'] = 'L - functions'
info['credit'] = ''
info['degree'] = ''
info['friends_data'] = []
info['sibling_data'] = []
info['parent_data'] = []
info['children_data'] = []
info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-functions') ]
info['downloads'] = []
info['properties'] = []
f = open('lfuncMainStrip.html')
info['contents'] =f.read()
f.close()


connection = Connection(port=37010)
db = connection.Lfunction
collection = db.LNavigation
collection.insert(info)
#########----------------------------------------------
info = {'title': 'Coming soon to a computer close to you'}
info['id'] = 'L/TODO'
info['objecttitle'] = 'L - functions'
info['credit'] = ''
info['degree'] = ''
info['friends_data'] = []
info['sibling_data'] = []
info['parent_data'] = []
info['children_data'] = []
info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-functions') ]
info['downloads'] = []
info['properties'] = []
info['contents'] = 'This page has not been created yet.'

connection = Connection(port=37010)
db = connection.Lfunction
collection = db.LNavigation
collection.insert(info)
