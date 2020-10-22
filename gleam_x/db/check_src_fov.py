#!/usr/bin/env python

from __future__ import print_function

import os,sys
from astropy import wcs
from astropy.io import fits
from astropy.coordinates import SkyCoord
import astropy.units as u

from argparse import ArgumentParser

def check_coords(w, coords):
    x, y =  w.all_world2pix(coords.ra.deg,coords.dec.deg,0)
    if 0 < x < w._naxis1 and 0 < y < w._naxis2:
        return True
    else:
        return False

if __name__ == "__main__":
    usage="Usage: %prog [args] <file>\n"
    parser = ArgumentParser()
    parser.add_argument('-f','--file',dest="file", default=None,
                      help="Fits image to check <FILE>",metavar="FILE")
    parser.add_argument('-s','--source',dest="source", default=None,
                      help="Source to measure")
    args = parser.parse_args()

    sources = {'Crab': '05:34:31.94 +22:00:52.2', 'PicA': '05:19:49.7229 -45:46:43.853', 'HydA': '09:18:05.651 -12:05:43.99', 'HerA': '16:51:11.4 +04:59:20' , 'VirA': '12:30:49.42338 +12:23:28.0439' , 'CygA': '19:59:28.35663 +40:44:02.0970' ,'CasA': '23:23:24.000 +58:48:54.00'}

    if args.file is None:
        print(args.file+" not specified.")
        sys.exit(1)

    if os.path.exists(args.file):
        hdu_in = fits.open(args.file)
    else:
        print(args.file+" does not exist.")
        sys.exit(1)

    if args.source in sources:
        pos = SkyCoord([sources[args.source]], unit=(u.hourangle, u.deg))
    else:
        print(args.source+" not found in dictionary, which only contains: ", sources.keys())
        sys.exit(1)

    w = wcs.WCS(hdu_in[0].header,naxis=2)

    if check_coords(w, pos):
        print("True")
    else:
        print("False")
