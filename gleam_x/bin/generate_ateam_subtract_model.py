import os
import numpy as np
import astropy.units as u

from argparse import ArgumentParser
from astropy.wcs import WCS
from astropy.io import fits
from astropy.coordinates import SkyCoord
from astropy.table import Table
from mwa_pb_lookup.lookup_beam import beam_lookup_1d as gleamx_beam_lookup
from gleam_x.bin.beam_value_at_radec import parse_metafits, beam_value
from gleam_x.db.check_src_fov import check_coords


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


@u.quantity_input(search_radius=u.arcminute)
def ateam_model_creation(
    metafits_file,
    ggsm,
    search_radius=10 * u.arcminute,
    min_flux=0.0,
    check_fov=False,
    model_output=None,
    drift_output=None,
):
    """Search around known A-Team sources for components in the GGSM, and create
    a corresponding model in Andre's formation for use in mwa_reduce tasks.

    Args:
        metafits_file (str): Path to a metafits file
        ggsm (str): Path to GLEAM global sky model
        search_radius (units, optional): Radius to use when search for nearby component. Defaults to 10.*u.arcminute
        min_flux (float, optional): Minimum flux in Jy to use to filter out faint objects. Defaults to 0.
        check_fov (bool, optional): Consider whether a A-Team source is within the GLEAM-X image before searching for components. Defaults to False.
        model_output (str, optional): Output path to write file to. Defaults to None.
        drift_output (str, optional): Output path to write a csv-like file describing the A-Team sources that were used for searching. Defaults to None.
    """
    casa = Source("CasA", SkyCoord("23h23m24.000s   +58d48m54.00s"), 13000.0, -0.5, 0.0)
    cyga = Source(
        "CygA", SkyCoord("19h59m28.35663s +40d44m02.0970s"), 9000.0, -1.0, 0.0
    )
    crab = Source("Crab", SkyCoord("05h34m31.94s    +22d00m52.2s"), 1500.0, -0.5, 0.0)
    vira = Source(
        "VirA", SkyCoord("12h30m49.42338s +12d23m28.0439s"), 1200.0, -1.0, 0.0
    )
    pica = Source("PicA", SkyCoord("05h19m49.7229s  -45d46m43.853s"), 570.0, -1.0, 0.0)
    hera = Source("HerA", SkyCoord("16h51m11.4s     +04d59m20s"), 520.0, -1.1, 0.0)
    hyda = Source("HydA", SkyCoord("09h18m05.651s   -12d05m43.99s"), 350.0, -0.9, 0.0)

    sources = [casa, cyga, crab, vira, pica, hera, hyda]

    if model_output == True:
        model_output = f"{metafits_file}.skymodel"

    time, delays, freq, grid = parse_metafits(metafits_file)

    header = fits.open(metafits_file)[0].header

    gpstime = header["GPSTIME"]
    cenchan = round(freq / 1e6 / 1.28 + 0.5)

    metafits_wcs = create_wcs(header["RA"], header["DEC"], cenchan)

    ggsm_tab = Table.read(ggsm)
    ggsm_sky = SkyCoord(ggsm_tab["RAJ2000"], ggsm_tab["DEJ2000"], unit=(u.deg, u.deg))

    model_text = "skymodel fileformat 1.1\n"

    for src in sources:
        response = gleamx_beam_lookup(src.pos.ra.deg, src.pos.dec.deg, grid, time, freq)
        cal_flux = src.brightness(freq)
        app_flux = cal_flux * np.mean(response)

        in_fov = check_coords(metafits_wcs, src.pos)

        if app_flux < min_flux or (check_fov and in_fov):
            continue

        if drift_output is not None:
            with open(drift_output, "a") as drift_file:
                drift_file.write(
                    f"{gpstime},{src.name},{app_flux}, {response[0]}, {response[1]}\n"
                )

        matches = search_ggsm(src.pos, ggsm_sky, search_radius)
        comps = ggsm[matches]

        for comp in comps:
            comp_model = ggsm_row_model(comp)
            model_text += comp_model

    if model_output not in [None, False]:
        with open(model_output, "w") as out_file:
            print(f"Writing to {model_output}")
            out_file.write(model_text)


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
        default=1.0,
        type=float,
        help="Minimum brightness, in Jy, for a source to be considered as one to peel",
    )
    parser.add_argument(
        "-c",
        "--check-fov",
        default=True,
        action="store_false",
        help="Check to only include sources if they are outside the image boundaries, assuming 8000x8000 pixels and pixel scale of 0.5 / central channel",
    )
    parser.add_argument(
        "--store-model",
        default=False,
        action="store_true",
        help="Store the peel sky-model as METAFITS.peel",
    )
    parser.add_argument(
        "--drift-output",
        nargs=1,
        default=None,
        help="Create a file of all sources across all METAFITS with the brightness of A-Team sources that are above --min-flux",
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

    args = parser.parse_args()

    args.search_radius *= u.arcminute
    print(args)

    drift_output = None if args.drift_output is None else args.drift_output[0]

    if drift_output is not None:
        with open(drift_output, "w") as drift_file:
            drift_file.write("time,name,app_flux,response_xx,response_yy\n")

    for metafits in args.metafits:
        print(f"{metafits}...")
        ateam_model_creation(
            metafits,
            args.ggsm,
            search_radius=args.search_radius,
            min_flux=args.min_flux,
            check_fov=args.check_fov,
            model_output=args.store_model,
            drift_output=drift_output,
        )

