#################################################################################
#
# (c) Copyright 2010 William Stein
#
#  This file is part of PSAGE
#
#  PSAGE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
# 
#  PSAGE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################


import os, sys
## if sys.maxint != 2**63 - 1:
##     print "*"*70
##     print "The PSAGE library only works on 64-bit computers.  Terminating build."
##     print "*"*70
##     sys.exit(1)

## Emulate being called from the command line
sys.argv=['setup.py']
sys.argv.append('build_ext')
sys.argv.append('--inplace')
#print "PARAM:", sys.argv 
import build_system
from sage.misc.package import is_package_installed

SAGE_ROOT = os.environ['SAGE_ROOT']

INCLUDES = ['%s/%s/'%(SAGE_ROOT,x) for x in
            ['local/include/csage', 'local/include', 'local/include/python2.6/',
             'devel/sage/sage/ext', 'devel/sage', 'devel/sage/sage/gsl']]

if '-ba' in sys.argv:
    print "Rebuilding all Cython extensions."
    FORCE = True
else:
    FORCE = False

def Extension(*args, **kwds):
    if not kwds.has_key('include_dirs'):
        kwds['include_dirs'] = INCLUDES
    else:
        kwds['include_dirs'] += INCLUDES
    if not kwds.has_key('force'):
        kwds['force'] = FORCE

    # Disable warnings when running GCC step -- cython has already parsed the code and
    # generated any warnings; the GCC ones are noise.
    if not kwds.has_key('extra_compile_args'):
        kwds['extra_compile_args'] = ['-w']
    else:
        kwds['extra_compile_args'].append('-w')
        
    E = build_system.Extension(*args, **kwds)
    E.libraries = ['csage'] + E.libraries
    return E


numpy_include_dirs = [os.path.join(SAGE_ROOT,
                                   'local/lib/python/site-packages/numpy/core/include')]

ext_modules = [
    Extension('maass_waveforms.backend.lpkbessel',
              ['maass_waveforms/backend/lpkbessel.pyx'])
    ]



# I just had a long chat with Robert Bradshaw (a Cython dev), and he
# told me the following functionality -- turning an Extension with
# Cython code into one without -- along with proper dependency
# checking, is now included in the latest development version of
# Cython (Nov 2, 2010).  It's supposed to be a rewrite he did of the
# code in the Sage library.  Hence once that gets released, we should
# switch to using it here. 


build_system.cythonize(ext_modules)

build_system.setup(
    name = 'lmfdb',
    version = "2011.09.26",
    description = "LMFDB: Software for Arithmetic Geometry",
    author = 'Fredrik Stroemberg',
    author_email = 'fredrik314@gmail.com',
    url = 'http://www.modforms.org',
    license = 'GPL v2+',
    packages = ['maass_waveforms.backend'
		],
    platforms = ['any'],
    download_url = 'NA',
    ext_modules = ext_modules
)

