r""" Excerpt from my MySubgroup class. Contains routines to draw fundamental domains.

r"""
import matplotlib.patches as patches
import matplotlib.path as path

from sage.all import I,Gamma0,Gamma1,Gamma,SL2Z,ZZ,RR,ceil,sqrt,CC,line,text,latex,exp,pi,infinity

def draw_fundamental_domain(N,group='Gamma0',model="H",axes=None,filename=None,**kwds):
        r""" Draw fundamental domain
        INPUT:
         - ''model'' -- (default ''H'')
             = ''H'' -- Upper halfplane
             = ''D'' -- Disk model
         - ''filename''-- filename to print to
         - ''**kwds''-- additional arguments to matplotlib 
         - ''axes''  -- set geometry of output
             =[x0,x1,y0,y1] -- restrict figure to [x0,x1]x[y0,y1]

        EXAMPLES::

            sage: G=MySubgroup(Gamma0(3))
            sage: G.draw_fundamental_domain()

        """
        G=eval(group+'('+str(N)+')')
        #print G
        name ="$"+latex(G)+"$"
        ## need a "nice" set of coset representatives to draw a connected fundamental domain. Only implemented for Gamma_0(N)
        coset_reps = nice_coset_reps(G)
        #if(group=='Gamma0'):
        #else:
        #coset_reps = list(G.coset_reps())
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        if(model=="D"):
            g=_draw_funddom_d(coset_reps,format,I)
        else:
            g=_draw_funddom(coset_reps,format)
        if(axes<>None):
            [x0,x1,y0,y1]=axes
        elif(model=="D"):
            x0=-1 ; x1=1 ; y0=-1.1 ; y1=1 
        else:
            # find the width of the fundamental domain
            w=0  #self.cusp_width(Cusp(Infinity))
            wmin=0 ; wmax=1
            max_x = RR(0.55)
            rho = CC( exp(2*pi*I/3))
            for V in coset_reps:
                ## we also compare the real parts of where rho and infinity are mapped
                r1 = (V.acton(rho)).real()
                if(V[1,0]<>0):
                    inf1 = RR(V[0,0] / V[1,0])
                else:
                    inf1 = 0
                if(V[1 ,0 ]==0  and V[0 ,0 ]==1 ):
                    if(V[0 ,1 ]>wmax):
                        wmax=V[0 ,1 ]
                    if(V[0 ,1 ]<wmin):
                        wmin=V[0 ,1 ]
                if( max(r1,inf1) > max_x):
                    max_x = max(r1,inf1)
            #print "wmin,wmax=",wmin,wmax
            #x0=-1; x1=1; y0=-0.2; y1=1.5
            x0=RR(-max_x) ; x1=RR(max_x) ; y0=RR(-0.15) ; y1=RR(1.5) 
        ## Draw the axes manually (since  can't figure out how to do it automatically)
        ax = line([[x0,0.0],[x1,0.0]],color='black')
        #ax = ax + line([[0.0,y0],[0.0,y1]],color='black')
        ## ticks
        ax = ax + line([[-0.5,-0.01],[-0.5,0.01]],color='black')
        ax = ax + line([[0.5,-0.01],[0.5,0.01]],color='black')
        g = g + ax
	if model=="H":
		t = text(name, (0, -0.1), fontsize=16, color='black')
	else:
		t = text(name, (0, -1.1), fontsize=16, color='black')		
        g = g + t
        g.set_aspect_ratio(1)
        g.set_axes_range(x0,x1,y0,y1)
        g.axes(False)
        if(filename<>None):
            fig = g.matplotlib()
            fig.set_canvas(FigureCanvasAgg(fig))
            axes = fig.get_axes()[0]
            axes.minorticks_off()
            axes.set_yticks([])
            fig.savefig(filename,**kwds)
        else:
            return g
#        g.show(figsize=[5,5])

def _draw_funddom(coset_reps,format="S"):
    r""" Draw a fundamental domain for G.
    
    INPUT:
    
    - ``format``  -- (default 'Disp') How to present the f.d.
    -   ``S`` -- Display directly on the screen
    
    EXAMPLES::        


    sage: G=MySubgroup(Gamma0(3))
    sage: G._draw_funddom()
        
    """
    pi=RR.pi()
    pi_3 = pi / RR(3.0)
    from sage.plot.plot import (Graphics,line)
    from sage.functions.trig import (cos,sin)
    g=Graphics()
    x1=RR(-0.5) ; y1=RR(sqrt(3 )/2 )
    x2=RR(0.5) ; y2=RR(sqrt(3 )/2 )
    xmax=RR(20.0) 
    l1 = line([[x1,y1],[x1,xmax]])
    l2 = line([[x2,y2],[x2,xmax]])
    l3 = line([[x2,xmax],[x1,xmax]]) # This is added to make a closed contour
    c0=_circ_arc(RR(pi/3.0) ,RR(2.0*pi)/RR(3.0) ,0 ,1 ,100 )
    tri=c0+l1+l3+l2
    g=g+tri
    for A in coset_reps:
        #print  "A=",A
        [a,b,c,d]=A
        if(a==1  and b==0  and c==0  and d==1 ):
            continue
        if(a<0 ):
            a=RR(-a); b=RR(-b); c=RR(-c); d=RR(-d) 
        else:
            a=RR(a); b=RR(b); c=RR(c); d=RR(d) 
        if(c==0 ): # then this is easier
            L0 = [[cos(pi_3*RR(i/100.0))+b,sin(pi_3*RR(i/100.0))] for i in range(100 ,201 )]
            L1 = [[x1+b,y1],[x1+b,xmax]]
            L2 = [[x2+b,y2],[x2+b,xmax]]
            L3 = [[x2+b,xmax],[x1+b,xmax]]
            c0=line(L0); l1=line(L1); l2=line(L2); l3=line(L3)
            tri=c0+l1+l3+l2
            g=g+tri
        else:
            den=(c*x1+d)**2 +c**2 *y1**2 
            x1_t=(a*c*(x1**2 +y1**2 )+(a*d+b*c)*x1+b*d)/den
            y1_t=y1/den
            den=(c*x2+d)**2 +c**2 *y2**2 
            x2_t=(a*c*(x2**2 +y2**2 )+(a*d+b*c)*x2+b*d)/den
            y2_t=y2/den
            inf_t=a/c
            #print "A=",A
            #print "arg1=",x1_t,y1_t,x2_t,y2_t
            c0=_geodesic_between_two_points(x1_t,y1_t,x2_t,y2_t)
            #print "arg1=",x1_t,y1_t,inf_t
            c1=_geodesic_between_two_points(x1_t,y1_t,inf_t,0. )
            #print "arg1=",x2_t,y2_t,inf_t
            c2=_geodesic_between_two_points(x2_t,y2_t,inf_t,0.0)
            tri=c0+c1+c2
            g=g+tri
    return g


def _draw_funddom_d(coset_reps,format="MP",z0=I):
    r""" Draw a fundamental domain for self in the circle model
    INPUT:
    - ''format''  -- (default 'Disp') How to present the f.d.
    =  'S'  -- Display directly on the screen
    - z0          -- (default I) the upper-half plane is mapped to the disk by z-->(z-z0)/(z-z0.conjugate())
    EXAMPLES::
        

    sage: G=MySubgroup(Gamma0(3))
    sage: G._draw_funddom_d()
        
    """
    # The fundamental domain consists of copies of the standard fundamental domain
    pi=RR.pi()
    from sage.plot.plot import (Graphics,line)
    g=Graphics()
    bdcirc=_circ_arc(0 ,2 *pi,0 ,1 ,1000 )
    g=g+bdcirc
    # Corners
    x1=-RR(0.5) ; y1=RR(sqrt(3 )/2)
    x2=RR(0.5) ; y2=RR(sqrt(3 )/2)
    z_inf=1 
    l1 = _geodesic_between_two_points_d(x1,y1,x1,infinity)
    l2 = _geodesic_between_two_points_d(x2,y2,x2,infinity)
    c0 = _geodesic_between_two_points_d(x1,y1,x2,y2)
    tri=c0+l1+l2
    g=g+tri
    for A in coset_reps:
        [a,b,c,d]=A
        if(a==1  and b==0  and c==0  and d==1 ):
            continue
        if(a<0 ):
            a=-a; b=-b; c=-c; d=-1 
        if(c==0 ): # then this is easier
            l1 = _geodesic_between_two_points_d(x1+b,y1,x1+b,infinity)
            l2 = _geodesic_between_two_points_d(x2+b,y2,x2+b,infinity)
            c0 = _geodesic_between_two_points_d(x1+b,y1,x2+b,y2)
            # c0=line(L0); l1=line(L1); l2=line(L2); l3=line(L3)
            tri=c0+l1+l2
            g=g+tri
        else:
            den=(c*x1+d)**2 +c**2 *y1**2 
            x1_t=(a*c*(x1**2 +y1**2 )+(a*d+b*c)*x1+b*d)/den
            y1_t=y1/den
            den=(c*x2+d)**2 +c**2 *y2**2 
            x2_t=(a*c*(x2**2 +y2**2 )+(a*d+b*c)*x2+b*d)/den
            y2_t=y2/den
            inf_t=a/c
            c0=_geodesic_between_two_points_d(x1_t,y1_t,x2_t,y2_t)
            c1=_geodesic_between_two_points_d(x1_t,y1_t,inf_t,0.0 )
            c2=_geodesic_between_two_points_d(x2_t,y2_t,inf_t,0.0 )
            tri=c0+c1+c2
            g=g+tri
    g.xmax(1 )
    g.ymax(1 )
    g.xmin(-1 )
    g.ymin(-1 )
    g.set_aspect_ratio(1 )
    return g


#### Methods not dependent explicitly on the group 
def _geodesic_between_two_points(x1,y1,x2,y2):
    r""" Geodesic path between two points hyperbolic upper half-plane

    INPUTS:
    
    - ''(x1,y1)'' -- starting point (0<y1<=infinity)
    - ''(x2,y2)'' -- ending point   (0<y2<=infinity)
    - ''z0''  -- (default I) the point in the upper corresponding
                 to the point 0 in the disc. I.e. the transform is
                 w -> (z-I)/(z+I)
    OUTPUT:

    - ''ca'' -- a polygonal approximation of a circular arc centered
    at c and radius r, starting at t0 and ending at t1

    
    EXAMPLES::


        sage: l=_geodesic_between_two_points(0.1,0.2,0.0,0.5)
    
    """
    pi=RR.pi()
    from sage.plot.plot import line
    from sage.functions.trig import arcsin
    #print "z1=",x1,y1
    #print "z2=",x2,y2
    if( abs(x1-x2)< 1E-10):
        # The line segment [x=x1, y0<= y <= y1]
        return line([[x1,y1],[x2,y2]])  #[0,0,x0,infinity]
    c=RR(y1**2 -y2**2 +x1**2 -x2**2 )/RR(2 *(x1-x2))
    r=RR(sqrt(y1**2 +(x1-c)**2 ))
    r1=RR(y1/r); r2=RR(y2/r)
    if(abs(r1-1 )< 1E-12 ):
        r1=RR(1.0)
    elif(abs(r2+1 )< 1E-12 ):
        r2=-RR(1.0)
    if(abs(r2-1 )< 1E-12 ):
        r2=RR(1.0)
    elif(abs(r2+1 )<1E-12 ):
        r2=-RR(1.0)
    if(x1>=c):
        t1 = RR(arcsin(r1))
    else:
        t1 = RR(pi)-RR(arcsin(r1))
    if(x2>=c):
        t2 = RR(arcsin(r2))
    else:
        t2 = RR(pi)-arcsin(r2)
    tmid = (t1+t2)*RR(0.5)
    a0=min(t1,t2)
    a1=max(t1,t2)
    #print "c,r=",c,r
    #print "t1,t2=",t1,t2
    return _circ_arc(t1,t2,c,r)

def _geodesic_between_two_points_d(x1,y1,x2,y2,z0=I):
    r""" Geodesic path between two points represented in the unit disc
         by the map w = (z-I)/(z+I)
    INPUTS:
    - ''(x1,y1)'' -- starting point (0<y1<=infinity)
    - ''(x2,y2)'' -- ending point   (0<y2<=infinity)
    - ''z0''  -- (default I) the point in the upper corresponding
                 to the point 0 in the disc. I.e. the transform is
                 w -> (z-I)/(z+I)
    OUTPUT:
    - ''ca'' -- a polygonal approximation of a circular arc centered
    at c and radius r, starting at t0 and ending at t1

    
    EXAMPLES::

        sage: l=_geodesic_between_two_points_d(0.1,0.2,0.0,0.5)
    
    """
    pi=RR.pi()
    from sage.plot.plot import line
    from sage.functions.trig import (cos,sin)    
    # First compute the points
    if(y1<0  or y2<0 ):
        raise ValueError,"Need points in the upper half-plane! Got y1=%s, y2=%s" %(y1,y2)
    if(y1==infinity):
        P1=CC(1 )
    else:
        P1=CC((x1+I*y1-z0)/(x1+I*y1-z0.conjugate()))
    if(y2==infinity):
        P2=CC(1 )
    else:
        P2=CC((x2+I*y2-z0)/(x2+I*y2-z0.conjugate()))
        # First find the endpoints of the completed geodesic in D
    if(x1==x2):
        a=CC((x1-z0)/(x1-z0.conjugate()))
        b=CC(1 )
    else:
        c=RR(y1**2 -y2**2 +x1**2 -x2**2 )/RR(2 *(x1-x2))
        r=RR(sqrt(y1**2 +(x1-c)**2 ))
        a=c-r
        b=c+r
        a=CC((a-z0)/(a-z0.conjugate()))
        b=CC((b-z0)/(b-z0.conjugate()))
    if( abs(a+b) < 1E-10 ): # On a diagonal
        return line([[P1.real(),P1.imag()],[P2.real(),P2.imag()]])
    th_a=a.argument()
    th_b=b.argument()
    # Compute the center of the circle in the disc model
    if( min(abs(b-1 ),abs(b+1 ))< 1E-10  and  min(abs(a-1 ),abs(a+1 ))>1E-10 ):
        c=b+I*(1 -b*cos(th_a))/sin(th_a)
    elif( min(abs(b-1 ),abs(b+1 ))> 1E-10  and  min(abs(a-1 ),abs(a+1 ))<1E-10 ):
        c=a+I*(1 -a*cos(th_b))/RR(sin(th_b))
    else:
        cx=(sin(th_b)-sin(th_a))/sin(th_b-th_a)
        c=cx+I*(1 -cx*cos(th_b))/RR(sin(th_b))
    # First find the endpoints of the completed geodesic
    r=abs(c-a)
    t1=CC(P1-c).argument()
    t2=CC(P2-c).argument()
    #print "t1,t2=",t1,t2
    return _circ_arc(t1,t2,c,r)


def _circ_arc(t0,t1,c,r,num_pts=5000 ):
    r""" Circular arc
    INPUTS:
    - ''t0'' -- starting parameter
    - ''t1'' -- ending parameter
    - ''c''  -- center point of the circle
    - ''r''  -- radius of circle
    - ''num_pts''  -- (default 100) number of points on polygon
    OUTPUT:
    - ''ca'' -- a polygonal approximation of a circular arc centered
    at c and radius r, starting at t0 and ending at t1

    
    EXAMPLES::

        sage: ca=_circ_arc(0.1,0.2,0.0,1.0,100)
    
    """
    from sage.plot.plot import line
    from sage.functions.trig import (cos,sin)
    t00=t0; t11=t1
    ## To make sure the line is correct we reduce all arguments to the same branch,
    ## e.g. [0,2pi]
    pi=RR.pi()
    while(t00<0.0):
        t00=t00+RR(2.0*pi)
    while(t11<0):
        t11=t11+RR(2.0*pi)
    while(t00>2*pi):
        t00=t00-RR(2.0*pi)
    while(t11>2*pi):
        t11=t11-RR(2.0*pi)

    xc=CC(c).real()
    yc=CC(c).imag()
    L0 = [[RR(r*cos(t00+i*(t11-t00)/num_pts))+xc,RR(r*sin(t00+i*(t11-t00)/num_pts))+yc] for i in range(0 ,num_pts)]
    ca=line(L0)
    return ca


def nice_coset_reps(G):
        r"""
        Compute a better/nicer list of right coset representatives [V_j]
        i.e. SL2Z = \cup G V_j
        Use this routine for known congruence subgroups.

        EXAMPLES::


            sage: G=MySubgroup(Gamma0(5))
            sage: G._get_coset_reps_from_G(Gamma0(5))
            [[1 0]
            [0 1], [ 0 -1]
            [ 1  0], [ 0 -1]
            [ 1  1], [ 0 -1]
            [ 1 -1], [ 0 -1]
            [ 1  2], [ 0 -1]
            [ 1 -2]]
    
        """
        cl=list()
        S,T=SL2Z.gens()
        lvl=G.generalised_level()
        # Start with identity rep.
        cl.append(SL2Z([1 ,0 ,0 ,1 ]))
        if(not S in G):
            cl.append(S)
        # If the original group is given as a Gamma0 then
        # the reps are not the one we want
        # I.e. we like to have a fundamental domain in
        # -1/2 <=x <= 1/2 for Gamma0, Gamma1, Gamma
        for j in range(1 , ZZ( ceil(RR(lvl/2.0))+2)):
            for ep in [1 ,-1 ]:
                if(len(cl)>=G.index()):
                    break
                # The ones about 0 are all of this form
                A=SL2Z([0 ,-1 ,1 ,ep*j])
                # just make sure they are inequivalent
                try:
                    for V in cl:
                        if((A<>V and A*V**-1  in G) or cl.count(A)>0 ):
                            raise StopIteration()
                    cl.append(A)
                except StopIteration:
                    pass
        # We now addd the rest of the "flips" of these reps.
        # So that we end up with a connected domain
        i=1 
        while(True):
            lold=len(cl)
            for V in cl:
                for A in [S,T,T**-1 ]:
                    B=V*A
                    try:
                        for W in cl:
                            if( (B*W**-1  in G) or cl.count(B)>0 ):
                                raise StopIteration()
                        cl.append(B)
                    except StopIteration:
                        pass
            if(len(cl)>=G.index() or lold>=len(cl)):
                # If we either did not addd anything or if we addded enough
                # we exit
                break
        # If we missed something (which is unlikely)        
        if(len(cl)<>G.index()):
            print "cl=",cl
            raise ValueError,"Problem getting coset reps! Need %s and got %s" %(G.index(),len(cl))
        return cl
