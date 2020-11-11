#!/usr/bin/env python
from __future__ import print_function

from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np

from astropy.io import fits
from optparse import OptionParser

def flux_cut(sources, min_flux):
    """Return an array of indicies that describes the sources that are above a minimum flux cut

    Args:
        sources (numpy.array): flux density values to consider
        min_flux (float): minimum flux value for source to qualify
    """
    mask = sources > min_flux

    return mask


def top_brightest(sources, top_n, plot=None):
    """Return a set of indicies that describes the top N brightest sources

    Args:
        sources (bympy.ndarray): flux density values to consider
        top_n (int): number of sources to return

    Keyword Args:
        plot (str): base string to modify and save a figure to (default: None)
    """
    # sort in ascending order
    sort_idx = np.argsort(sources)[::-1]

    return sort_idx[:top_n]


def percentile_total(sources, percentile, plot=None):
    """Sorts sources from brightest to faintests, and selects the set of sources whose sum flux represents some percentile of the total

    Args:
        sources (numpy.ndarray): flux density values to consider
        percentile (float): percentile targe
    """
    if not (0 <= percentile <= 100.0):
        raise ValueError("Percentile needs to be between 0 to 100")

    # Sort the indices to get brightest to faintest
    sort_idx = np.argsort(sources)[::-1]

    # Get the cumulative sum across sources and convert to a percentage of total
    cumulative = np.cumsum(sources[sort_idx])
    cumulative_perc = cumulative / cumulative[-1] * 100.0

    # Select all sources that contribute to meet the desired percentile
    mask = cumulative_perc < percentile

    return sort_idx[mask]


def unwrap(RA):
    if RA > 180.:
        return RA - 360.
    else:
        return RA
vunwrap = np.vectorize(unwrap)

if __name__ == "__main__":

    usage="Usage: %prog [options] <file>\n"
    parser = OptionParser(usage=usage)
    parser.add_option('--ra',type="string", dest="ra",
                        help="The RA center of your crop in decimal degrees")
    parser.add_option('--dec',type="string", dest="dec",
                        help="The declination center of your crop in decimal degrees")
    parser.add_option('--radius',type="float", dest="radius",
                        help="The radius of your crop circle in degrees")
    
    parser.add_option(
        "--minflux",
        type="float",
        default=None,
        help="The minimum flux density of the source (default = 1.0 Jy)",
    )

    parser.add_option(
        "--top-brightest",
        type="int",
        default=None,
        help="Save the top TOP-BRIGHTEST number of sourcesas part of the model",
    )

    parser.add_option(
        "--percentile-total",
        type="float",
        default=None,
        help="Select the brightest set of sources whose cumulative flux represent PERCENT of the total flux of potential sources in the sky-model (0 to 100)",
    )

    parser.add_option('--nobeamselect', action="store_false", dest="beamselect", default=True,
                        help="Use the primary beam to (crudely) attenuate the catalogue fluxes when calculating the minimum flux (default=True)")
    parser.add_option('--attenuate', action="store_true", dest="attenuate", default=False,
                        help="Use the primary beam to (crudely) attenuate the output source flux densities (default=False, therefore use -apply-beam in calibrate to apply the beam)")
    parser.add_option('--metafits',type="string", dest="metafits",
                        help="The metafits file for your observation (only necessary if using the beam attenuation option)")
    parser.add_option('--catalogue',type="string", dest="cat",
                        help="The filename of the catalogue you want to read in (fits format).")
    parser.add_option('--racol',type="string", dest="racol", default="RAJ2000",
                        help="The name of the RA column (in decimal degrees) in your catalogue (default = RAJ2000)")
    parser.add_option('--decol',type="string", dest="decol", default="DEJ2000",
                        help="The name of your Dec column (in decimal degrees) in your catalogue (default = DEJ2000)")
    parser.add_option('--fluxcol',type="string", dest="fluxcol", default="int_flux_wide",
                        help="The name of the flux density column (default = int_flux_wide)")
    parser.add_option('--alphacol',type="string", dest="alphacol", default="alpha",
                        help="The name of the spectral index column (default = alpha)")
    parser.add_option('--plot', type="string", dest="plot", default=None,
                        help="Specify an output name to generate a plot of the resulting local sky model (default = None)")
    parser.add_option('--output',type="string", dest="output", default="cropped_catalogue.fits",
                        help="The filename of the output cropped catalogue (fits format).")
    (options, args) = parser.parse_args()

    if options.plot is not None:
        import matplotlib as mpl
        mpl.use('Agg') # So does not use display
        import matplotlib.pyplot as plt

    pos = SkyCoord(options.ra, options.dec, unit=(u.deg, u.deg))

    # Read in the catalogue
    temp = fits.open(options.cat)
    data = temp[1].data

    coords = SkyCoord(data[options.racol], data[options.decol], unit=(u.deg, u.deg))
    separations = np.array(pos.separation(coords))
    # Select sources within crop radius of your original RA and Dec
    indices = np.where(separations<options.radius)
    # Select only sources which meet the minimum flux density criterion
    if options.minflux is not None:
        fluxcut = np.where(data[options.fluxcol] > options.minflux)
        indices = np.intersect1d(fluxcut, indices)

    # Select only sources with non-zero spectral indices
    alphacut = np.where(np.logical_not(np.isnan(data[options.alphacol])))
    indices = np.intersect1d(alphacut,indices)

    # Now that we have some subset, check if beam attenuation is on, and if it is, attenuate and recalculate:

    if options.beamselect is True or options.attenuate is True:
        if options.metafits is False:
            print("No metafits file selected.")
            sys.exit(1)
        from beam_value_at_radec import beam_value
        from beam_value_at_radec import parse_metafits

    if options.beamselect is True:
        t, delays, freq = parse_metafits(options.metafits)
        x,y = beam_value(data[options.racol][indices], data[options.decol][indices], t, delays, freq)
        i = (x + y)/2
    # Attenuate the fluxes
        data[options.fluxcol][indices] = i * data[options.fluxcol][indices]
    # Select only the sources which meet the minimum flux criterion
        if options.minflux is not None:
            subindices = flux_cut(data[options.fluxcol][indices], options.minflux)
        elif options.top_brightest is not None:
            subindices = top_brightest(
                data[options.fluxcol][indices], options.top_brightest, plot=options.plot
            )
        elif options.percentile_total is not None:
            subindices = percentile_total(
                data[options.fluxcol][indices], options.percentile_total, plot=options.plot
            )
        else:
            raise ValueError("A cropping mode has not been selected")


        print(indices)

    # Undo the attenuation
        data[options.fluxcol][indices] = data[options.fluxcol][indices] / i
    # Select the final indices
        indices = indices[subindices]

    if options.attenuate is True:
        t, delays, freq = parse_metafits(options.metafits)
        x,y = beam_value(data[options.racol][indices], data[options.decol][indices], t, delays, freq)
    # Perform a crude attenuation of the source flux densities
        i = (x + y)/2
    # Attenuate the fluxes
        data[options.fluxcol][indices] = i * data[options.fluxcol][indices]

    nselected=indices.shape[0]
    noriginal=data.shape[0]

    if indices.shape > 0:
        # Write out the sources
        temp[1].data = data[indices]
        temp.writeto(options.output,overwrite=True)
        print("Selected {0} of {1} sources".format(nselected,noriginal))
    else:
        print("No sources selected!")

    if options.plot is not None:
        srcs = coords[indices]

        minra = np.nanmin(srcs.fk5.ra.value)
        maxra = np.nanmax(srcs.fk5.ra.value)
        if maxra - minra > 300.:
            ra = vunwrap(srcs.fk5.ra.value)
        else:
            ra = srcs.fk5.ra.value
        dec = srcs.fk5.dec.value
    # Grab the source brightnesses and spectral indices
        fluxd = data[options.fluxcol][indices]
        alpha = data[options.alphacol][indices]

    # Use the source flux density to specify the plotting order (fainter things later)
        order = np.argsort(-1*fluxd)

    # Plot the sources: sources with spectral indices as coloured circles, those without as markers
        bright = np.logical_not(np.isnan(alpha))
        dim = np.isnan(alpha)

    # Create a figure in WCS coordinates
        fig = plt.figure(figsize=(6,6))
        ax = fig.add_axes([0.1, 0.1, 0.7, 0.7])
        points = ax.scatter(ra[order][bright], dec[order][bright], c = np.squeeze(alpha[order]), s = 20*fluxd[order]*np.log10(1000*fluxd[order]), marker="o", cmap="inferno", vmin=-1.4, vmax=0.3)
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
        ax.set_title("Observation {0}".format(options.metafits[0:10]))

        fig.savefig(options.plot, bbox_inches="tight")

