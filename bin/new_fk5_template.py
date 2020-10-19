#!/usr/bin/env python

__author__ = "Natasha Hurley-Walker"
__date__ = "15/08/2019"

import os, sys
from argparse import ArgumentParser
import numpy as np
from astropy.io import fits
from astropy import wcs
from scipy import signal

# Conversion factors
std2fwhm = 2*np.sqrt(2*np.log(2))
krsize = 11 # How many pixels on the side of the Gaussian

def new_fk5_template(ra, dec, nx, ny, pixscale, fwhm, output, noise=0.0, background=0.0, overwrite=False):
    if not os.path.exists(output) or overwrite is True:
        w = wcs.WCS(naxis=2)
        # Divisible by 2
        nx = (nx//2)*2
        ny = (ny//2)*2
        w.wcs.crpix = [nx/2, ny/2]
        w.wcs.cdelt = np.array([-pixscale, pixscale])
        w.wcs.crval = [ra, dec]
        w.wcs.ctype = ["RA---SIN", "DEC--SIN"]
        header = w.to_header()
        stdev = (fwhm/std2fwhm)/pixscale
        
        # Set up the convolution kernel
        kernel = np.outer(signal.windows.gaussian(krsize*krsize, stdev), signal.windows.gaussian(krsize*krsize, stdev))

        # Simulate the data
        if noise > 0.0:
            data = np.random.normal(loc=0, scale=noise, size=(nx, ny))
            blurred = signal.fftconvolve(data, kernel, mode = 'same')
            new_rms = np.std(blurred)
            ratio = noise/new_rms
            blurred *= ratio
            data = blurred.astype("float32")
        else:
            data = np.zeros([nx, ny], dtype="float32")
        bkg = background * np.ones([nx, ny], dtype="float32")
        data += bkg
        new = fits.PrimaryHDU(data,header=header) #create new hdu
        newlist = fits.HDUList([new]) #create new hdulist
        newlist[0].header["BMAJ"] = fwhm
        newlist[0].header["BMIN"] = fwhm
        newlist[0].header["BPA"] = 0.0
        newlist.writeto(output, overwrite=True)
    return output

if __name__ == '__main__':
    parser = ArgumentParser(description="""
    Make a new FK5 SIN projected FITS file
    """)
    parser.add_argument("--ra", default=180.0, dest="racent", type=float, help="RA centre in decimal deg")
    parser.add_argument("--dec", default=0.0, dest="decent", type=float, help="Dec centre in decimal deg")
    parser.add_argument("--nx", default=100, dest="nx", type=int, help="Length of RA axis in pixels")
    parser.add_argument("--ny", default=100, dest="ny", type=int, help="Length of Dec axis in pixels")
    parser.add_argument("--pixscale", default=0.02, dest="pixscale", type=float, help="Pixel scale in degrees")
    parser.add_argument("--fwhm", default=0.07, dest="fwhm", type=float, help="Beam size in degrees")
    parser.add_argument("--noise", default=0.0, dest="noise", type=float, help="Noise level in Jy/pix")
    parser.add_argument("--background", default=0.0, dest="background", type=float, help="Background level in Jy/pix")
    parser.add_argument("--output", default="template.fits", dest="output", help="Output filename")
    parser.add_argument("--overwrite", default=False, action="store_true", dest="overwrite", help="Overwrite existing file (default False)")

    args = parser.parse_args()

    if len(sys.argv) <= 1:
        parser.print_help()
        sys.exit()
    else:
        new_fk5_template(args.racent, args.decent, args.nx, args.ny, args.pixscale, args.fwhm, args.output, args.noise, args.background, args.overwrite)
