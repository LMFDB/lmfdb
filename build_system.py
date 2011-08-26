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


# A setuptools-based build system.  See the comment before the line
# "build_system.cythonize(ext_modules)" in setup.py about how this
# code can probably be replaced by code in Cython soon. 

import os, sys
from setuptools import setup
import setuptools

def time_stamp(filename):
    try:
        return os.path.getmtime(filename)
    except OSError, msg:
        print msg
        return 0

def cython(f_pyx, language, include_dirs, force):
    assert f_pyx.endswith('.pyx')
    # output filename
    dir, f = os.path.split(f_pyx)
    ext = 'cpp' if language == 'c++' else 'c'
    outfile = os.path.splitext(f)[0] + '.' + ext
    full_outfile = dir + '/' + outfile
    if not force:
        if os.path.exists(full_outfile) and time_stamp(f_pyx) <= time_stamp(full_outfile):
            # Already compiled
            return full_outfile, []
    includes = ''.join(["-I '%s' "%x for x in include_dirs])
    # call cython
    cmd = "cd %s && python `which cython` --embed-positions --directive cdivision=False %s -o %s %s"%(
        dir, includes, outfile, f)
    return full_outfile, [cmd]

class Extension(setuptools.Extension):
    def __init__(self, module, sources, include_dirs,
                 language="c", force=False, **kwds):
        self.cython_cmds = []
        for i in range(len(sources)):
            f = sources[i]
            if f.endswith('.pyx'):
                sources[i], cmds = cython(f, language, include_dirs, force)
                for c in cmds:
                    self.cython_cmds.append(c)
        setuptools.Extension.__init__(self, module, sources, language=language,
                                      include_dirs=include_dirs, **kwds)

def apply_pair(p):
    """
    Given a pair p consisting of a function and a value, apply
    the function to the value.

    This exists solely because we can't pickle an anonymous function
    in execute_list_of_commands_in_parallel below.
    """
    return p[0](p[1])

def execute_list_of_commands_in_parallel(command_list, nthreads):
    """
    INPUT:
        command_list -- a list of pairs, consisting of a
             function to call and its argument
        nthreads -- integer; number of threads to use
        
    OUTPUT:
        Executes the given list of commands, possibly in parallel,
        using nthreads threads.  Terminates setup.py with an exit code of 1
        if an error occurs in any subcommand.

    WARNING: commands are run roughly in order, but of course successive
    commands may be run at the same time.
    """
    print "Execute %s commands (using %s threads)"%(len(command_list), min(len(command_list),nthreads))
    from multiprocessing import Pool
    p = Pool(nthreads)
    print command_list
    for r in p.imap(apply_pair, command_list):
        if r:
            print "Parallel build failed with status %s."%r
            sys.exit(1)

def number_of_threads():
    """
    Try to determine the number of threads one can run at once on this
    system (e.g., the number of cores).  If successful return that
    number.  Otherwise return 0 to indicate failure.

    OUTPUT:
        int
    """
    if hasattr(os, "sysconf") and os.sysconf_names.has_key("SC_NPROCESSORS_ONLN"): # Linux and Unix
        n = os.sysconf("SC_NPROCESSORS_ONLN") 
        if isinstance(n, int) and n > 0:
            return n
    try:
        return int(os.popen2("sysctl -n hw.ncpu")[1].read().strip())
    except: 
        return 0

def execute_list_of_commands_in_serial(command_list):
    """
    INPUT:
        command_list -- a list of commands, each given as a pair
           of the form [command, argument].
        
    OUTPUT:
        the given list of commands are all executed in serial
    """    
    for f,v in command_list:
        r = f(v)
        if r != 0:
            print "Error running command, failed with status %s."%r
            sys.exit(1)

def cythonize(ext_modules):
    cmds = sum([E.cython_cmds for E in ext_modules], [])
    cmds = [(os.system, c) for c in cmds]
    n = number_of_threads()
    if n == 1:
        execute_list_of_commands_in_serial(cmds)
    else:
        execute_list_of_commands_in_parallel(cmds, n)

