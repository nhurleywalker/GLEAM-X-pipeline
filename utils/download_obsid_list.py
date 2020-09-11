from __future__ import print_function

import pandas as pd
import numpy as np
import astropy.units as u
from argparse import ArgumentParser
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation

import mysql_db as mdb

MWA = EarthLocation.from_geodetic(lat=-26.703319*u.deg, lon=116.67081*u.deg, height=377*u.m)

def get_observations(fds_only=True, 
                     start_obsid=None,
                     finish_obsid=None,
                     obs_date=None):

    df = pd.read_sql_table('observation',
                          mdb.dbc.dfconn)

    if fds_only:
        df = df[df['obsname'].str.contains('FDS')]
    
    if start_obsid is not None:
        df = df[df['obs_id'] >= int(start_obsid)]

    if finish_obsid is not None:
        df = df[df['obs_id'] <= int(finish_obsid)]

    if obs_date is not None:
        gps = Time(df['obs_id'], format='gps', location=MWA)
        gps_date = gps.strftime('%Y-%m-%d')

        df = df[gps_date == obs_date]

    return df


def create_obsids_txt(df, out):
    df['obs_id'].to_csv(out, index=False)


if __name__ == '__main__':
    parser = ArgumentParser(description='Pulls down a list of `obs_ids` provide a set of specifications')
    parser.add_argument('-a','--all-obs', default=False, action='store_true', help='Include calibration scans as well as the FDS observations')
    parser.add_argument('-s','--start-obsid', default=None, type=int, help='First `obs_id` in a range of obsids')
    parser.add_argument('-f','--finish-obsid', default=None, type=int, help='Last `obs_id` in a range of obsids')
    parser.add_argument('-d','--date', default=None, help='Obsids on this date are returned. Date is expected in YYY-MM-DD format')
    parser.add_argument('-o', '--out', default=None, help='Output path of a line delimited set of obsids. Only supports text output file and ignores file extension. ')

    args = parser.parse_args()

    print(args)

    df = get_observations(
            fds_only=not args.all_obs, 
            start_obsid=args.start_obsid,
            finish_obsid=args.finish_obsid,
            obs_date=args.date 
        )

    print(df.shape)

    if args.out is not None:
        create_obsids_txt(df, args.out)