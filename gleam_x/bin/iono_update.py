#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import numpy as np
import argparse
import gleam_x.db.mysql_db as mdb

__author__ = ["Natasha Hurley-Walker", "Tim Galvin"]
__date__ = "25/09/2018"


def update_ionosphere(obsid, med, peak, std, cur):

    # Need to convert from numpy types to native python types
    obsid = int(obsid) if not isinstance(obsid, int) else obsid
    med = float(med) if isinstance(med, np.floating) else med
    peak = float(peak) if isinstance(peak, np.floating) else peak
    std = float(std) if isinstance(std, np.floating) else std

    cur.execute("SELECT count(*) FROM observation WHERE obs_id =%s", (obsid,))
    if cur.fetchone()[0] > 0:
        print(
            "Updating observation {0} with median = {1}, peak = {2}, std = {3}".format(
                obsid, med, peak, std
            )
        )
        cur.execute(
            "UPDATE observation SET ion_phs_med = %s, ion_phs_peak = %s, ion_phs_std = %s WHERE obs_id =%s",
            (med, peak, std, obsid),
        )
    else:
        print("observation not in database: ", obsid)
        return


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="add observations to database")
    parser.add_argument(
        "--ionocsv", type=str, help="ionospheric triage output csv file", default=None
    )

    args = parser.parse_args()

    if os.path.exists(args.ionocsv):
        filename, file_extension = os.path.splitext(args.ionocsv)
        if file_extension == ".csv":
            arr = np.loadtxt(open(args.ionocsv, "rb"), delimiter=",", skiprows=1)
            obsid = arr[0]
            med = arr[1]
            peak = arr[2]
            std = arr[3]
        else:
            print("Other file formats not yet enabled.")
            sys.exit(1)

    conn = mdb.connect()
    cur = conn.cursor()
    update_ionosphere(obsid, med, peak, std, cur)
    conn.commit()
    conn.close()
