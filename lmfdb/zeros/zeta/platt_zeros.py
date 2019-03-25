# -*- coding: utf-8 -*-
#
# AUTHOR: Jonathan Bober <jwbober@gmail.com>
#
# Simple Python module for extracting lists of zeros from Dave Platt's
# tables of zeros of the zeta function.
#

import sqlite3
import os
import struct
import sys
from math import log

import mpmath
mpmath.mp.prec = 300

zeta_folder =  os.path.expanduser('/home/lmfdb/data/zeros/zeta/')
data_location = os.path.join(zeta_folder, 'data/')
db_location = os.path.join(zeta_folder,'index.db')

def list_zeros(filename,
               offset,
               block_number,
               number_of_zeros=2000,
               t_start=0,
               N_start=0):
    r"""
    Lower level function to list zeros starting at a specific place in a
    specific file. This function is meant to be called by a higher level
    function which does an initial query into the index in order to
    figure out what file and offset to start with.

    INPUT:
        - filename: the name of the file that we are going to grab the
                    data from
        - offset: the position to seek to in the file to get the start
                  of the block that we are going to grab initial data
                  from
        - block_number: the index of this block in this file. (We need
                        to know this because at least one of the files
                        has some sort of garbage at the end, and so we
                        might run out of blocks before we run out of
                        file
        - number of zeros: the number of zeros to return
        - t_start/N_start: where to start the listing from. Either the
                           height t_start or the N-th zero. If both are
                           specified, then whichever comes last will
                           be used.

    """

    db = sqlite3.connect(db_location)
    c = db.cursor()

    eps = mpmath.mpf(2) ** (-101)     # The (absolute!) precision to which
                                    # the zeros are stored.

    infile = open(os.path.join(data_location, filename), 'rb')

    # infile is the file that actually contains the data that we want.
    # It is in a compressed binary format that we aren't going to
    # describe completely here. See [TODO].

    number_of_blocks = struct.unpack('Q', infile.read(8))[0]  # The first 8 bytes of the
                                                             # the file are a 64-bit
                                                             # unsigned integer.

    # We move to the beginning of the block that we are interested in...
    infile.seek(offset, 0)
    t0, t1, Nt0, Nt1 = struct.unpack('ddQQ', infile.read(8 * 4))

    # and then start reading. Each block has a 32 byte header with a pair of
    # doubles and a pair of integers. t0 is the offset for the imaginary parts
    # of the zeros in this block (and t1 the offset for the next block),
    # Nt0 = N(t0), the number of zeros with imaginary part < t0, and similarly
    # for t1. So the number of zeros in this block is Nt1 - Nt0.

    mpmath.mp.prec = log(t1, 2) + 10 + 101  # We make sure that the working precision
                                            # is large enough. Note that we are adding
                                            # a little too much here, so when these
                                            # numbers are printed, they will have too
                                            # many digits.

    t0 = mpmath.mpf(t0)

    Z = 0   # Z is going to be a python integer that holds the
            # difference gamma - t0, where gamma is a zero of
            # the zeta function. Z will be a 104+ bit positive integer,
            # and the difference is interpreted as Z * eps == Z * 2^(-101).

    count = 0   # the number of zeros we have found so far
    N = Nt0     # the index of the next zero

    # FIXME THIS VARIABLE IS NEVER USED
    #L = []      # the zeros we have found so far

    # now we start finding zeros
    while count < number_of_zeros:
        #
        # If the index of the next zero falls off the end of the
        # block we are going to need to go to the next block, and
        # possibly the next file.
        #
        if N == Nt1:
            block_number += 1
            #
            # Check if we are at the end of the file...
            #
            if block_number == number_of_blocks:
                infile.close()

                # If we are at the end of the file, we have to make a new
                # query into the index to get the name of the next file.
                #
                # (Possible optimization: parse the file name properly, so
                # we can just look at a list to get the next one.)
                #
                c = db.cursor()
                query = 'select * from zero_index where N = ? limit 1'
                c.execute(query, (N,))
                result = c.fetchone()
                if result is None:
                    return
                t0, N0, filename, offset, block_number = result

                infile = open(os.path.join(data_location, filename), 'rb')
                if not infile:
                    return
                number_of_blocks = struct.unpack('Q', infile.read(8))[0]
                infile.seek(offset, 0)

            #
            # At this point we just repeat all of the above opening
            # code since we are starting a new block.
            #
            header = infile.read(8 * 4)
            t0, t1, Nt0, Nt1 = struct.unpack('ddQQ', header)
            mpmath.mp.prec = log(t1, 2) + 10 + 101
            t0 = mpmath.mpf(t0)
            Z = 0

        # Now we are actually reading data from the block.
        #
        # Each block entry is a 13 byte integer...
        z1, z2, z3 = struct.unpack('QIB', infile.read(13))
        Z = Z + (z3 << 96) + (z2 << 64) + z1

        # now we have the zero:
        zero = t0 + mpmath.mpf(Z) * eps
        N = N + 1

        # But we only append it to the list if
        # it belongs there. (We may want to start
        # the listing in the middle of a block.
        if N >= N_start and zero >= t_start:
            count = count + 1
            yield (N, zero)

    infile.close()


def zeros_starting_at_t(t, number_of_zeros=1000):
    if t < 14:
        t = 14
    query = 'select * from zero_index where t <= ? order by t desc limit 1'
    c = sqlite3.connect(db_location).cursor()
    c.execute(query, (float(t),))
    t0, N0, filename, offset, block_number = c.fetchone()
    return list_zeros(filename, offset, block_number, number_of_zeros=number_of_zeros, t_start=t)


def zeros_starting_at_N(N, number_of_zeros=1000):
    N = int(N)
    if N < 0:
        N = 0

    query = 'select * from zero_index where N <= ? order by N desc limit 1'
    c = sqlite3.connect(db_location).cursor()
    c.execute(query, (N,))
    t0, N0, filename, offset, block_number = c.fetchone()
    return list_zeros(filename, offset, block_number, number_of_zeros=number_of_zeros, N_start=N)

if __name__ == "__main__":
    t = float(sys.argv[1])
    count = int(sys.argv[2])
    _print = int(sys.argv[3])
    c = sqlite3.connect(db_location).cursor()
    zeros = zeros_starting_at_t(t, count, _print=_print)
