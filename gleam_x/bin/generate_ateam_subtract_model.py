#!/usr/bin/env python

import os
from typing import Tuple, Any
from collections import defaultdict

import numpy as np
import astropy.units as u

from argparse import ArgumentParser
from astropy.wcs import WCS
from astropy.io import fits
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from astropy.table import Table
from mwa_pb_lookup.lookup_beam import beam_lookup_1d as gleamx_beam_lookup
from gleam_x.bin.beam_value_at_radec import parse_metafits, beam_value
from gleam_x.db.check_src_fov import check_coords

# TODO: Move to a proper GLEAM-X location
# MWA location from CONV2UVFITS/convutils.h
LAT = -26.703319
LON = 116.67081
ALT = 377.0

LOCATION = EarthLocation.from_geodetic(
    lat=LAT * u.deg, lon=LON * u.deg, height=ALT * u.m
)

MODEL_MODES = ["subtrmodel", "casa", "casaclean", "count"]

# TODO: Make Source use and return proper units
class Source:
    def __init__(self, name, pos, flux, alpha, beta):
        self.name = name
        self.pos = pos
        self.flux = flux
        self.alpha = alpha
        self.beta = beta

    def __repr__(self):
        return "{0} {1} {2} {3} {4} {5}".format(
            self.name,
            self.pos.ra.deg,
            self.pos.dec.deg,
            self.flux,
            self.alpha,
            self.beta,
        )

    def brightness(self, freq):
        """Return the brightness of the source at the specified nu

        Args:
            freq (float): frequency to evaluate the model at. If `freq` is above 1e6, it is assumed to be in hertz, otherwise MHerts
        """
        freq = freq / 1e6 if freq > 1e6 else freq
        appflux = self.flux * ((freq / 150.0) ** (self.alpha))

        return appflux


# TODO : Move these to a more meaningful location in the GLEAM-X package
casa = Source("CasA", SkyCoord("23h23m24.000s   +58d48m54.00s"), 13000.0, -0.5, 0.0)
cyga = Source("CygA", SkyCoord("19h59m28.35663s +40d44m02.0970s"), 9000.0, -1.0, 0.0)
crab = Source("Crab", SkyCoord("05h34m31.94s    +22d00m52.2s"), 1500.0, -0.5, 0.0)
vira = Source("VirA", SkyCoord("12h30m49.42338s +12d23m28.0439s"), 1200.0, -1.0, 0.0)
pica = Source("PicA", SkyCoord("05h19m49.7229s  -45d46m43.853s"), 570.0, -1.0, 0.0)
hera = Source("HerA", SkyCoord("16h51m11.4s     +04d59m20s"), 520.0, -1.1, 0.0)
hyda = Source("HydA", SkyCoord("09h18m05.651s   -12d05m43.99s"), 350.0, -0.9, 0.0)

BRIGHT_SOURCES = tuple([casa, cyga, crab, vira, pica, hera, hyda])


def ggsm_row_model(row):
    """Transfer a row inro the Andre format for model components

    Args:
        row (astropy.table.row): A row from the astropy.Table of a component

    Returns:
        str: model description of row
    """
    gformatter = 'source {{\n  name "{Name:s}"\n  component {{\n    type {shape:s}\n    position {RA:s} {Dec:s}\n    shape {a:2.1f} {b:2.1f} {pa:4.1f}\n    sed {{\n      frequency {freq:3.0f} MHz\n      fluxdensity Jy {flux:4.7f} 0 0 0\n      spectral-index {{ {alpha:2.2f} {beta:2.2f} }}\n    }}\n  }}\n}}\n'
    pformatter = 'source {{\n  name "{Name:s}"\n  component {{\n    type {shape:s}\n    position {RA:s} {Dec:s}\n    sed {{\n      frequency {freq:3.0f} MHz\n      fluxdensity Jy {flux:4.7f} 0 0 0\n      spectral-index {{ {alpha:2.2f} {beta:2.2f} }}\n    }}\n  }}\n}}\n'

    pos = SkyCoord(row["RAJ2000"], row["DEJ2000"], unit=(u.deg, u.deg))
    RA = pos.ra.to_string(u.hour)
    Dec = pos.dec.to_string(u.deg)

    point = np.isnan(row["a"])
    if point:
        out = pformatter.format(
            Name=row["Name"],
            RA=RA,
            Dec=Dec,
            flux=row["S_200"],
            alpha=row["alpha"],
            beta=row["beta"],
            freq=200,
            shape="point",
        )
    else:
        out = gformatter.format(
            Name=row["Name"],
            RA=RA,
            Dec=Dec,
            a=row["a"],
            b=row["b"],
            pa=row["pa"],
            flux=row["S_200"],
            alpha=row["alpha"],
            beta=row["beta"],
            freq=200,
            shape="gaussian",
        )

    return out


def search_ggsm(a_src, ggsm_sky, search_radius):
    """Search for components around a A-team source and return a mask of components
    that are within a specified search_radius

    Args:
        a_src (Source): A source to search around for nearby components
        ggsm_sky (SkyCoord): Component positions from the GGSM
        search_radius (units): The search radius to use

    Returns:
        np.ndarray: Boolean mask describing whether GSSM components were near a source position
    """
    mask = a_src.separation(ggsm_sky) < search_radius

    return mask


def check_coords_mask(w: WCS, coords: SkyCoord, border_size: int) -> bool:
    """Checks to see whether a source is within an inner region of a image, assuming
    a rectangular mask region that is `border_size` wide around the outside of the 
    GLEAM-X images. 

    Args:
        w (WCS): Assumed GLEAM-X WCS template used for images
        coords (SkyCoord): Position of source to test
        border_size (int): Size of the region around the image that is consider to be masked

    Returns:
        bool: Denotes whether an image is with the center square region of an image
    """

    x, y = w.all_world2pix(coords.ra.deg, coords.dec.deg, 0)

    if (0 + border_size) < x < (w._naxis1 - border_size) and (0 + border_size) < y < (
        w._naxis2 - border_size
    ):
        return True
    else:
        return False


def create_wcs(ra, dec, cenchan):
    """Creates a fake WCS header to generate a MWA primary beam response

    Arguments:
        ra {float} -- Observation pointing direction in degrees
        dec {float} -- Observation pointing direction in degrees
        cenchan {float} -- Central channel

    Returns:
        {astropy.wcs.WCS} -- WCS information describing the observation
    """
    pixscale = 0.5 / float(cenchan)
    # print("pixscale: ", pixscale)
    # print("cenchan: ", cenchan)
    w = WCS(naxis=2)
    w.wcs.crpix = [4000, 4000]
    w.wcs.cdelt = np.array([-pixscale, pixscale])
    w.wcs.crval = [ra, dec]
    w.wcs.ctype = ["RA---SIN", "DEC--SIN"]
    w.wcs.cunit = ["deg", "deg"]
    w._naxis1 = 8000
    w._naxis2 = 8000

    return w


def casa_outlier_source(src: Source) -> str:
    """Generate a new entry in a casa tclean outlier file for a A-Team source

    Args:
        src (Source): The source to add to the outlier file

    Returns:
        str: An entry in the outlier file for tclean
    """
    line = (
        f"#outlier {src.name}\n"
        f"imagename=outlier{src.name}\n"
        f"imsize=[128,128] \n"
        f"phasecenter=J2000 {str(src.pos.ra.to_string(u.hour))} "
        f"{str(src.pos.dec.to_string(u.degree, alwayssign=True))} \n"
        "\n"
    )

    return line


def casa_clean_script(
    outliers: defaultdict,
    metafits: str,
    outpath: str = None,
    corrected_data: bool = False,
):
    """Creates a casa clean last file for execution

    Args:
        outliers (defaultdict): Set ot outlying sources that need to be removed
        metafits (str): the metafits file used throughout processing, expected to confirm to gleam-x typical usage
        outpath (str, optional): path to create the clean last file at. If None will write out 'clean.last' (defaults to None)
        ms_debug (bool, optional): whether imaging should be performed using CORRECTED_DATA column (default is False)
    """
    obsid = metafits.replace(".metafits", "")
    outpath = outpath if outpath is not None else "casa_script.casa"

    # TODO: Adjust the cell size depending on frequency

    with open(outpath, "w") as out:
        for c, (imagename, phasecenter, imsize) in enumerate(
            zip(outliers["imagename"], outliers["phasecenter"], outliers["imsize"])
        ):
            out.write(f"print('Running tclean on {imagename}') \n")
            datacolumn = "data" if c == 0 and corrected_data == False else "corrected"
            clean = (
                "tclean("
                f"vis='{obsid}.ms', imagename='{imagename}', "
                f"imsize={imsize}, phasecenter='{phasecenter}', "
                f"datacolumn='{datacolumn}', "
                "nterms=3, deconvolver='mtmfs',threshold='0.05Jy', "
                "stokes='XXYY',  "
                "niter=5000, gain=0.1,  wprojplanes=1024,"
                "cell='10arcsec', weighting='briggs', robust=0.0, savemodel='modelcolumn' "
                ")\n"
            )
            out.write(clean)
            # nterms=2, deconvolver='mtmfs',threshold='0.1Jy' ,

            out.write(f"print('Running uvsub on {imagename}') \n")
            uvsub = f"uvsub(vis='{obsid}.ms')\n"
            out.write(uvsub)

        if corrected_data is False:
            doc = "# Need to move corrected column back to data, and delete data. The uvsub will always created corrected_data. \n"
            out.write(doc)

            txt = (
                "print('Moving the CORRECTED_DATA column to the DATA column')\n"
                f"tb.open('{obsid}.ms', nomodify=False)\n"
                f"tb.removecols('DATA')\n"
                f"tb.renamecol('CORRECTED_DATA', 'DATA')\n"
                f"tb.flush()\n"
                f"tb.close()\n"
            )
            out.write(txt)


def casa_clean_source(
    src: Source, outliers: defaultdict, imsize=(128, 128)
) -> defaultdict:
    """Adds to the bookkeeping a new source that will be used to generate a clean.last file

    Args:
        src (Source): a source to add to the existing outlier record
        outliers (defaultdict): the record keeper contain sources to add to the clean.last file
        imsize (tuple, optional): The imagesize of each cutout. Defaults to (128,128).

    Returns:
        defaultdict: updated recorded with new source inserted
    """
    outliers["imagename"].append(f"outlier{src.name}")
    outliers["phasecenter"].append(
        f"J2000 {str(src.pos.ra.to_string(u.hour))} {str(src.pos.dec.to_string(u.degree, alwayssign=True))}"
    )
    outliers["imsize"].append(list(imsize))

    return outliers


@u.quantity_input(search_radius=u.arcminute, min_elevation=u.degree)
def ateam_model_creation(
    metafits_file,
    mode,
    ggsm=None,
    search_radius=10 * u.arcminute,
    min_flux=0.0,
    check_fov=False,
    model_output=None,
    sources=BRIGHT_SOURCES,
    pixel_border=0,
    min_response=None,
    max_response=None,
    min_elevation=None,
    apply_beam=False,
    corrected_data: bool = False,
):
    """Search around known A-Team sources for components in the GGSM, and create
    a corresponding model in Andre's formation for use in mwa_reduce tasks.

    Args:
        metafits_file (str): Path to a metafits file
        ggsm (str): Path to GLEAM global sky model
        search_radius (units, optional): Radius to use when search for nearby component. Defaults to 10.*u.arcminute
        min_flux (float, optional): Minimum flux in Jy to use to filter out faint objects. Defaults to 0.
        check_fov (bool, optional): Consider whether a A-Team source is within the GLEAM-X image before searching for components. Defaults to False.
        model_output (str, optional): Output path to write file to. If True ;skymodel' is appended to the metafits file. Defaults to None.
        sources (list[Source], optional): Colleciton of bright sources used that will be modelled and potentially included as components to subtract. Defaults to known bright sources.
        pixel_border(int, optional): A bright source has to be within this many pixels from the edge of an image to be includedin a model. Defaults to 0. 
        min_response (float, optional): Sources where the primary beam attentuation is more than this number are removed. 
        max_response (float, optional): Sources where the primary beam attentuation is less than this number are removed. 
        min_elevation (float, optional): Minimum elevation a source should have before being included in the model. If None the elevation is not considered. Defaults to None. 
        apply_beam (bool, optional): Apply primary beam attenuation to flux densities that get placed into the model. Defaults to False. 
        corrected_data (bool, optional): Whether to image the corrected data column when creating the casa outlier and subtraction imaging script. Defaults to False. 
    """
    if mode not in MODEL_MODES:
        raise ValueError(f"Expected mode with {MODEL_MODES}, received {mode}")

    if model_output == True:
        model_output = f"{metafits_file}.skymodel"

    time, delays, freq, grid = parse_metafits(metafits_file)

    header = fits.open(metafits_file)[0].header

    # Mid-point of the observation used for AltAz.
    gpstime = header["GPSTIME"]
    start_time = header["DATE-OBS"]
    duration = header["EXPOSURE"] * u.s
    obs_time = Time(start_time, format="isot", scale="utc") + 0.5 * duration

    cenchan = round(freq / 1e6 / 1.28 + 0.5)

    metafits_wcs = create_wcs(header["RA"], header["DEC"], cenchan)
    no_comps = 0

    if mode == "subtrmodel":
        model_text = "skymodel fileformat 1.1\n"

        assert ggsm is not None, "GGSM needs to be set for subtrmodel mode"
        ggsm_tab = Table.read(ggsm)
        ggsm_sky = SkyCoord(
            ggsm_tab["RAJ2000"], ggsm_tab["DEJ2000"], unit=(u.deg, u.deg)
        )
    elif mode == "casa":
        model_text = ""
    elif mode == "casaclean":
        model_dict = defaultdict(list)

    for src in sources:
        response = gleamx_beam_lookup(src.pos.ra.deg, src.pos.dec.deg, grid, time, freq)
        cal_flux = src.brightness(freq)
        app_flux = cal_flux * np.mean(response)

        in_fov = check_coords(metafits_wcs, src.pos)

        if app_flux < min_flux or (check_fov and in_fov):
            continue

        if max_response is not None and np.mean(response) > max_response:
            continue

        if min_response is not None and np.mean(response) < min_response:
            continue

        altaz = src.pos.transform_to(AltAz(obstime=obs_time, location=LOCATION))
        if min_elevation is not None and altaz.alt < min_elevation:
            continue

        # Decide if a potential source is within a certain border around the image
        # Only include it in the model to subtract if it is on the edge, otherwise
        # ignore and hope for the best
        if check_fov and check_coords_mask(
            metafits_wcs, src.pos, border_size=pixel_border
        ):
            continue

        if mode == "casa":
            model_text += casa_outlier_source(src)
            no_comps += 1
        elif mode == "casaclean":
            model_dict = casa_clean_source(src, model_dict)
            no_comps += 1
        elif mode == "count":
            no_comps += 1
        elif mode == "subtrmodel":
            matches = search_ggsm(src.pos, ggsm_sky, search_radius)
            comps = ggsm_tab[matches]
            no_comps += len(comps)

            print(f"{src.name} is going to the model...")
            if apply_beam:
                print("...Applying primary beam attenuation to the components")
                comps_response = gleamx_beam_lookup(
                    ggsm_sky[matches].ra.deg,
                    ggsm_sky[matches].dec.deg,
                    grid,
                    time,
                    freq,
                )
                comps["S_200"] = comps["S_200"] * np.mean(comps_response, axis=0)

            for comp in comps:
                comp_model = ggsm_row_model(comp)
                model_text += comp_model

    if mode == "count":
        return no_comps

    if model_output not in [None, False] and no_comps > 0:
        if mode == "casaclean":
            casa_clean_script(
                model_dict,
                metafits_file,
                outpath=model_output,
                corrected_data=corrected_data,
            )
        else:
            with open(model_output, "w") as out_file:
                print(f"Writing {no_comps} components to {model_output}")
                out_file.write(model_text)

    return None


def attach_units_or_None(param, to_unit) -> Tuple["u", None]:
    """Test is params is set, and if it is not None multiple the unit

    Args:
        param (Any): item to attach the unit to
        to_unit (u): Units to add
    
    Returns:
        Tuple[u, None]: If param is None returns None, others the value with the unit attached
    """
    return param * to_unit if param is not None else None


if __name__ == "__main__":

    try:
        GGSM = f"{os.environ['GXBASE']}/models/GGSM.fits"
    except:
        GGSM = ""

    parser = ArgumentParser(description="Simple test script to figure out peeling")
    parser.add_argument("metafits", nargs="+", help="metafits file of observation")

    parser.add_argument(
        "-m",
        "--min-flux",
        default=0,
        type=float,
        help="Minimum apparent brightness, in Jy, for a source to be considered as one to include in model. A crude stokes-I intensity is formed by taking the mean of the XX and YY responses to derived the apparent brightness. ",
    )
    parser.add_argument(
        "-c",
        "--check-fov",
        default=True,
        action="store_false",
        help="Check to only include sources if they are outside the image boundaries, assuming 8000x8000 pixels and pixel scale of 0.5 / central channel",
    )
    parser.add_argument(
        "--model-output",
        type=str,
        nargs=1,
        default=None,
        help="The path to save the model as.",
    )
    parser.add_argument(
        "--ggsm", default=GGSM, type=str, help="Path to the GLEAM Global Sky Model"
    )
    parser.add_argument(
        "--search-radius",
        default=10,
        type=float,
        help="The search radius, in arcminutes, used when searching the GGSM for components related to known bright A-team sources",
    )
    parser.add_argument(
        "--pixel-border",
        type=int,
        default=0,
        help="A masking border widt. If non-zero, sources will only be considered for subtraction if ther are fewer than this many pixels from the border. If zero this criteria is ignored. ",
    )
    parser.add_argument(
        "--min-response",
        type=float,
        default=None,
        help="Include sources in the model if they are at a position where their primary beam attentuation is above this threshold. In practise this would select objects towards the edge of an image away from the most sensitive part of the primary beam. ",
    )
    parser.add_argument(
        "--max-response",
        type=float,
        default=None,
        help="Include sources in the model if they are at a position where their primary beam attentuation is below this threshold. In practise this would select objects towards the edge of an image away from the most sensitive part of the primary beam. ",
    )
    parser.add_argument(
        "--min-elevation",
        default=None,
        type=float,
        help="Minimum elevation (degrees) a candidate source should hae before its components are added to the model. ",
    )
    parser.add_argument(
        "--apply-beam",
        default=False,
        action="store_true",
        help="Place the apparent brightness of each component into the model if subtrmodel is used, not the expected brightness that is described by the GGSM.",
    )

    parser.add_argument(
        "--mode",
        default=MODEL_MODES[0],
        choices=MODEL_MODES,
        help="The type of model file to create. subtrmodel for the AO style, or casa to create a outlier file for imaging. ",
    )
    parser.add_argument(
        "--corrected-data",
        default=False,
        action="store_true",
        help="In line with the GLEAM-X processing pipeline, if using the debug mode than the calibrated data are placed in the CORRECTED_DATA column, and these are the data that should be imaged initially. This is only relevant for the casa outlier subtraction mode. ",
    )
    args = parser.parse_args()

    args.search_radius = attach_units_or_None(args.search_radius, u.arcminute)
    args.min_elevation = attach_units_or_None(args.min_elevation, u.degree)
    args.model_output = args.model_output[0] if args.model_output is not None else None

    for metafits in args.metafits:
        result = ateam_model_creation(
            metafits,
            args.mode,
            ggsm=args.ggsm,
            search_radius=args.search_radius,
            min_flux=args.min_flux,
            check_fov=args.check_fov,
            model_output=args.model_output,
            pixel_border=args.pixel_border,
            max_response=args.max_response,
            min_response=args.min_response,
            min_elevation=args.min_elevation,
            apply_beam=args.apply_beam,
            corrected_data=args.corrected_data,
        )

        if result is not None:
            if args.mode == "count":
                print(f"{metafits} {result}")

