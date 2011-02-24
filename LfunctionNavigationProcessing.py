import LfunctionComp

def processDirichletNavigation(info, args):
    print str(args)
    try:
        print args['start']
        N = int(args['start'])
        if N < 3:
            N=3
        elif N > 100:
            N=100
    except:
        N = 3
    try:
        length = int(args['length'])
        if length < 1:
            length = 1
        elif length > 20:
            length = 20
    except:
        length = 10
    try:
        numcoeff = int(args['numcoeff'])
    except:
        numcoeff = 50
    chars = LfunctionComp.charactertable(N, N+length,'primitive')
    s = '<table>\n'
    s += '<tr>\n<th scope="col">Conductor</th>\n'
    s += '<th scope="col">Primitive characters</th>\n</tr>\n'
    for i in range(N,N+length):
        s += '<tr>\n<th scope="row">' + str(i) + '</th>\n'
        s += '<td>\n'
        j = i-N
        for k in range(len(chars[j][1])):
            s += '<a href="Dirichlet?charactermodulus='
            s += str(i)
            s += '&characternumber='
            s += str(chars[j][1][k])
            s += '&numcoeff='
            s += str(numcoeff)
            s += '">'
            s += '\(\chi_{' + str(chars[j][1][k]) + '}\)</a> '
        s += '</td>\n</tr>\n'
    s += '</table>\n'
    info['contents'] = s
    return info
