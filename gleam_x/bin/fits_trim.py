#!/usr/bin/env python

"""
fits_trim.py

A tool that does two things:
1 - converts pixels that are identically zero into masked pixels
2 - trims the fits image to the smallest rectangle that still contains all the data pixels

Author: Paul Hancock
Nov-2014
"""


import numpy as np
from astropy.io import fits
import sys


def trim(fin, fout):
    """Searches for the four directions (top, bottom, left, right) for the first
    valid row or column, where valid means not made up entirely of NaNs. Essentially
    performs a crop to remove any row or column made up entirely of nan pixels. 

    Arguments:
        fin (str) -- Path to the input fits file with dimensions to crop
        fout (str) -- Path to new output fits file with cropped dimensions
    """
    hdulist = fits.open(fin)
    data = hdulist[0].data
    # turn pixels that are identically zero, into masked pixels
    data[np.where(data == 0.0)] = np.nan

    print(f"Input image shape: {data.shape}")

    imin, imax = 0, data.shape[1] - 1
    jmin, jmax = 0, data.shape[0] - 1

    # select [ij]min/max to exclude rows/columns that are all zero

    for i in range(0, imax):
        imin = i
        if not np.all(np.isnan(data[:, i])):
            break
    print(f"imin: {imin}")

    for i in range(imax, imin, -1):
        imax = i
        if not np.all(np.isnan(data[:, i])):
            break
    print(f"imax: {imax}")

    for j in range(0, jmax):
        jmin = j
        if not np.all(np.isnan(data[j, :])):
            break
    print(f"jmin: {jmin}")

    for j in range(jmax, jmin, -1):
        jmax = j
        if not np.all(np.isnan(data[j, :])):
            break

    print(f"jmax: {jmax}")

    # End index is not inclusive
    hdulist[0].data = data[jmin : (jmax + 1), imin : (imax + 1)]

    print(f"Output data shape: {hdulist[0].data.shape}")

    # recenter the image so the coordinates are correct.
    hdulist[0].header["CRPIX1"] -= imin
    hdulist[0].header["CRPIX2"] -= jmin

    # save
    hdulist.writeto(fout, overwrite=True)
    print("wrote", fout)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        fin = sys.argv[-2]
        fout = sys.argv[-1]
        print(fin, "=>", fout, "(mask and trim)")
    else:
        print("usage: python {0} infile.fits outfile.fits".format(__file__))
        sys.exit()
    trim(fin, fout)

