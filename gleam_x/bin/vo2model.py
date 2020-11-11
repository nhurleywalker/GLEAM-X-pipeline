#!/usr/bin/env python
# Convert fits and VO catalogues to Andre's sky model format
from __future__ import print_function

import os, sys

# from string import replace

import numpy as np

# tables and votables
import astropy.io.fits as fits
from astropy.io.votable import parse_single_table
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.table import Table
from argparse import ArgumentParser

usage = "Usage: %prog [args] <file>\n"
parser = ArgumentParser(usage=usage)
parser.add_argument(
    "--catalogue",
    type=str,
    dest="catalogue",
    help="The filename of the catalogue you want to read in.",
    default=None,
)
parser.add_argument(
    "--output",
    type=str,
    dest="output",
    help="The filename of the output (default=test.txt).",
    default="test.txt",
)
parser.add_argument(
    "--namecol",
    type=str,
    dest="namecol",
    help="The name of the Name column (no default).",
    default="Name",
)
parser.add_argument(
    "--racol",
    type=str,
    dest="racol",
    help="The name of the RA column (default=ra_str).",
    default="ra_str",
)
parser.add_argument(
    "--decol",
    type=str,
    dest="decol",
    help="The name of the Dec column (default=dec_str).",
    default="dec_str",
)
parser.add_argument(
    "--acol",
    type=str,
    dest="acol",
    help="The name of the major axis column (default=a_wide).",
    default="a_wide",
)
parser.add_argument(
    "--bcol",
    type=str,
    dest="bcol",
    help="The name of the minor axis column (default=b_wide).",
    default="b_wide",
)
parser.add_argument(
    "--pacol",
    type=str,
    dest="pacol",
    help="The name of the position angle column (default=pa_wide).",
    default="pa_wide",
)
parser.add_argument(
    "--fluxcol",
    type=str,
    dest="fluxcol",
    help="The name of the flux density column (default=int_flux_wide).",
    default="int_flux_wide",
)
parser.add_argument(
    "--freq",
    type=float,
    dest="freq",
    help="The frequency at which the flux density measurements are made, in MHz (default=200).",
    default=200.0,
)
parser.add_argument(
    "--alphacol",
    type=str,
    dest="alphacol",
    help="The name of the spectral index alpha-term column (default=alpha).",
    default="alpha",
)
parser.add_argument(
    "--betacol",
    type=str,
    dest="betacol",
    help="The name of the spectral index curvature beta-term column (default=beta).",
    default="beta",
)
parser.add_argument(
    "--alpha",
    type=float,
    dest="alpha",
    help="The value of alpha to use if there is no alpha column (default = -0.83)",
    default=-0.83,
)
parser.add_argument(
    "--beta",
    type=float,
    dest="beta",
    help="The value of beta to use if there is no beta column (default = 0.0).",
    default=0.0,
)
parser.add_argument(
    "--point",
    dest="point",
    action="store_true",
    default=False,
    help="Output unresolved sources as point sources instead of Gaussians (default=False). Need to specify resolution, and both int and peak flux columns for this to work, or have blank major/minor axis columns to indicate unresolved sources.",
)
parser.add_argument(
    "--resolution",
    type=float,
    dest="resolution",
    default=1.2,
    help="The int/peak value below which a source is considered unresolved (default=1.2).",
)
parser.add_argument(
    "--intflux",
    type=str,
    dest="intflux",
    help="Int flux column (default=int_flux_wide).",
    default="int_flux_wide",
)
parser.add_argument(
    "--peakflux",
    type=str,
    dest="peakflux",
    help="Peak flux column (default=peak_flux_wide).",
    default="peak_flux_wide",
)
# parser.add_option('--betacol',type=str, dest="betacol",
#                    help="The name of the spectral index beta-term column (default=beta).", default="beta")
args = parser.parse_args()

if args.output is None:
    output = "test.txt"
else:
    output = args.output

if args.catalogue is None:
    print("must specify input catalogue")
    sys.exit(1)
else:
    filename, file_extension = os.path.splitext(args.catalogue)
    if file_extension == ".fits":
        data = Table.read(args.catalogue).to_pandas()
        data["Name"] = data["Name"].str.decode("utf-8")

    elif file_extension == ".vot":
        temp = parse_single_table(args.catalogue)
        data = temp.array

if args.fluxcol is None:
    print("Must have a valid flux density column")
    sys.exit(1)
try:
    names = data[args.namecol]
except KeyError:
    names = np.array(
        [
            "J" + (data[args.racol][i][:-3] + data[args.decol][i][:-3]).replace(":", "")
            for i in range(len(data[args.racol]))
        ]
    )
try:
    alpha = data[args.alphacol]
except KeyError:
    alpha = args.alpha * np.ones(shape=data[args.fluxcol].shape)
try:
    beta = data[args.betacol]
except KeyError:
    beta = args.beta * np.ones(shape=data[args.fluxcol].shape)

if type(data[args.racol][0]) == str:
    rastr = True
else:
    rastr = False

# Generate an output in Andre's sky model format
# formatter="source {{\n  name \"{Name:s}\"\n  component {{\n    type gaussian\n    position {RA:s} {Dec:s}\n    shape {a:s} {b:s} {pa:s}\n    sed {{\n      frequency {freq:3.0f} MHz\n      fluxdensity Jy {flux:s} 0 0 0\n      spectral-index {{ {alpha:s} {beta:2.2f} }}\n    }}\n  }}\n}}\n"
gformatter = 'source {{\n  name "{Name:s}"\n  component {{\n    type {shape:s}\n    position {RA:s} {Dec:s}\n    shape {a:2.1f} {b:2.1f} {pa:4.1f}\n    sed {{\n      frequency {freq:3.0f} MHz\n      fluxdensity Jy {flux:4.7f} 0 0 0\n      spectral-index {{ {alpha:2.2f} {beta:2.2f} }}\n    }}\n  }}\n}}\n'
pformatter = 'source {{\n  name "{Name:s}"\n  component {{\n    type {shape:s}\n    position {RA:s} {Dec:s}\n    sed {{\n      frequency {freq:3.0f} MHz\n      fluxdensity Jy {flux:4.7f} 0 0 0\n      spectral-index {{ {alpha:2.2f} {beta:2.2f} }}\n    }}\n  }}\n}}\n'

shape = np.array(["gaussian"] * data.shape[0])

if args.point:
    try:
        srcsize = data[args.intflux] / data[args.peakflux]
        indices = np.where(srcsize < args.resolution)
    except KeyError:
        indices = np.where(np.isnan(data[args.acol]))
    shape[indices] = "point"

bigzip = zip(
    names,
    data[args.racol],
    data[args.decol],
    data[args.acol],
    data[args.bcol],
    data[args.pacol],
    data[args.fluxcol],
    alpha,
    beta,
    shape,
)

with open(args.output, "w") as f:
    f.write("skymodel fileformat 1.1\n")
    for Name, RA, Dec, a, b, pa, flux, alpha, beta, shape in bigzip:

        if rastr is True:
            coords = SkyCoord(RA, Dec, frame="fk5", unit=(u.hour, u.deg))
        else:
            coords = SkyCoord(RA, Dec, frame="fk5", unit=(u.deg, u.deg))

        RA = coords.ra.to_string(u.hour)
        Dec = coords.dec.to_string(u.deg)

        if shape == "gaussian":
            f.write(
                gformatter.format(
                    Name=Name,
                    RA=RA,
                    Dec=Dec,
                    a=a,
                    b=b,
                    pa=pa,
                    flux=flux,
                    alpha=alpha,
                    beta=beta,
                    freq=args.freq,
                    shape=shape,
                )
            )

        elif shape == "point":
            f.write(
                pformatter.format(
                    Name=Name,
                    RA=RA,
                    Dec=Dec,
                    flux=flux,
                    alpha=alpha,
                    beta=beta,
                    freq=args.freq,
                    shape=shape,
                )
            )

