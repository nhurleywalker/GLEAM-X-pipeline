#!/usr/bin/env python

"""Script to help identify which calibrate solution files are not appropriate to apply, and helps to 
identify ones close in time that are appropriate. 
"""

import os
import sys
import numpy as np
from calplots.aocal import fromfile
from argparse import ArgumentParser

THRESHOLD = (
    0.25  # acceptable level of flagged solutions before the file is considered ratty
)


def check_solutions(aofile, threshold=THRESHOLD, *args, **kwargs):
    """Inspects the ao-calibrate solutions file to evaluate its reliability

    Args:
        aofile (str): aocal solutions file to inspect
    
    Keyword Args:
        threshold (float): The threshold, between 0 to 1, where too many solutions are flagged before the file becomes invalid (default: 0.25)

    Returns:
        bool: a valid of invalid aosolutions file
    """
    threshold = threshold / 100 if threshold > 1 else threshold
    if not os.path.exists(aofile):
        return False

    ao_results = fromfile(aofile)
    ao_flagged = np.sum(np.isnan(ao_results)) / np.prod(ao_results.shape)

    if ao_flagged > threshold:
        return False

    return True


def report(obsids, cobsids, file=None):
    """Report when an obsid has been associated with a new copied obsid solution file

    Args:
        obsid (iterable): Subject obsid with a missing solutions file
        cobsid (iterable): Obsid to copy solutions from
    
    Keyword Args:
        file (_io.TextIOWrapper): An open file handler to write to
    """
    for o, c in zip(obsids, cobsids):
        print(o, c, file=file)


def find_valid_solutions(
    obsids,
    dry_run=False,
    base_path=".",
    suffix="_local_gleam_model_solutions_initial_ref.bin",
    *args,
    **kwargs,
):
    """Scans across a set of obsids to ensure a `calibrate` solutions file is found. If a obsids does not have this file, cidentify one close in time. 

    Directory structure is assumed to follow basic GLEAM-X pipeline:
        {obsid}/{obsid}{suffix}
    
    Minimal options are provide to configure this. 

    Args:
        obsids (numpy.ndarray): Array of obsids
    
    Keyword Args:
        dry_run (bool): Just present actions, do not carry them out (default: False)
        base_path (str): Prefix of path to search for ao-solutions (default: '.')
        suffix (str): Suffix of the solution file, in GLEAM-X pipeline this is `{obsid}_{solution}` (default: '_local_gleam_model_solutions_initial_ref.bin')
    
    Returns:
        calids (numpy.ndarray): Parrallel array with calibration solution obsid corresponding to the obsids specified in `obsids`
    """
    obsids = obsids.astype(np.int)
    calids = obsids.copy()

    present = np.array(
        [
            check_solutions(f"{base_path}/{obsid}/{obsid}{suffix}", **kwargs)
            for obsid in obsids
        ]
    )

    if np.all(present == False):
        print("No potenial calibration scans. base_path needs to be set?")
        sys.exit(1)

    for pos in np.argwhere(~present):
        obsid = obsids[pos]
        cobsid = obsids[np.argmin(np.abs(obsids[present] - obsid))]
        calids[pos] = cobsid

    return calids


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Detects whether a calibration solution was successfully derived. Otherwise, will find an observation close in time and will copy solutions from that."
    )
    parser.add_argument(
        "-t",
        "--threshold",
        default=THRESHOLD,
        type=float,
        help=f"Threshold (between 0 to 1) of the acceptable number of NaN solutions before the entirety of solutions file considered void, defaults to {THRESHOLD}",
    )

    subparsers = parser.add_subparsers(dest="mode")

    check = subparsers.add_parser(
        "check", help="Check a ao-solutions file to see if it is valid"
    )
    check.add_argument(
        "aofile",
        type=str,
        nargs="+",
        help="Path to ao-solution file/s to check to see if it is valid",
    )

    assign = subparsers.add_parser(
        "assign",
        help="Assign a calibration ao-solutions file to a collection of obsids. Presents a report in stdout of obsid and corresponding calibration scan",
    )
    assign.add_argument(
        "obsids",
        type=str,
        help="Path to text file with obsids to consider. Text file is new line delimited",
    )
    assign.add_argument(
        "-n",
        "--no-report",
        action="store_true",
        default=False,
        help="Presents report of obsids and corresponding calibration obsid closest in time",
    )
    assign.add_argument(
        "-c",
        "--calids-out",
        default=None,
        type=str,
        help="Output text file to generate",
    )
    assign.add_argument(
        "-b",
        "--base-path",
        type=str,
        default=".",
        help="Prefix added to path while scanning for ao-solution files",
    )

    args = parser.parse_args()

    if args.mode == "check":
        print("Checking Mode")
        for f in args.aofile:
            if check_solutions(f, threshold=args.threshold):
                print(f"{f} passed")
            else:
                print(f"{f} failed")
    elif args.mode == "assign":
        print("Assigning calibration")

        obsids = np.loadtxt(args.obsids, dtype=np.int)
        calids = find_valid_solutions(
            obsids, threshold=args.threshold, base_path=args.base_path.rstrip("/")
        )

        if not args.no_report:
            report(obsids, calids)
        if args.calids_out is not None:
            with open(args.calids_out, "w") as outfile:
                report(obsids, calids, file=outfile)
    else:
        print("Invalid directive supplied. ")
        parser.print_help()

