#!/usr/bin/env python

from astropy.time import Time
from astropy.io import fits
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.table import Table
from astropy import wcs
import astropy.units as u

import numpy as np

import os
import sys
import glob

import matplotlib.pyplot as plt
import matplotlib.cm as cm

import argparse

parser = argparse.ArgumentParser()
group1 = parser.add_argument_group("Input/output files")
group1.add_argument('--filelist',dest="filelist",default=None,
                  help="List of files to use (text file, single column) \
                        Expecting a list of fits files to change, and will \
                        search for associated _comp_matched files with the \
                        source-finding results, and also the <obsid>.metafits")
group1.add_argument('--correctall',action="store_true",dest="correct_all",default=False,
                  help="Correct associated background and RMS maps? (default = False)")
group1.add_argument('--skymodel',dest="skymodel",default=None,
                  help="Sky model to cross-match to (no default)")
group2 = parser.add_argument_group("Input/output files")
group2.add_argument('--plot',action="store_true",dest="make_plots",default=False,
                  help="Make fit plots? (default = False)")
group2.add_argument('--rescale',action="store_true",dest="do_rescale",default=False,
                  help="Generate rescaled fits files? (default = False)")
group2.add_argument('--Nsrc',dest="Nsrc",default=10000,type=int,
                  help="Number of sources to use for the polynomial fit (default=10000)")
group2.add_argument('--threshold',dest="SNR_threshold",default=None,type=int,
                  help="Alternatively, set a S/N threshold for sources used for \
                        the polynomial fit (will override --Nsrc if set)")
group2.add_argument('--order',dest="poly_order",default=5,type=int,
                  help="Set the order of the polynomial fit. (default = 5)")
group2.add_argument('--write',action="store_true",dest="write_coefficients",default=False,
                    help="Write coefficients to file? (default = False)")
results = parser.parse_args()

#inv = cmap_map(lambda x: 1-x, cm.PiYG)

if os.path.exists(results.filelist):
    f = open(results.filelist, 'r+')
    infiles = [line.rstrip() for line in f.readlines()]
    f.close()
    concat_table = results.filelist.replace(".txt", "_concat.fits")
    title = results.filelist.replace(".txt","")
    dec_plot = results.filelist.replace(".txt", "_fitted_dec_poly.png")
    ra_plot = results.filelist.replace(".txt", "_fitted_ra_poly.png")
else:
    print(results.filelist)
    print("Must specify a list of files to read!")
    sys.exit(1)

mwa = EarthLocation.of_site("Murchison Widefield Array")

def sigma_clip(ratios, n=1):
    median = np.median(ratios)
    std = np.nanstd(ratios)
    ind = np.intersect1d(np.where(ratios > median-n*std), np.where(ratios < median + n*std))
    return ind

# Initialise lists
alts = np.empty(0)
azs = np.empty(0)
logratios = np.empty(0)
int_fluxes = np.empty(0)
local_rmses = np.empty(0)
S200s = np.empty(0)
alphas = np.empty(0)
ras = np.empty(0)
decs = np.empty(0)

for fitsimage in infiles:
    sf = fitsimage.replace(".fits", "_comp.fits")
    sfm = fitsimage.replace(".fits", "_comp_matched.fits")
# Cross-match with a sky model to get model flux densities
    print(sfm)
    if not os.path.exists(sfm):
        # Rely on the user running Aegean and just fail if the source-finding isn't there
        if not os.path.exists(sf):
            print("Source-finding results for {0} not found".format(fitsimage))
            sys.exit(1)
        os.system("stilts tmatch2 \
        values1=\"RAJ2000 DEJ2000\" \
        values2=\"ra dec\" \
        in1={0} in2={1} \
        matcher=sky params=45 \
        out={2}".format(results.skymodel, sf, sfm))
    gpstime = Time(int(fitsimage[0:10]), format="gps")
# We get this from the FITS image rather than the metafits because I make sub-band images
    hdr = fits.getheader(fitsimage)
    centfreq = hdr["CRVAL3"] / 1.e6 #MHz
# But the metafits is better for the RA, because of the denormal projection
    path, _ = os.path.split(fitsimage)
    meta = fits.getheader("{0}/{1}.metafits".format(path, fitsimage[0:10]))
    ra_cent = meta["RA"]
# Get the cross-matched catalogue
    hdu = fits.open(sfm)
    cat = hdu[1].data
# RA offsets and Decs
    ras = np.append(ras, cat["RAJ2000"] - ra_cent*np.ones(len(cat["RAJ2000"])))
    decs = np.append(decs, cat["DEJ2000"])
# Altitudes and azimuths
    coords = SkyCoord(cat["RAJ2000"], cat["DEJ2000"], unit=(u.deg, u.deg))
    altaz = coords.transform_to(AltAz(obstime=gpstime, location=mwa))
    alts = np.append(alts, altaz.alt.value)
# Flux densities
    int_fluxes = np.append(int_fluxes, cat["int_flux"])
    S200s = np.append(S200s, cat["S_200"])
    alphas = np.append(alphas, cat["alpha"])
    logratios = np.append(logratios, np.log10(cat["S_200"]*(centfreq/200.)**cat["alpha"]/cat["int_flux"]))
    local_rmses = np.append(local_rmses, cat["local_rms"])
    azs = np.append(azs, altaz.az.value)

# sigma-clip to get rid of crazy values
ind = sigma_clip(logratios, 3)
median = np.median(logratios[ind])
std = np.nanstd(logratios[ind])
vmin = median - std
vmax = median + std

h = ras[ind]
d = decs[ind]
x = azs[ind]
a = alts[ind]
c = logratios[ind]
f = int_fluxes[ind]
r = local_rmses[ind]
S200 = S200s[ind]
alpha = alphas[ind]

# Save the results as a FITS table
t = Table([h, d, x, a, f, r, S200, alpha, c], names = ("RA_offset", "Dec", "Azimuth", "Altitude", "flux", "local_rms", "S_200", "alpha", "log10ratio"))
t.write(concat_table, overwrite=True)

# Get the highest S/N measurements
if results.SNR_threshold is None:
    SNR = sorted(f /r, reverse=True)
    threshold = SNR[results.Nsrc]
else:
    threshold = results.SNR_threshold

good = np.where(f / r > threshold)

P, res, rank, sv, cond = np.polyfit(np.array(d[good]), np.array(c[good]), results.poly_order, full=True, w = f[good]/r[good])
decmodel = np.poly1d(P)

# Remove outliers
model_subtracted = c[good] - decmodel(d[good])
indices = sigma_clip(model_subtracted, 2)

# Re-fit model
P_dec,res,rank,sv,cond = np.polyfit(np.array(d[good][indices]),np.array(c[good][indices]), results.poly_order, full=True, w = f[good][indices]/r[good][indices])
decmodel = np.poly1d(P_dec)

# TODO write these to a file
#print("fit parameters:")
#print(P)

# Now that we have accumulated Dec, apply the polynomials to the concatenated catalogue, and then fit over RA
new_int_fluxes = int_fluxes * 10**(decmodel(decs))
new_c = np.log10(S200s*(centfreq/200.)**alphas / new_int_fluxes)

# weights can stay the same, because if we had applied the flux density correction, it would have been to both the integrated flux densities and the local RMS
# Might as well keep the clipping I've already applied, as well
P_ra, res, rank, sv,cond = np.polyfit(np.array(h[good][indices]),np.array(new_c[good][indices]), results.poly_order, full=True, w = f[good][indices]/r[good][indices])
ramodel = np.poly1d(P_ra)

if results.make_plots is True:
# Dec plot
    w = f[good][indices]/r[good][indices]
    x = d[good][indices]
    y = c[good][indices]
    x = [X for (W,X) in sorted(zip(w,x))]
    y = [Y for (W,Y) in sorted(zip(w,y))]
    w = sorted(w)

    SNR = np.log10(w)
    figsize = (6,6)
    fitplot = plt.figure(figsize=figsize)
    ax = fitplot.add_subplot(111)
    
    ax.set_title(title, fontsize=10)
    ax.scatter(x, y, marker='.', c=SNR, cmap=cm.Greys)
    x = sorted(x)
    ax.plot(x, decmodel(x), '-', ms=1)
    ax.set_xlabel("Declination (deg)")
    ax.set_ylabel("log10 ratio")

# Where the S/N is at least 30, find the min and max ratios, so the plots look good
    maw = np.ma.masked_less(w, 30)
    may = np.ma.masked_array(y, mask=np.ma.getmask(maw))
    ax.set_ylim([np.ma.min(may), np.ma.max(may)])

    fitplot.savefig(dec_plot, bbox_inches="tight")

# RA plot after Dec correction
    w = f[good][indices]/r[good][indices]
    x = h[good][indices]
    y = new_c[good][indices]
    x = [X for (W,X) in sorted(zip(w,x))]
    y = [Y for (W,Y) in sorted(zip(w,y))]
    w = sorted(w)

    SNR = np.log10(w)
    figsize = (6,6)
    fitplot = plt.figure(figsize=figsize)
    ax = fitplot.add_subplot(111)
    
    ax.set_title(title, fontsize=10)
    ax.scatter(x, y, marker='.', c=SNR, cmap=cm.Greys)
    x = sorted(x)
    ax.plot(x, ramodel(x), '-', ms=1)
    ax.set_xlabel("RA offset (deg)")
    ax.set_ylabel("log10 ratio")

# Where the S/N is at least 30, find the min and max ratios, so the plots look good
    maw = np.ma.masked_less(w, 30)
    may = np.ma.masked_array(y, mask=np.ma.getmask(maw))
    ax.set_ylim([np.ma.min(may), np.ma.max(may)])

    fitplot.savefig(ra_plot, bbox_inches="tight")

if results.do_rescale is True:
    for fitsimage in infiles:
        if results.correct_all is True:
            extlist = [".fits", "_bkg.fits", "_rms.fits"]
        else:
            extlist = [".fits"]
        for ext in extlist:
            infits = fitsimage.replace(".fits", ext)
            outfits = infits.replace(".fits", "_rescaled.fits")

    # Modify each fits file to produce a new version
            hdu_in = fits.open(infits)
        # wcs in format [stokes,freq,y,x]; stokes and freq are length 1 if they exist
            w = wcs.WCS(hdu_in[0].header, naxis=2)
            naxes = hdu_in[0].header["NAXIS"]
    # going to need the RA in order to calculate the RA offsets
            path, fl = os.path.split(infits)
            meta = fits.getheader("{0}/{1}.metafits".format(path, fl[0:10]))
            ra_cent = meta["RA"]
            #create an array but don't set the values (they are random)
            if naxes == 4:
                indexes = np.empty((hdu_in[0].data.shape[2]*hdu_in[0].data.shape[3],2), dtype=int)
                idx = np.array([(j,0) for j in range(hdu_in[0].data.shape[3])])
                j=hdu_in[0].data.shape[3]
                for i in range(hdu_in[0].data.shape[2]):
                    idx[:,1]=i
                    indexes[i*j:(i+1)*j] = idx
            elif naxes == 2:
                indexes = np.empty((hdu_in[0].data.shape[0]*hdu_in[0].data.shape[1],2), dtype=int)
                idx = np.array([(j,0) for j in range(hdu_in[0].data.shape[1])])
                j=hdu_in[0].data.shape[1]
                for i in range(hdu_in[0].data.shape[0]):
                    idx[:,1]=i
                    indexes[i*j:(i+1)*j] = idx
             
        #put ALL the pixels into our vectorized functions and minimise our overheads
            ra,dec = w.wcs_pix2world(indexes,1).transpose()
            dec_corr = np.zeros(dec.shape)
            ra_corr = np.zeros(ra.shape)
    # We generated log10 ratios so use 10^ to get back to raw correction 
    # e.g. a 4th order polynomial would look like:
    # corr = 10** ( a*(Dec)^3 + b*(Dec)^2 + c*Dec + d)
            for i in range(0,results.poly_order+1):
                dec_corr += P_dec[i]*pow(dec, results.poly_order-i)
            dec_corr = 10**dec_corr
            for i in range(0,results.poly_order+1):
                ra_corr += P_ra[i]*pow(ra-ra_cent, results.poly_order-i)
            ra_corr = 10**ra_corr
            corr = dec_corr * ra_corr
            if naxes == 4:
                corr = corr.reshape(hdu_in[0].data.shape[2],hdu_in[0].data.shape[3])
            elif naxes == 2:
                corr = corr.reshape(hdu_in[0].data.shape[0],hdu_in[0].data.shape[1])
            hdu_in[0].data = np.array(corr*hdu_in[0].data, dtype=np.float32)
            hdu_in.writeto(outfits, overwrite=True)
            hdu_in.close()
