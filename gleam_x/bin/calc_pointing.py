#!/usr/bin/env python
from __future__ import print_function
__author__ = "Natasha Hurley-Walker"
__date__ = "10/09/2019"

import sys
from argparse import ArgumentParser 
from astropy.io import fits
from astropy.coordinates import EarthLocation, SkyCoord
from astropy import units as u

def calc_optimal_ra_dec(metafits):
    hdu = fits.open(metafits)
    alt = hdu[0].header["ALTITUDE"]
    if alt < 55. :
        az = hdu[0].header["AZIMUTH"]
        date = hdu[0].header["DATE-OBS"]
        mwa = EarthLocation.of_site("Murchison Widefield Array")
        
        # Empirical testing shows that if the altitude is < 55 degrees, the pointing is actually 8 degrees above where you think it is
        alt += 8.0
        newaltaz = SkyCoord(az, alt, frame="altaz", unit=(u.deg, u.deg), obstime=date, location=mwa)
        newradec = newaltaz.transform_to("fk5")
    else:
        newradec = SkyCoord(hdu[0].header["RA"], hdu[0].header["Dec"], unit = (u.deg, u.deg))
    return newradec

if __name__ == '__main__':
    parser = ArgumentParser(description="""
    Highly off-zenith pointings have maximum primary beam sensitivity quite far from the pointing centre.
    This script returns the ideal phase centre for the GLEAM-X pointings.
    """)
    parser.add_argument("metafits", default=None, help="Metafits filename")
    args = parser.parse_args()

    radec = calc_optimal_ra_dec(args.metafits)
    print(radec.to_string("hmsdms"))



