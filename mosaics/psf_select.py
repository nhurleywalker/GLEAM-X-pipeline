#!/usr/bin/env python

import numpy as np
import os, sys, re

import astropy
from astropy.io import fits
from astropy.io.votable import writeto as writetoVO
from astropy.table import Table, Column
from astropy.io.votable import parse_single_table

from optparse import OptionParser

usage="Usage: %prog [options]\n"
parser = OptionParser(usage=usage)
parser.add_option('--input',dest="input",default=None,
                  help="Input FITS table to downselect.")
parser.add_option('--minsnr',dest="minsnr",default=10.0,type="float",
                  help="Minimum S/N ratio for sources used to fit PSF (default = 10 sigma)")
parser.add_option('--nofilter',action="store_false",dest="usefilter",default=True,
                  help="Don't use NVSS (and SUMSS South of Dec -40) to select unresolved sources? (default = use NVSS and SUMSS)")
parser.add_option('--noisolate',action="store_false",dest="isolate",default=True,
                  help="Don't exclude sources near other sources? (will exclude by default)")
parser.add_option('--output',dest="output",default=None,
                  help="Output psf FITS file -- default is input_psfcat.fits")
(options, args) = parser.parse_args()

# Parse the input options

if not os.path.exists(options.input):
    print "Error! Must specify an input file."
    sys.exit(1)
else:
    inputfile=options.input

if options.output:
    outputfile=options.output
else:
    outputfile=inputfile.replace(".fits","_psfcat.fits")

# Read the VO table and start processing
if options.isolate is True:
    sparse=re.sub(".fits","_isolated.fits",inputfile)
    os.system('stilts tmatch1 matcher=sky values="ra dec" params=600 \
               action=keep0 in='+inputfile+' out='+sparse)
else:
    sparse=inputfile

if options.usefilter is True:
    nscat="/group/mwasci/$USER/GLEAM-X-pipeline/models/NVSS_SUMSS_psfcal.fits"
# Snapshot: Get rid of crazy-bright sources, really super-extended sources, and sources with high residuals after fit
    os.system('stilts tpipe in='+sparse+' cmd=\'select ((local_rms<1.0)&&((int_flux/peak_flux)<3)&&((residual_std/peak_flux)<0.1))\' out=temp_crop.fits')
# Match GLEAM with NVSS/SUMSS
    os.system('stilts tmatch2 matcher=sky params=30 in1='+nscat+' in2=temp_crop.fits out=temp_ns_match.fits values1="RAJ2000 DEJ2000" values2="ra dec" fixcols="dups" suffix1="_ns" suffix2=""')
# Keep only basic aegean headings
    os.system('stilts tpipe in=temp_ns_match.fits cmd=\'keepcols "ra dec peak_flux err_peak_flux int_flux err_int_flux local_rms a err_a b err_b pa err_pa residual_std flags"\' out='+outputfile)

    os.remove('temp_crop.fits')
    os.remove('temp_ns_match.fits')

    hdu = fits.open(outputfile)
    data = hdu[1].data
else:
    hdu = fits.open(sparse)
    data = hdu[1].data

x=data['ra']
if max(x)>360.:
    print "RA goes higher than 360 degrees! Panic!"
    sys.exit(1)
y=data['dec']
    
# Downselect to unresolved sources

mask=[]
# Filter out any sources where Aegean's flags weren't zero
indices=np.where((data['flags']==0) & ((data['peak_flux']/data['local_rms'])>=options.minsnr))
mask.extend(indices[0])
mask=np.array(mask)

tab = Table(data[mask])
tab.description = "Sources selected for PSF calculation."
tab.write(outputfile, overwrite=True)

