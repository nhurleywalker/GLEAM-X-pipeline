#! /usr/bin/env python

from __future__ import print_function, division

from argparse import ArgumentParser

import numpy as np
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS

import logging
logging.basicConfig(format="%(levelname)s (%(module)s): %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def strip_wcsaxes(hdr):
    """Strip extra axes in a header object."""


    remove_keys = [key+i for key in 
                   ["CRVAL", "CDELT", "CRPIX", "CTYPE", "CUNIT", "NAXIS"]
                   for i in ["3", "4"]]

    for key in remove_keys:
        if key in hdr.keys():
            del hdr[key]

    return hdr


def radec_to_lm(ra, dec, ra0, dec0):
    """Convert RA,DEC to l,m."""

    l = np.cos(dec)*np.sin(ra-ra0)
    m = np.sin(dec)*np.cos(dec0) - np.cos(dec)*np.sin(dec0)*np.cos(ra-ra0)

    return l, m


def dOmega(ra, dec, ra0, dec0):
    """Calculate dOmega from RA,DEC.

    dOmega = dldm / (1-l^2-m^2)^1/2
    """

    ra = np.radians(ra)
    dec = np.radians(dec)
    ra0 = np.radians(ra0)
    dec0 = np.radians(dec0)

    l, m = radec_to_lm(ra, dec, ra0, dec0)
    n = np.sqrt(1 - l**2 - m**2)

    return 1. / n


def check_projection(hdr, projections=["SIN", "ZEA"]):
    """Check that projection == 'SIN'."""

    projection = hdr["CTYPE1"].split("-")[-1]

    if  projection not in projections:
        raise ValueError("projection is not {}: projection={}".format(
            projections, projection))
    else:
        return projection


def make_sinfactor_map(fitsimage, stride=16000000, ra0=None, dec0=None,
                       outname=None):
    """Make a map of dOmega for a given image and reference coordinates."""

    hdu = fits.open(fitsimage)
    try:
        projection = check_projection(hdu[0].header)
    except ValueError:
        logger.warning("dOmega factors only valid for SIN projection.")
        raise
    else:

        shape = np.squeeze(hdu[0].data).shape
        arr = np.full(shape, np.nan)

        w = WCS(hdu[0].header).celestial

        if ra0 is None:
            ra0 = hdu[0].header["CRVAL1"]
        if dec0 is None:
            dec0 = hdu[0].header["CRVAL2"]

        indices=  np.indices(shape)
        y = indices[0].flatten()
        x = indices[1].flatten()
        n = len(x) 

        for i in range(0, n, stride):

            r, d = w.all_pix2world(x[i:i+stride], y[i:i+stride], 0)
            factors = dOmega(r, d, ra0, dec0)

            arr[y[i:i+stride], x[i:i+stride]] = factors

    if outname is None:
        outname = fitsimage.replace(".fits", "_dOmega.fits")

    fits.writeto(outname, arr.astype(np.float32), strip_wcsaxes(hdu[0].header), overwrite=True)



def make_ratio_map(fitsimage, ra0, dec0, stride=16000000, outname=None):
    """Make a map of ratio of dOmega."""

    hdu = fits.open(fitsimage)
    try:
        projection = check_projection(hdu[0].header)
    except ValueError:
        logger.warning("dOmega ratios only valid for SIN and ZEA projections.")
        raise
    else:

        shape = np.squeeze(hdu[0].data).shape
        arr = np.full(shape, np.nan)

        w = WCS(hdu[0].header).celestial

        indices=  np.indices(shape)
        y = indices[0].flatten()
        x = indices[1].flatten()
        n = len(x) 

        for i in range(0, n, stride):

            r, d = w.all_pix2world(x[i:i+stride], y[i:i+stride], 0)
            factors = dOmega(r, d, ra0, dec0)

            arr[y[i:i+stride], x[i:i+stride]] = 1. / factors

    if outname is None:
        # return hdu instead of writing file - avoid unnecessary file creation
        hdu[0].data = arr
        return hdu
    else:
        fits.writeto(outname, arr, strip_wcsaxes(hdu[0].header), overwrite=True)



def make_effective_psf(dOmega_map, outname, bmaj, bmin=None, bpa=0.):
    """Create each of the PSF axes."""

    if bmin is None:
        bmin = bmaj

    if isinstance(dOmega_map, str):
        hdu = fits.open(dOmega_map)
    else:
        hdu = dOmega_map

    shape = hdu[0].data.shape


    psf = {}
    #  Swarp cannot cope with cubes, so we have to output each aspect of the PSF individually
    psf["bmaj"] = bmaj / hdu[0].data
    psf["bmin"] = bmin * np.ones(hdu[0].data.shape)
    psf["bpa"] = bpa * np.ones(hdu[0].data.shape)

    for aspect in ["bmaj", "bmin", "bpa"]:
        outname_aspect = outname+"_"+aspect+".fits"
        fits.writeto(outname_aspect, psf[aspect].astype(np.float32), hdu[0].header, overwrite=True)



def main():
    """
    """

    ps = ArgumentParser(description="Calculate ratio of effective solid angle "
                                    "change across reprojected radio maps for "
                                    "determining how the point spread function "
                                    "varies over the new map.",
                        )

    ps.add_argument("new_image", type=str,
                    help="New (resampled/reprojected) FITS image in ZEA projection.")
    ps.add_argument("original_image", type=str,
                    help="Original FITS image in SIN projection. Used to get "
                         "original CRVAL1/CRVAL2 values.")


    args = ps.parse_args()

    hdr = fits.getheader(args.original_image)
    bmaj = hdr["BMAJ"]
    try:
        bmin = hdr["BMIN"]
    except KeyError:
        bmin = bmaj
    try:
        bpa = hdr["BPA"]
    except KeyError:
        bpa = 0.

    original_projection = "SIN"
    with fits.open(args.original_image) as f:
        ra0 = f[0].header["CRVAL1"]
        dec0 = f[0].header["CRVAL2"]

    outname = args.new_image.replace(".fits", "")
    hdu = make_ratio_map(args.new_image, ra0, dec0, outname=None)
    make_effective_psf(hdu, outname, bmaj, bmin, bpa)


if __name__ == "__main__":
    main()


    
