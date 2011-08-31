def setPageLinks(info, L, args):
    info['friends'] =[]
    try:
        if args['type'] == 'riemann':
            info['friends'].append(('\(GL(1)\) twists', '/L/Character/Dirichlet'))
        elif  args['type'] == 'lcalcurl':
            info['friends'].append(('Maass form', '/L/TODO'))
        elif  args['type'] == 'gl2holomorphic':
            None
        elif  args['type'] == 'gl2maass':
            info['friends'].append(('Maass form', url_for( 'render_maass_form', **args)))
        elif  args['type'] == 'gl3maass':
            None
        elif  args['type'] == 'dirichlet':
            info['friends'].append(('Character', '/L/TODO'))
            info['friends'].append(('L-functions with same conductor', '/L/Character/Dirichlet?start=' + str(args['charactermodulus']) + '&length=1'))
    except:
        None
        
    info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-functions') ]
    
    try:
        info['downloads'] = [('Lcalc file', L.url) ,('Coefficients', '/L/TODO') \
                       ,('The computation', '/L/TODO')]
    except:
        info['downloads'] =[]
    return info
