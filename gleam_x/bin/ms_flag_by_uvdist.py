#! /usr/bin/env python

# Code taken with permission from Stefan Duchesna
#   - gitlab.com/Sunmish/piip

# Contributions by Tim Galvin:
#  - idea for taql updating
#  - taql number of visibilities flagged
#  - suppress numpy warnings

from __future__ import print_function, division

import numpy as np
import sys
import warnings

from datetime import datetime
from casacore.tables import table, taql, maketabdesc, makescacoldesc

from argparse import ArgumentParser


CASA_DATA_COLUMNS = {"DATA": "data", "CORRECTED_DATA": "corrected"}


class MeasurementSet:
    """Easier handling of a Measurement Set."""

    def __init__(self, ms, data_column):
        self.mset = table(ms, readonly=True, ack=False)
        self.name = ms
        mset = self.mset
        self.filtered = taql(
            "select * from $ms where not FLAG_ROW and ANTENNA1 <> ANTENNA2"
        )
        self.len = len(self.filtered)
        self.data_column = data_column

    def baseline_preparation(self):

        mset = self.filtered

        antenna_table = table(self.name + "/ANTENNA", readonly=True, ack=False)
        self.antennas = list(set(mset.getcol("ANTENNA1")))
        self.nbaselines = int(len(self.antennas) * (len(self.antennas) - 1) / 2)
        self.baselines = []
        self.station_names = {}
        self.baseline_stats = np.full((self.nbaselines, 5), 1.0, dtype=np.float32)
        i = 0
        for ant1 in self.antennas:
            for ant2 in self.antennas:
                baseline = set([ant1, ant2])
                if ant1 != ant2 and baseline not in self.baselines:

                    self.baselines.append(baseline)
                    self.baseline_stats[i, 0] = ant1
                    self.baseline_stats[i, 1] = ant2

                    # get baseline length:
                    ant1_pos = antenna_table.getcol("POSITION", startrow=ant1, nrow=1)[
                        0
                    ]
                    ant2_pos = antenna_table.getcol("POSITION", startrow=ant2, nrow=1)[
                        0
                    ]

                    self.baseline_stats[i, 2] = cartesian_dist3d(ant1_pos, ant2_pos)

                    i += 1

        # Get station names as well:
        station_names = antenna_table.getcol("NAME")
        for i in range(len(station_names)):
            self.station_names[i] = station_names[i]

        self.baseline_stats = self.baseline_stats[self.baseline_stats[:, 2].argsort()]

    @staticmethod
    def get_data(mset):

        flags = mset.filtered.getcol("FLAG")
        data = mset.filtered.getcol(mset.data_column)
        data[flags] = np.nan

        return data

    @staticmethod
    def flag_baselines(ms, baselines):
        """example taql expressions:
        SELECT FROM some.ms WHERE any(ANTENNA1==[0,0,1] && ANTENNA2==[1,3,2])
        update MY.MS set FLAG_ROW=T where isdefined(FLAG) && all(FLAG)
        """

        ant1, ant2 = zip(*baselines)
        unflag1 = taql("CALC sum([select nfalse(FLAG) from $ms])")

        print("Flagging {} baselines.".format(len(ant1)))
        taql("update $ms set FLAG_ROW=T where any(ANTENNA1==$ant1 && ANTENNA2==$ant2)")
        taql("update $ms set FLAG=T where any(ANTENNA1==$ant1 && ANTENNA2==$ant2)")

        unflag2 = taql("CALC sum([select nfalse(FLAG) from $ms])")
        print("Number of visibilities flagged: {}".format(unflag1[0] - unflag2[0]))


def cartesian_dist3d(c1, c2):
    """3-D Cartesian distance between vectors ``c1`` and ``c2``."""
    return np.sqrt((c2[0] - c1[0]) ** 2 + (c2[1] - c1[1]) ** 2 + (c2[2] - c1[2]) ** 2)


def chan_avg(mset, data_column="CORRECTED_DATA", stride=1000):
    """
    """

    data = MeasurementSet.get_data(mset)
    data_avg_amp = np.full((mset.filtered.nrows(), 4), np.nan, dtype=np.complex_)

    # Hides empty slice warnings when channel already completely flagged
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        # read in data in chunks to help with memory (for my laptop mostly):
        for i in range(0, mset.filtered.nrows(), stride):
            if i + stride > mset.filtered.nrows():
                end = mset.filtered.nrows()
            else:
                end = i + stride
            # mean visibility across channels for each row/pol:
            data_avg_amp[i:end, :] = np.nanmean(data[i:end, :, :], axis=1)

    return data_avg_amp


def get_baseline_stats(
    mset, data_avg_amp, window=5000, sigma=3, return_baselines=False
):
    """
    """

    mset.baseline_preparation()

    ant1 = mset.filtered.getcol("ANTENNA1")
    ant2 = mset.filtered.getcol("ANTENNA2")

    baseline_avg = np.full((len(mset.baseline_stats), 4), np.nan, dtype=np.float32)
    baseline_std = np.full((len(mset.baseline_stats), 4), np.nan, dtype=np.float32)

    for i in range(len(mset.baseline_stats)):

        a1 = mset.baseline_stats[i, 0]
        a2 = mset.baseline_stats[i, 1]

        d = data_avg_amp[(ant1 == int(a1)) & (ant2 == int(a2))]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)

            # abs for the complex vis? np.std does this as well internally
            avg = np.nanmean(np.abs(d), axis=0)
            std = np.nanstd(d, axis=0)

        baseline_avg[i, :] = avg
        baseline_std[i, :] = std

    count = 0
    flag_string = ""
    baselines = []
    for i in range(len(mset.baseline_stats)):

        dist = mset.baseline_stats[i, 2]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)

            window_selection = (mset.baseline_stats[:, 2] < dist + window) & (
                mset.baseline_stats[:, 2] > dist - window
            )

            window_std = np.nanstd(baseline_avg[window_selection], axis=0)
            window_avg = np.nanmean(baseline_avg[window_selection], axis=0)

            if (np.abs(baseline_avg[i] - window_avg) > sigma * window_std).any():
                # output suitable to pass to CASA's flagdata:
                flag_string += ";{}&{}".format(
                    mset.station_names[int(mset.baseline_stats[i, 0])],
                    mset.station_names[int(mset.baseline_stats[i, 1])],
                )

                baselines.append(
                    (int(mset.baseline_stats[i, 0]), int(mset.baseline_stats[i, 1]))
                )

                count += 1

    if not return_baselines:
        flag_string = flag_string.lstrip(";")
        print(flag_string)
    else:
        return baselines


def main():
    """
    """

    ps = ArgumentParser(
        description="Find baselines to flag - can be memory intensive so may not work on large MeasurementSets."
    )
    ps.add_argument("ms", type=str, help="name of MeasurementSet")
    ps.add_argument(
        "column", type=str, help="name of column in MeasurementSet to search on."
    )
    ps.add_argument(
        "-s",
        "--sigma",
        type=float,
        default=3,
        help="baselines with amplitudes about sigma times the standard deviation in a sliding window that we will be reported for flagging.",
    )
    ps.add_argument(
        "-w",
        "--window",
        type=float,
        default=5000,
        help="sliding window used for searching, in number of baselines",
    )  # fullish range
    ps.add_argument(
        "-a",
        "--apply",
        action="store_true",
        help="Flag baselines if >1 baselines are selected. If not selected then a list of CASA-compatible baslines will be printed that can be fed to CASA's flagdata.",
    )

    args = ps.parse_args()

    mset = MeasurementSet(args.ms, args.column)
    d = chan_avg(mset, args.column, stride=50000)
    if args.apply:
        baselines = get_baseline_stats(
            mset, d, window=args.window, sigma=args.sigma, return_baselines=True
        )
        if len(baselines) > 0:
            MeasurementSet.flag_baselines(args.ms, baselines)
        else:
            print("No baselines to flag.")
    else:
        get_baseline_stats(mset, d, window=args.window, sigma=args.sigma)


if __name__ == "__main__":
    main()
