#!/usr/bin/env python

from astropy.io import fits
import numpy as np
import sys

in_xx = sys.argv[1]
in_yy = sys.argv[2]
in_rms = sys.argv[3]
out_weight = in_xx.replace("-XX-beam.fits", "_weight.fits")

hdu_xx = fits.open(in_xx)
hdu_yy = fits.open(in_yy)
hdu_rms = fits.open(in_rms)

stokes_I = (hdu_xx[0].data + hdu_yy[0].data)/2.0
imsize = hdu_rms[0].data.shape[0]
# Use a central region of the RMS map to calculate the weight via inverse variance
weight = 1./(np.nanmean(hdu_rms[0].data[imsize/2 - 200:imsize/2 + 200, imsize/2 - 200:imsize/2 + 200]))**2
hdu_xx[0].data = weight * stokes_I
hdu_xx.writeto(out_weight)

