#!/usr/bin/env python

from astropy.io import fits
import numpy as np
import sys

infile = sys.argv[1]

hdu = fits.open(infile)

ind = np.where(np.abs(hdu[0].data) < 1.e-9)

hdu[0].data[ind] = 0.0

hdu.writeto(infile.replace(".fits", "_zeroed.fits"))
