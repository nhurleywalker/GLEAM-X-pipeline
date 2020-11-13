#!/usr/bin/env python

from __future__ import print_function

import sys
import os, logging
import numpy as np
from math import pi
from astropy.io import fits
from astropy.wcs import WCS
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
import astropy.units as u
from mwa_pb_lookup.lookup_beam import beam_lookup_1d

import argparse

# configure the logging
logging.basicConfig(format="# %(levelname)s:%(name)s: %(message)s")
logger = logging.getLogger(__name__)
# logger.setLevel(logging.WARNING)

# location from CONV2UVFITS/convutils.h
MWA = EarthLocation.from_geodetic(
    lat=-26.703319 * u.deg, lon=116.67081 * u.deg, height=377 * u.m
)

######################################################################
def beam_value(ra, dec, t, delays, freq, gridnum, pol="i", interp=True):

    logger.info("Computing for %s" % t)

    pol = pol.upper()
    assert pol in ("I", "XX", "YY"), "pol %s is not supported" % pol

    rX, rY = beam_lookup_1d(ra, dec, gridnum, t, freq)

    if pol == "I":
        return np.squeeze(rX), np.squeeze(rY)
    elif pol == "XX":
        return np.squeeze(rX)
    elif pol == "YY":
        return np.squeeze(rY)
    else:
        # Shouldnt get here, but anyway..
        raise ValueError("pol value is {0}, and not correctly set.".format(pol))


def parse_metafits(metafits):
    # Delays needed for beam model calculation
    try:
        f = fits.open(metafits)
    except Exception as e:
        logger.error("Unable to open FITS file %s: %s" % (metafits, e))
        sys.exit(1)
    if not "DELAYS" in f[0].header.keys():
        logger.error("Cannot find DELAYS in %s" % options.metafits)
        sys.exit(1)
    delstr = f[0].header["DELAYS"].split(",")
    delays = [int(e) for e in delstr]

    # get the date so we can convert to Az,El
    start_time = f[0].header["DATE-OBS"]
    duration = f[0].header["EXPOSURE"] * u.s
    t = Time(start_time, format="isot", scale="utc") + 0.5 * duration

    # Just use the central frequency
    # Nice update would be to use the whole bandwidth and calculate spectral term
    try:
        freq = f[0].header["FREQCENT"] * 1000000.0
    except:
        logger.error("Unable to read frequency FREQCENT from %s" % metafits)

    gridnum = f[0].header["GRIDNUM"]

    return t, delays, freq, gridnum


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group1 = parser.add_argument_group("required arguments:")
    group1.add_argument("--ra", type=float, help="The RA in decimal degrees")
    group1.add_argument("--dec", type=float, help="The declination in decimal degrees")
    group1.add_argument(
        "--metafits", type=str, help="The metafits file for your observation"
    )
    options = parser.parse_args()

    t, delays, freq, gridnum = parse_metafits(options.metafits)

    val = beam_value(options.ra, options.dec, t, delays, freq, gridnum)
    print(val[0], val[1])

# Leaving this code here for later; might be useful when returning different pols
#    header = hdu.header
#    data = hdu.data

#    wcs=WCS(header)

# construct the basic arrays
#    x, y = np.meshgrid(np.arange(data.shape[-1]), np.arange(data.shape[-2]))
#    ra, dec = wcs.celestial.wcs_pix2world(x, y, 0)

# pick out just those pixels that are above the horizon
# up = altaz.alt.rad > 0

#    if pol in ('I', 'XX', 'YY'):
#        d = np.nan*np.ones(altaz.alt.shape)
#        if pol == 'I':
#            d[up] = (rX**2 + rY**2) / (rX+rY)
#        elif pol == 'XX':
#            d[up] = rX
#        elif pol == 'YY':
#            d[up] = rY
#        hdu.data = np.float32(d.reshape(hdu.data.shape))
#        return hdu
#    # pol == 'HALF':
#    d = np.nan*np.ones(altaz.alt.shape)
#    d[up] = rX
#    hdu.data = np.float32(d.reshape(hdu.data.shape))
#    hdu2 = hdu.copy()
#    d[up] = rY
#    hdu2.data = np.float32(d.reshape(hdu.data.shape))
#    return hdu, hdu2

# # convert to alt az
# radec = SkyCoord(ra*u.deg, dec*u.deg)
# altaz = radec.transform_to(AltAz(obstime=t,location=MWA))

# # theta phi (and rX, rY) are 1D arrays.
# theta = (pi/2) - altaz.alt.rad # [up]
# phi = altaz.az.rad #[up]

# # Test if more than one RA and Dec value has been specified
# if not hasattr(theta,"__getitem__"):
#    theta = [theta]
#    phi = [phi]

# #rX,rY=mwapy.pb.primary_beam.MWA_Tile_full_EE(theta, phi,
# rX,rY=MWA_Tile_full_EE([theta], [phi],
#       freq=freq, delays=delays,
#       zenithnorm=True, power=True,
#       interp=interp)

# return np.squeeze(rX), np.squeeze(rY)
