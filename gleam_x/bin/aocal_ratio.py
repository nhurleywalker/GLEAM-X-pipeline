#!/usr/bin/env python
import os, logging
from argparse import ArgumentParser
from calplots.aocal import fromfile
import numpy as np


def aocal_ratio(sol_numerator, sol_denominator, outpath):
    """Take the ratio of two sets of gains that are stored in the 
    mwareduce solution file format. The result is placed in a new
    file compatible with applysolutions. 

    Args:
        sol_numerator (str): Path to the gains that will act as the numerator
        sol_denominator (str): Path to the gains that will as the denominator
        outpath (str): The output path of the new solution file to create
    """
    ao_num = fromfile(sol_numerator)
    ao_den = fromfile(sol_denominator)

    ao_ratio = ao_num / ao_den

    mask = np.isfinite(ao_ratio)
    ao_ratio[~mask] = np.nan

    ao_ratio.tofile(outpath)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Create a new solutions file that is the ratio of two input ao-solution files. "
    )
    parser.add_argument("sol1", type=str, help="The numerator when taking the ratio")
    parser.add_argument("sol2", type=str, help="The denominator when taking the ratio")
    parser.add_argument(
        "outpath", type=str, help="The output path of the new solutions file to create"
    )

    args = parser.parse_args()

    aocal_ratio(args.sol1, args.sol2, args.outpath)

