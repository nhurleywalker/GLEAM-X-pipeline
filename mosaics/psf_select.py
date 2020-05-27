#!/usr/bin/env python

import numpy as np
import os, sys, re

from astropy.io.votable import writeto as writetoVO
from astropy.table import Table, Column
from astropy.io.votable import parse_single_table

from optparse import OptionParser

usage="Usage: %prog [options]\n"
parser = OptionParser(usage=usage)
parser.add_option('--input',dest="input",default=None,
                  help="Input VO table to downselect.")
parser.add_option('--minsnr',dest="minsnr",default=10.0,type="float",
                  help="Minimum S/N ratio for sources used to fit PSF (default = 10 sigma)")
parser.add_option('--nomrc',action="store_false",dest="usemrc",default=True,
                  help="Don't use MRC (and VLSSr North of Dec 0) to select unresolved sources? (default = use ancillary catalogues.)")
parser.add_option('--noisolate',action="store_false",dest="isolate",default=True,
                  help="Don't exclude sources near other sources? (will exclude by default)")
parser.add_option('--output',dest="output",default=None,
                  help="Output psf vot file -- default is input_psf.vot")
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
    outputfile=inputfile.replace(".vot","_psf.vot")

# Read the VO table and start processing
if options.isolate:
    sparse=re.sub(".vot","_isolated.vot",inputfile)
    os.system('stilts tmatch1 matcher=sky values="ra dec" params=600 \
               action=keep0 in='+inputfile+' out='+sparse)
else:
    sparse=inputfile

if options.usemrc:
    catdir=os.environ['MWA_CODE_BASE']+'/MWA_Tools/catalogues'
    MRCvot=catdir+"/MRC.vot"
    VLSSrvot=catdir+"/VLSSr.vot"
# GLEAM: Get rid of crazy-bright sources, really super-extended sources, and sources with high residuals after fit
    os.system('stilts tpipe in='+sparse+' cmd=\'select ((local_rms<1.0)&&((int_flux/peak_flux)<2)&&((residual_std/peak_flux)<0.1))\' out=temp_crop.vot')
# MRC: get point like sources (MFLAG is blank)
    Mmatchvot=re.sub(".vot","_MRC.vot",sparse)
    os.system('stilts tpipe in='+MRCvot+' cmd=\'select NULL_MFLAG\' cmd=\'addcol PA_MRC "0.0"\' out=mrc_temp.vot')
# Use only isolated sources
    os.system('stilts tmatch1 matcher=sky values="_RAJ2000 _DEJ2000" params=600 \
               action=keep0 in=mrc_temp.vot out=mrc_crop.vot')
# Match GLEAM with MRC
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1=mrc_crop.vot in2=temp_crop.vot out=temp_mrc_match.vot values1="_RAJ2000 _DEJ2000 2*e_RA2000 2*e_DE2000 PA_MRC" values2="ra dec 2*a 2*b pa" ofmt=votable')
# Keep only basic aegean headings
    os.system('stilts tpipe in=temp_mrc_match.vot cmd=\'keepcols "ra dec peak_flux err_peak_flux int_flux err_int_flux local_rms a err_a b err_b pa err_pa residual_std flags"\' out='+Mmatchvot)

# VLSSr: get point-like sources (a and b are < 86", same resolution as MRC); only sources North of Dec +20
    Vmatchvot=re.sub(".vot","_VLSSr.vot",sparse)
    os.system('stilts tpipe in='+VLSSrvot+' cmd=\'select ((MajAx<.02389)&&(MinAx<0.02389)&&(_DEJ2000>0)) \' out=vlssr_temp.vot')
# Use only isolated sources
    os.system('stilts tmatch1 matcher=sky values="_RAJ2000 _DEJ2000" params=600 \
               action=keep0 in=vlssr_temp.vot out=vlssr_crop.vot')
# Match GLEAM with VLSSr
    os.system('stilts tmatch2 matcher=sky params=120 in1=vlssr_crop.vot in2=temp_crop.vot out=temp_vlssr_match.vot values1="_RAJ2000 _DEJ2000" values2="ra dec" ofmt=votable')
# Keep only basic aegean headings
    os.system('stilts tpipe in=temp_vlssr_match.vot cmd=\'keepcols "ra dec peak_flux err_peak_flux int_flux err_int_flux local_rms a err_a b err_b pa_2 err_pa residual_std flags"\' out='+Vmatchvot)
# Concatenate the MRC and VLSSr matched tables together
    os.system('stilts tcat in='+Mmatchvot+' in='+Vmatchvot+' out='+outputfile)

    os.remove('temp_crop.vot')
    os.remove('mrc_temp.vot')
    os.remove('mrc_crop.vot')
    os.remove('temp_mrc_match.vot')
    os.remove('vlssr_temp.vot')
    os.remove('vlssr_crop.vot')
    os.remove('temp_vlssr_match.vot')
    os.remove(Mmatchvot)
    os.remove(Vmatchvot)

    table = parse_single_table(outputfile)
    data = table.array
else:
    table = parse_single_table(sparse)
    data = table.array

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

vot = Table(data[mask])
vot.description = "Sources selected for PSF calculation."
writetoVO(vot, outputfile)

