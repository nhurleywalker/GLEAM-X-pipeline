#!/usr/bin/env python

# Multiply two fits files, or a fits file by a value
from __future__ import print_function
import sys
import os

import astropy.io.fits as fits

file1=sys.argv[1]
file2=sys.argv[2]
output=sys.argv[3]

print("Multiplying "+file1+" by "+file2)

hdu1=fits.open(file1)

if os.path.exists(file2):
    hdu2=fits.open(file2)
    hdu1[0].data*=hdu2[0].data
else:
    hdu1[0].data*=float(file2)

hdu1.writeto(output,overwrite=True)
