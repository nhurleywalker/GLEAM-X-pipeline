#!/usr/bin/env python

from astropy.time import Time
from astropy.io import fits
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
import astropy.units as u

import numpy as np

import glob

import matplotlib.pyplot as plt
import matplotlib.cm as cm

#inv = cmap_map(lambda x: 1-x, cm.PiYG)

# TODO make an argument parser and add this as an option
infiles = glob.glob("*_matched.fits")

mwa = EarthLocation.of_site("Murchison Widefield Array")

def sigma_clip(ratios):
    median = np.median(ratios)
    std = np.nanstd(ratios)
    ind = np.intersect1d(np.where(ratios > median-std), np.where(ratios < median + std))
    return ind

def plot_altaz(alts, azs, ratios, int_fluxes, ymin, ymax, vmin, vmax, alpha, projection):
    fig = plt.figure()
    ax = fig.add_axes([0.05,0.1,0.8,0.8], projection=projection)
    cbaxes = fig.add_axes([0.85, 0.1, 0.03, 0.85])
    sc = ax.scatter(x, y, c = c, s = s, vmin=vmin, vmax=vmax, cmap="spring", alpha=alpha, edgecolors="face")
    if projection == "polar":
        ax.set_theta_zero_location('N')
        ax.set_ylabel("Zenith angle")
    else:
        ax.set_ylabel("Altitude")
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel("Azimuth")
    cb = plt.colorbar(sc, cax = cbaxes, orientation="vertical")
    cb.set_label("Log(Model / Measured) Ratio")
    cb.set_alpha(1)
    cb.draw_all()
    return fig

alts = np.empty(0)
azs = np.empty(0)
ratios = np.empty(0)
int_fluxes = np.empty(0)

for cat in infiles:
    gpstime = Time(int(cat[0:10]), format="gps")
    hdu = fits.open(cat)
    coords = SkyCoord(hdu[1].data["RAJ2000"], hdu[1].data["DEJ2000"], unit=(u.deg, u.deg))
    altaz = coords.transform_to(AltAz(obstime=gpstime, location=mwa))
    int_fluxes = np.append(int_fluxes, hdu[1].data["S_200"])
    alts = np.append(alts, altaz.alt.value)
    azs = np.append(azs, altaz.az.value)
# Probably replace at some point with whatever Stefan changes in his matched tables
    ratios = np.append(ratios, np.log(hdu[1].data["S_200"]/hdu[1].data["flux"]))

# sigma-clip
ind = sigma_clip(ratios)
median = np.median(ratios[ind])
std = np.nanstd(ratios[ind])
vmin = median - std
vmax = median + std


# Choose projection
if np.max(alts) > 85.0:
    projection = "polar"
    azs = np.radians(azs)
    zas = 90. - alts
    y = zas[ind]
# Figure out zenith angle limits
    ymin = 0.0
else:
    projection = None
    y = alts[ind]
# Figure out altitude limts
    ymin = 0.95*np.min(y)
ymax = 1.05*np.max(y)

x = azs[ind]
c = ratios[ind]
s = 100*int_fluxes[ind]

fig = plot_altaz(x, y, c, s, ymin, ymax, vmin, vmax, 0.15, projection)
fig.savefig("accumulated_azel.png")

# Individual plots -- done afterwards so we can use consistent flux scales
for cat in infiles:
    gpstime = Time(int(cat[0:10]), format="gps")
    hdu = fits.open(cat)
    coords = SkyCoord(hdu[1].data["RAJ2000"], hdu[1].data["DEJ2000"], unit=(u.deg, u.deg))
    altaz = coords.transform_to(AltAz(obstime=gpstime, location=mwa))
    int_fluxes = hdu[1].data["S_200"]
    alts = altaz.alt.value
    azs = altaz.az.value
# Probably replace at some point with whatever Stefan changes in his matched tables
    ratios = np.log(hdu[1].data["S_200"]/hdu[1].data["flux"])
    ind = sigma_clip(ratios)
    if projection == "polar":
        azs = np.radians(azs)
        zas = 90. - alts
        y = zas[ind]
    else:
        y = alts[ind]
    x = azs[ind]
    c = ratios[ind]
    s = 100*int_fluxes[ind]
    fig = plot_altaz(x, y, c, s, ymin, ymax, vmin, vmax, 0.85, projection)
    fig.savefig(cat[0:10]+"_altaz_ratios.png")
