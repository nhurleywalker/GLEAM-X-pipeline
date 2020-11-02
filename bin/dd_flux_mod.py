#!/usr/bin/env python

# Read in the PSF map, which contains (a*b)/(a_theory*b_theory)
# Multiply the mosaic by (a*b)/(a_theory*b_theory)

# Then when we rerun source-finding, using the PSF map,
# projection should be taken into account by the PSF map,
# and reduced peak flux densities from ionospheric blurring
# should be boosted back to where they should have been.

import numpy as np

from astropy.io import fits
from astropy import wcs
from optparse import OptionParser

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--mosaic',type="string", dest="mosaic",
                    help="The filename of the mosaic you want to read in.")
parser.add_option('--psf',type="string", dest="psf",
                    help="The filename of the psf image you want to read in. \
                    The fourth slice should contain the blur factor to apply.")
parser.add_option('--output',type="string", dest="output",
                    help="The filename of the output rescaled image.")
(options, args) = parser.parse_args()

input_mosaic = options.mosaic
input_root=input_mosaic.replace(".fits","")

# Read in the mosaic to be modified
mosaic = fits.open(input_mosaic)
w = wcs.WCS(mosaic[0].header)

#create an array but don't set the values (they are random)
indexes = np.empty( (mosaic[0].data.shape[0]*mosaic[0].data.shape[1],2),dtype=int)

#since I know exactly what the index array needs to look like I can construct
# it faster than list comprehension would allow
#we do this only once and then recycle it
idx = np.array([ (j,0) for j in xrange(mosaic[0].data.shape[1])])
j=mosaic[0].data.shape[1]
for i in xrange(mosaic[0].data.shape[0]):
    idx[:,1]=i
    indexes[i*j:(i+1)*j] = idx

#put ALL the pixels into our vectorized functions and minimise our overheads
ra,dec = w.wcs_pix2world(indexes,1).transpose()

# Read in the PSF
psf = fits.open(options.psf)

# Specifically, the blur factor
blur = psf[0].data[3]

w_psf = wcs.WCS(psf[0].header,naxis=2)

# Apply the blur correction
k, l = w_psf.wcs_world2pix(ra,dec,1)
k_int = [int(np.floor(x)) for x in k]
k_int = [x if (x>=0) and (x<=360) else 0 for x in k_int]
l_int = [int(np.floor(x)) for x in l]
l_int = [x if (x>=0) and (x<=180) else 0 for x in l_int]
blur_tmp = blur[l_int,k_int]
blur_corr = blur_tmp.reshape(mosaic[0].data.shape[0],mosaic[0].data.shape[1])
mosaic[0].data *= blur_corr

# Testing this suggests it is 100x+ faster. 
# k_int = np.floor(k).astype(np.int)
# k_mask = ( (k_int >= 0) & ( k_int <= 360 ) )
# k_int[~k_mask] = 0

# l_int = np.floor(l).astype(np.int)
# l_mask = ( (l_int >= 0 ) & ( l_int <= 180 ) )
# l_int[~l_mask] = 0

# blur_tmp = blur[l_int,k_int]
# blur_corrn = blur_tmp.reshape(mosaic_shape)

mosaic.writeto(options.output,clobber=True)
