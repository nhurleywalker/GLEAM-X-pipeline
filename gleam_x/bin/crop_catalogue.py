#!/usr/bin/env python
import sys
from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np

from astropy.io import fits
from argparse import ArgumentParser

from gleam_x.bin.beam_value_at_radec import beam_value, parse_metafits

def unwrap(RA):
    if RA > 180.:
        return RA - 360.
    else:
        return RA
vunwrap = np.vectorize(unwrap)

if __name__ == '__main__':
    parser = ArgumentParser(description='Will produce a crop catalogue from a sky-model catalogue.')
    parser.add_argument('--ra', type=str,
                        help="The RA center of your crop in decimal degrees")

    parser.add_argument('--dec',type=str,
                        help="The declination center of your crop in decimal degrees")

    parser.add_argument('--radius',type=float,
                        help="The radius of your crop circle in degrees")

    parser.add_argument('--minflux',type=float, default=1.0,
                        help="The minimum flux density of the source (default = 1.0 Jy)")

    parser.add_argument('--nobeamselect', action="store_false",  default=True, dest="beamselect",
                        help="Use the primary beam to (crudely) attenuate the catalogue fluxes when calculating the minimum flux (default=True)")

    parser.add_argument('--attenuate', action="store_true", default=False,
                        help="Use the primary beam to (crudely) attenuate the output source flux densities (default=False, therefore use -apply-beam in calibrate to apply the beam)")

    parser.add_argument('--metafits',type=str,
                        help="The metafits file for your observation (only necessary if using the beam attenuation option)")

    parser.add_argument('--catalogue', type=str, dest='cat',
                        help="The filename of the catalogue you want to read in (fits format).")

    parser.add_argument('--racol',type=str, default="RAJ2000",
                        help="The name of the RA column (in decimal degrees) in your catalogue (default = RAJ2000)")

    parser.add_argument('--decol', type=str, default="DEJ2000",
                        help="The name of your Dec column (in decimal degrees) in your catalogue (default = DEJ2000)")

    parser.add_argument('--fluxcol',type=str, default="int_flux_wide",
                        help="The name of the flux density column (default = int_flux_wide)")

    parser.add_argument('--alphacol',type=str, default="alpha",
                        help="The name of the spectral index column (default = alpha)")

    parser.add_argument('--plot', type=str, default=None,
                        help="Specify an output name to generate a plot of the resulting local sky model (default = None)")

    parser.add_argument('--output',type=str, default="cropped_catalogue.fits",
                        help="The filename of the output cropped catalogue (fits format).")
    args = parser.parse_args()

    # This needs to be done immediately before I import any other modules which import matplotlib!
    if args.plot is not None:
        import matplotlib as mpl
        mpl.use('Agg') # So does not use display
        import matplotlib.pyplot as plt

    pos = SkyCoord(args.ra, args.dec, unit=(u.deg, u.deg))

    # Read in the catalogue
    temp = fits.open(args.cat)
    data = temp[1].data

    coords = SkyCoord(data[args.racol], data[args.decol], unit=(u.deg, u.deg))
    separations = np.array(pos.separation(coords))
    # Select sources within crop radius of your original RA and Dec
    indices = np.where(separations<args.radius)
    # Select only sources which meet the minimum flux density criterion
    fluxcut = np.where(data[args.fluxcol]>args.minflux)
    # Select only sources with non-zero spectral indices
    alphacut = np.where(np.logical_not(np.isnan(data[args.alphacol])))
    indices = np.intersect1d(fluxcut,indices)
    indices = np.intersect1d(alphacut,indices)

    # Now that we have some subset, check if beam attenuation is on, and if it is, attenuate and recalculate:

    if args.beamselect is True or args.attenuate is True:
        if args.metafits is False:
            print("No metafits file selected.")
            sys.exit(1)
        
    if args.beamselect is True:
        t, delays, freq, gridnum = parse_metafits(args.metafits)
        x,y = beam_value(data[args.racol][indices], data[args.decol][indices], t, delays, freq, gridnum)
        i = (x + y)/2
        
        # Attenuate the fluxes
        data[args.fluxcol][indices] = i * data[args.fluxcol][indices]
        
        # Select only the sources which meet the minimum flux criterion
        subindices = np.where(data[args.fluxcol][indices] > args.minflux)
        
        # Undo the attenuation
        data[args.fluxcol][indices] = data[args.fluxcol][indices] / i
        
        # Select the final indices
        indices = indices[subindices]

    if args.attenuate is True:
        t, delays, freq, gridnum = parse_metafits(args.metafits)
        x, y = beam_value(data[args.racol][indices], data[args.decol][indices], t, delays, freq, gridnum)
        
        # Perform a crude attenuation of the source flux densities
        i = (x + y)/2

        # Attenuate the fluxes
        data[args.fluxcol][indices] = i * data[args.fluxcol][indices]

    nselected=indices.shape[0]
    noriginal=data.shape[0]

    if indices.shape > 0:
        # Write out the sources
        temp[1].data = data[indices]
        temp.writeto(args.output,overwrite=True)
        print("Selected {0} of {1} sources".format(nselected,noriginal))
    else:
        print("No sources selected!")

    if args.plot is not None:
        srcs = coords[indices]

        minra = np.nanmin(srcs.fk5.ra.value)
        maxra = np.nanmax(srcs.fk5.ra.value)
        if maxra - minra > 300.:
            ra = vunwrap(srcs.fk5.ra.value)
        else:
            ra = srcs.fk5.ra.value
        dec = srcs.fk5.dec.value
        
        # Grab the source brightnesses and spectral indices
        fluxd = data[args.fluxcol][indices]
        alpha = data[args.alphacol][indices]

        # Use the source flux density to specify the plotting order (fainter things later)
        order = np.argsort(-1*fluxd)

        # Plot the sources: sources with spectral indices as coloured circles, those without as markers
        bright = np.logical_not(np.isnan(alpha))
        dim = np.isnan(alpha)

        # Create a figure in WCS coordinates
        fig = plt.figure(figsize=(6,6))
        ax = fig.add_axes([0.1, 0.1, 0.7, 0.7])
        points = ax.scatter(ra[order][bright], dec[order][bright], c = alpha[order], s = 20*fluxd[order]*np.log10(1000*fluxd[order]), marker="o", cmap="inferno", vmin=-1.4, vmax=0.3)
        ax.scatter(ra[order][dim], dec[order][dim], marker="x", color="red") #transform = ax.get_transform("fk5")

        # Add a colorbar for the alpha values
        cbaxes_alpha = fig.add_axes([0.83, 0.1, 0.02, 0.7])
        cb_alpha = plt.colorbar(points, cax = cbaxes_alpha, orientation="vertical")
        cb_alpha.set_label("Spectral index (alpha)")

        # Reverse x-axis
        xlims = ax.get_xlim()
        ax.set_xlim(xlims[1], xlims[0])

        # axis labels
        ax.set_xlabel("Right Ascension (deg)")
        ax.set_ylabel("Declination (deg)")

        # Title
        ax.set_title("Observation {0}".format(args.metafits[0:10]))

        fig.savefig(args.plot, bbox_inches="tight")

