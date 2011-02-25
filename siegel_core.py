from sage.all_cmdline import *

def dimension( wt, group, char = None, tp = 0):
    """
    Return the dimensions of all, Klingen Eisenstein, Maass cusp,
    and interesting cusp Siegel modular forms.
    For Sp(8,Z), returns total dim of cuspforms, Ikeda, Miyawaki, other ...
    """
    R = PowerSeriesRing(ZZ, default_prec = wt + 1 , names=('x',))
    (x,) = R._first_ngens(1)

    if ('Sp(4,Z)', None, 0) == (group, char, tp):

        H_all  = 1/(1 - x**4)/(1 - x**6)/(1 - x**10)/(1 - x**12)
        H_Kl   = x**12/(1 - x**4)/(1 - x**6)
        H_MS = (x**10 + x**12)/(1 - x**4)/(1 - x**6)
        if is_even(wt):
            a,b,c,d = H_all[wt], 1 if wt>=4 else 0, H_Kl[wt], H_MS[wt]
            return (a,b,c,d,a - b - c - d)
        else:
            a = H_all[wt - 35]
            return (a,0,0,0,a)

    elif ('Sp(8,Z)', None, 0) == (group, char, tp):
        if wt > 16:
          raise ValueError, 'Not yet implemented'
        elif wt == 8: return (1,1,0,0)
        elif wt == 10: return (1,1,0,0)
        elif wt == 12: return (2,1,1,0)
        elif wt == 14: return (3,2,1,0)
        elif wt == 16: return (7,2,2,3)
        else: return (0,0,0,0)
        
        
    elif ('Gamma_0(2)', None, 0) == (group, char, tp):
        raise ValueError, 'Not yet implemented'
        
    elif ('Gamma_0(3)', None, 0) == (group, char, tp):

        H_all = ((1 + 2*x**4 + x**6)  +  x**15*(1 + 2*x**2 + x**6))/(1 - x**2)/(1 - x**4)/(1 - x**6)**2
        H_cusp = ((1 + 2*x**4 + x**6)*(x**4 + x**6 - x**10)  +  x**15*(1 + 2*x**2 + x**6))/(1 - x**2)/(1 - x**4)/(1 - x**6)**2
        a = H_all[wt]
        b = c = d = 0
        
    else:
        raise ValueError, 'Not yet implemented'

    return (a,b,c,d,a - b - c - d)



