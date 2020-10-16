#! /usr/bin/env python

import os
import numpy as np
from astropy.io import fits
from argparse import ArgumentParser

def make_psf(bmaj_image, bmin_image, bpa_image, outname):
    """Make the PSF map from the individual BMAJ, BMIN, BPA maps."""

    bmaj = fits.open(bmaj_image)
    bmin = fits.getdata(bmin_image)
    bpa = fits.getdata(bpa_image)

    shape = bmaj[0].data.shape
    psf_map = np.full((3, shape[0], shape[1]), np.nan)
    psf_map[0, ...] = bmaj[0].data
    psf_map[1, ...] = bmin
    psf_map[2, ...] = bpa

    fits.writeto(outname, psf_map.astype(np.float32), bmaj[0].header, overwrite=True)



def main():
    """
    """

    ps = ArgumentParser(description="Combine BMAJ, BMIN, and BPA maps for PSF map.")
    ps.add_argument("bmaj_image", type=str, help="BMAJ map.")
    ps.add_argument("bmin_image", type=str, help="BMIN map.")
    ps.add_argument("bpa_image", type=str, help="BPA map.")
    ps.add_argument("-o", "--outname", type=str, default="psfmap.fits",
                    help="Outname name for PSF map. [Default psfmap.fits]")
    ps.add_argument("-r", "--remove", action="store_true",
                    help="Switch on to remove BMAJ, BMIN, and BPA maps.")

    args = ps.parse_args()

    make_psf(args.bmaj_image, args.bmin_image, args.bpa_image, args.outname)

    if args.remove:
        for image in [args.bmaj_image, args.bmin_image, args.bpa_image]:
            if os.path.exists(image):
                os.remove(image)



if __name__ == "__main__":
    main()
