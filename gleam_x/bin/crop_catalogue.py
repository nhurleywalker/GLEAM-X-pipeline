#!/usr/bin/env python
import matplotlib as mpl

mpl.use("Agg")  # So does not use display
import matplotlib.pyplot as plt

import sys
from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np

from astropy.io import fits
from argparse import ArgumentParser

from gleam_x.bin.beam_value_at_radec import beam_value, parse_metafits


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

    if plot is not None:
        parts = plot.split(".")
        plot = f"{'.'.join(parts[:-1])}-top-brightest.{parts[-1]}"

        fig, ax = plt.subplots(1, 1)

        ax.plot(np.arange(len(sources)), sources[sort_idx], "ro")
        ax.axvline(top_n)

        ax.set(title=f"{top_n} of {len(sources)} selected", xscale="log")

        fig.savefig(plot)

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
    first_false = np.argwhere(~mask)[0, 0]

    if plot is not None:
        parts = plot.split(".")
        plot = f"{'.'.join(parts[:-1])}-percentile-total.{parts[-1]}"

        fig, ax = plt.subplots(1, 1)

        ax.plot(np.arange(len(sources)), cumulative_perc, "ro")
        # ax.plot(np.arange(len(sources)), cumulative, "ro")
        ax.axvline(first_false)

        ax.set(
            title=f"{np.sum(mask)} of {len(sources)} selected, percentile {percentile}, cumulative flux {cumulative[-1]:.0f}Jy",
            # xscale="log",
        )

        fig.savefig(plot)

    return sort_idx[mask]


def unwrap(RA):
    if RA > 180.0:
        return RA - 360.0
    else:
        return RA


vunwrap = np.vectorize(unwrap)

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Will produce a crop catalogue from a sky-model catalogue."
    )
    parser.add_argument(
        "--ra", type=str, help="The RA center of your crop in decimal degrees"
    )

    parser.add_argument(
        "--dec", type=str, help="The declination center of your crop in decimal degrees"
    )

    parser.add_argument(
        "--radius", type=float, help="The radius of your crop circle in degrees"
    )

    parser.add_argument(
        "--minflux",
        type=float,
        default=None,
        help="The minimum flux density of the source (default = 1.0 Jy)",
    )

    parser.add_argument(
        "--top-brightest",
        default=None,
        type=int,
        help="Save the top TOP-BRIGHTEST number of sourcesas part of the model",
    )

    parser.add_argument(
        "--percentile-total",
        type=float,
        default=None,
        help="Select the brightest set of sources whose cumulative flux represent PERCENT of the total flux of potential sources in the sky-model (0 to 100)",
    )

    parser.add_argument(
        "--nobeamselect",
        action="store_false",
        default=True,
        dest="beamselect",
        help="Use the primary beam to (crudely) attenuate the catalogue fluxes when calculating the minimum flux (default=True)",
    )

    parser.add_argument(
        "--attenuate",
        action="store_true",
        default=False,
        help="Use the primary beam to (crudely) attenuate the output source flux densities (default=False, therefore use -apply-beam in calibrate to apply the beam)",
    )

    parser.add_argument(
        "--metafits",
        type=str,
        help="The metafits file for your observation (only necessary if using the beam attenuation option)",
    )

    parser.add_argument(
        "--catalogue",
        type=str,
        dest="cat",
        help="The filename of the catalogue you want to read in (fits format).",
    )

    parser.add_argument(
        "--racol",
        type=str,
        default="RAJ2000",
        help="The name of the RA column (in decimal degrees) in your catalogue (default = RAJ2000)",
    )

    parser.add_argument(
        "--decol",
        type=str,
        default="DEJ2000",
        help="The name of your Dec column (in decimal degrees) in your catalogue (default = DEJ2000)",
    )

    parser.add_argument(
        "--fluxcol",
        type=str,
        default="int_flux_wide",
        help="The name of the flux density column (default = int_flux_wide)",
    )

    parser.add_argument(
        "--alphacol",
        type=str,
        default="alpha",
        help="The name of the spectral index column (default = alpha)",
    )

    parser.add_argument(
        "--plot",
        type=str,
        default=None,
        help="Specify an output name to generate a plot of the resulting local sky model (default = None)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="cropped_catalogue.fits",
        help="The filename of the output cropped catalogue (fits format).",
    )
    args = parser.parse_args()

    pos = SkyCoord(args.ra, args.dec, unit=(u.deg, u.deg))

    # Read in the catalogue
    temp = fits.open(args.cat)
    data = temp[1].data

    coords = SkyCoord(data[args.racol], data[args.decol], unit=(u.deg, u.deg))
    separations = np.array(pos.separation(coords))

    # Select sources within crop radius of your original RA and Dec
    indices = np.where(separations < args.radius)

    # Select only sources which meet the minimum flux density criterion
    if args.minflux is not None:
        fluxcut = np.where(data[args.fluxcol] > args.minflux)
        indices = np.intersect1d(fluxcut, indices)

    # Select only sources with non-zero spectral indices
    alphacut = np.where(np.logical_not(np.isnan(data[args.alphacol])))
    indices = np.intersect1d(alphacut, indices)

    # Now that we have some subset, check if beam attenuation is on, and if it is, attenuate and recalculate:

    if args.beamselect is True or args.attenuate is True:
        if args.metafits is False:
            print("No metafits file selected.")
            sys.exit(1)

    if args.beamselect is True:
        t, delays, freq, gridnum = parse_metafits(args.metafits)
        x, y = beam_value(
            data[args.racol][indices],
            data[args.decol][indices],
            t,
            delays,
            freq,
            gridnum,
        )
        i = (x + y) / 2

        # Attenuate the fluxes
        data[args.fluxcol][indices] = i * data[args.fluxcol][indices]

        if args.minflux is not None:
            subindices = flux_cut(data[args.fluxcol][indices], args.minflux)
        elif args.top_brightest is not None:
            subindices = top_brightest(
                data[args.fluxcol][indices], args.top_brightest, plot=args.plot
            )
        elif args.percentile_total is not None:
            subindices = percentile_total(
                data[args.fluxcol][indices], args.percentile_total, plot=args.plot
            )
        else:
            raise ValueError("A cropping mode has not been selected")

        # Undo the attenuation
        data[args.fluxcol][indices] = data[args.fluxcol][indices] / i

        # Select the final indices
        indices = indices[subindices]

    if args.attenuate is True:
        t, delays, freq, gridnum = parse_metafits(args.metafits)
        x, y = beam_value(
            data[args.racol][indices],
            data[args.decol][indices],
            t,
            delays,
            freq,
            gridnum,
        )

        # Perform a crude attenuation of the source flux densities
        i = (x + y) / 2

        # Attenuate the fluxes
        data[args.fluxcol][indices] = i * data[args.fluxcol][indices]

    nselected = indices.shape[0]
    noriginal = data.shape[0]

    if nselected > 0:
        # Write out the sources
        temp[1].data = data[indices]
        temp.writeto(args.output, overwrite=True)
        print("Selected {0} of {1} sources".format(nselected, noriginal))
    else:
        print("No sources selected!")

    if args.plot is not None:
        srcs = coords[indices]

        minra = np.nanmin(srcs.fk5.ra.value)
        maxra = np.nanmax(srcs.fk5.ra.value)
        if maxra - minra > 300.0:
            ra = vunwrap(srcs.fk5.ra.value)
        else:
            ra = srcs.fk5.ra.value
        dec = srcs.fk5.dec.value

        # Grab the source brightnesses and spectral indices
        fluxd = data[args.fluxcol][indices]
        alpha = data[args.alphacol][indices]

        # Use the source flux density to specify the plotting order (fainter things later)
        order = np.argsort(-1 * fluxd)

        # Plot the sources: sources with spectral indices as coloured circles, those without as markers
        bright = np.logical_not(np.isnan(alpha))
        dim = np.isnan(alpha)

        # Create a figure in WCS coordinates
        fig = plt.figure(figsize=(6, 6))
        ax = fig.add_axes([0.1, 0.1, 0.7, 0.7])
        points = ax.scatter(
            ra[order][bright],
            dec[order][bright],
            c=alpha[order],
            s=20 * fluxd[order] * np.log10(1000 * fluxd[order]),
            marker="o",
            cmap="inferno",
            vmin=-1.4,
            vmax=0.3,
        )
        ax.scatter(
            ra[order][dim], dec[order][dim], marker="x", color="red"
        )  # transform = ax.get_transform("fk5")

        # Add a colorbar for the alpha values
        cbaxes_alpha = fig.add_axes([0.83, 0.1, 0.02, 0.7])
        cb_alpha = plt.colorbar(points, cax=cbaxes_alpha, orientation="vertical")
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

