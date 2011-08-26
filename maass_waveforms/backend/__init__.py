from web_maassforms import WebMaassFormSpace,WebMaassForm

## import os, sys
## import build_system
## SAGE_ROOT = os.environ['SAGE_ROOT']

## INCLUDES = ['%s/%s/'%(SAGE_ROOT,x) for x in
##             ['local/include/csage', 'local/include', 'local/include/python2.6/',
##              'devel/sage/sage/ext', 'devel/sage', 'devel/sage/sage/gsl']]
## if '-ba' in sys.argv:
##     print "Rebuilding all Cython extensions."
##     FORCE = True
## else:
##     FORCE = False

## E=build_system.Extension(
##     "maass_waveforms.backend.lpkbessel",
##     sources=["maass_waveforms/backend/lpkbessel.pyx"],
##     include_dirs = INCLUDES,
##     extra_compile_args='-w',
##     force=FORCE)


## E.libraries = ['csage'] + E.libraries
## ext_modules=[E]
## build_system.cythonize(ext_modules)
## build_system.setup(
##     name = 'lpkbessel',
##     version = "2011.09.26",
##     description = "Maass waveforms for the web",
##     author = 'Fredrik Stroemberg',
##     author_email = 'fredrik314n@gmail.com',
##     url = 'http://www.lfunctions.org',
##     license = 'GPL v2+',
##     packages = ['maass_waveforms.backend.lpkbessel'],
##     platforms = ['any'],
##     download_url = 'NA',
##     ext_modules = ext_modules
## )

## print "DOne compiling!"
