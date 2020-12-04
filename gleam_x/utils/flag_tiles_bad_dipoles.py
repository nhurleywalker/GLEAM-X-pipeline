#!/usr/bin/env python

import os
import requests
import numpy as np
import astropy.units as u
from astropy.time import Time
from astropy.io import fits
from astropy.table import Table
from argparse import ArgumentParser
from casacore.tables import taql

BASEURL = "http://ws.mwatelescope.org/metadata"


def download(obsid, service="fits"):
    """Downloads a component from the MWA metadata service

    Args:
        obsid (int): Observation ID of interest
        service (str, optional): Metaservice to call upon. Defaults to "fits".

    Returns:
        requests.models.Response: The response from the URL call
    """
    url = f"{BASEURL}/{service}"

    response = requests.get(url, params={"obsid": obsid}, timeout=1.0)

    return response


def parse_service(obsid, service="fits", out_file=None):
    """Call and oarse the response of the metadata service appropriately. 

    Args:
        obsid (int): Observation ID of interest
        service (str, optional): Which aspect of the metadata service to poll. Defaults to "fits".
        out_file (str, optional): Name of the file to write the resonse to. Only relevant for when a metafits file has been pulled from the fits service. 
                                  A default file suffix of 'down.metafits' will be used if this is None when service is fits. Defaults to None.

    Returns:
        [astropy.table.Table,dict]: If service is fits, a table of the tile / input / antenna mappings is returned. Otherwise, a dict of the formated JSON content is returned
    """
    response = download(obsid, service=service)

    if service == "fits":
        out_file = f"{obsid}_down.metafite" if out_file is None else out_file
        with open(out_file, "wb") as outfile:
            for i in response:
                outfile.write(i)

        tab = Table.read(out_file)

        return tab
    else:
        json_res = response.json()

        return json_res


def dead_dipole_antenna_flag(obsid, meta_outfile=None, dead_tolerance=0, ms=None):
    """Attempt to identify and flag tiles (ANTENNA ins the measurement set) based on the number of dipoles that are flagged. 
    Since the `tileid` is not a one-to-one correspondence to the antenna number, there has to be some mapping. 

    TODO: I think the `con` service call is redundant and information can be pulled from the `obs` service

    Args:
        obsid (int): Observation ID of interest
        meta_outfile (str, optional): Path to save the metafits file to. If None, one is generated.. Defaults to None.
        dead_tolerance (int, optional): Number of dead dipoles before the tile is considered flagged. Defaults to 0.
        ms (str, optional): Path to the measurement set that shoule be flagged. Defaults to None.
    """

    tab = parse_service(obsid, service="fits", out_file=meta_outfile)
    obs = parse_service(obsid, service="obs")
    con = parse_service(obsid, service="con")

    tile_ids = []
    bad_dipoles = obs["rfstreams"]["0"]["bad_dipoles"]
    for k in bad_dipoles.keys():
        if sum(map(len, bad_dipoles[k])) > dead_tolerance:
            tile_ids.append(k)

    input_nums = [con[f"{tid}"]["inputnum"] for tid in tile_ids]
    antennas = [tab["Antenna"][i == tab["Input"]][0] for i in input_nums]

    print("Identified antennas to flag:")
    print("ID mappings")
    print("tile_id, input_num, antenna")
    for t, i, a in zip(tile_ids, input_nums, antennas):
        print(t, i, a)

    if ms is not None and os.path.exists(ms):
        before = taql("CALC sum([select nfalse(FLAG) from $ms])")

        print(f"Flagging {ms}")
        taql(
            f"UPDATE $ms SET FLAG=T where any(ANTENNA1==$antennas or ANTENNA2==$antennas)"
        )

        after = taql("CALC sum([select nfalse(FLAG) from $ms])")
        diff = before[0] - after[0]
        print(f"Number of antennas flagged: {len(antennas)}")
        print(f"Number of visibilities flagged: {diff}")

        if diff == 0:
            print(
                "No changes were made. Possible that all identified antennas were already flagged?"
            )


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Downloads information from the MWA metadata service to identify and flag tiles that contain some number of dead dipoles"
    )
    parser.add_argument("obsid", type=int, help="observation ID to download")
    parser.add_argument(
        "-o", "--output", default=None, type=str, help="Output path to download to"
    )
    parser.add_argument(
        "-d",
        "--dead-tolerance",
        default=0,
        type=int,
        help="Number of acceptable dead dipoles before the tile is flagged. This is summed across the X and Y. ",
    )
    parser.add_argument(
        "-m",
        "--measurement-set",
        default=None,
        type=str,
        help="The measurement set that corresponds to the supplied obsid. If one is provided then the antennas with more than 'dead-tolerance' dead dipoles will be flagged",
    )

    args = parser.parse_args()

    dead_dipole_antenna_flag(
        args.obsid,
        meta_outfile=args.output,
        dead_tolerance=args.dead_tolerance,
        ms=args.measurement_set,
    )

