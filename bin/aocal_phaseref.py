#!/usr/bin/env python
import os, logging
from optparse import OptionParser #NB zeus does not have argparse!
#from aocal import fromfile
from mwapy.aocal import fromfile
import numpy as np
parser = OptionParser(usage = "usage: %prog inbinfile outbinfile refant" +
"""
Divide through by phase of a single reference antenna
""")
parser.add_option("-v", "--verbose", action="count", default=0, dest="verbose", help="-v info, -vv debug")
parser.add_option("--incremental", action="store_true", dest="incremental", help="incremental solution")
parser.add_option("--preserve_xterms", action="store_true", dest="preserve_xterms", help="preserve cross-terms (default is to set them all to 0+0j)")
opts, args = parser.parse_args()

if len(args) != 3:
    parser.error("incorrect number of arguments")
infilename = args[0]
outfilename = args[1]
refant = int(args[2])

if opts.verbose == 1:
    logging.basicConfig(level=logging.INFO)
elif opts.verbose > 1:
    logging.basicConfig(level=logging.DEBUG)

ao = fromfile(infilename)

ref_phasor = (ao[0, refant, ...]/np.abs(ao[0, refant, ...]))[np.newaxis, np.newaxis, ...]
if opts.incremental:
    logging.warn("incremental solution untested!")
    ao = ao / (ao*ref_phasor)
else:
    ao = ao / ref_phasor

if not opts.preserve_xterms:
    ao[0, :, :, 1] = np.zeros(ao.shape[1:3], dtype=np.complex128)
    ao[0, :, :, 2] = np.zeros(ao.shape[1:3], dtype=np.complex128)

ao.tofile(outfilename)
