from __future__ import print_function

import requests
import json
import time
import sys
import os
import time
import numpy as np
import argparse
import mysql_db as mdb

__author__ = ["PaulHancock",
              "Natasha Hurley-Walker", 
              "Tim Galvin"]

# Append the service name to this base URL, eg 'con', 'obs', etc.
BASEURL = 'http://ws.mwatelescope.org/metadata'

dbconn = mdb.connect()

# Function to call a JSON web service and return a dictionary: This function by Andrew Williams
# Function to call a JSON web service and return a dictionary: This function by Andrew Williams
def getmeta(service='obs', params=None, level=0):
    
    # Validate the service name
    if service.strip().lower() in ['obs', 'find', 'con']:
        service = service.strip().lower()
    else:
        print("invalid service name: {0}".format(service))
        return
    
    service_url = "{0}/{1}".format(BASEURL, service)
    try:
        response = requests.get(service_url, params=params, timeout=1.)
        response.raise_for_status()

    except requests.HTTPError as error:
        if level <= 2:
            print("HTTP encountered. Retrying...")
            time.sleep(3)
            getmeta(service=service, params=params, level=level+1)
        else:
            raise error
    
    return response.json()


def copy_obs_info(obsid, cur):
    cur.execute("SELECT count(*) FROM observation WHERE obs_id = %s",(obsid,))
    if cur.fetchone()[0] > 0:
        print("\tObsid `{0}` is already imported.".format(obsid))
        return
    meta = getmeta(service='obs', params={'obs_id':obsid})
    if meta is None:
        print("\t{0} has no metadata!".format(obsid))
        return
    metadata = meta['metadata']
    
    cur.execute("""
    INSERT INTO observation
    (obs_id, projectid,  lst_deg, starttime, duration_sec, obsname, creator,
    azimuth_pointing, elevation_pointing, ra_pointing, dec_pointing,
    cenchan, freq_res, int_time, delays,
    calibration, cal_obs_id, calibrators,
    peelsrcs, flags, selfcal, ion_phs_med, ion_phs_peak, ion_phs_std,
    nfiles, archived, status
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
    """, (
    obsid, meta['projectid'], metadata['local_sidereal_time_deg'], meta['starttime'], meta['stoptime']-meta['starttime'], meta['obsname'], meta['creator'],
    metadata['azimuth_pointing'], metadata['elevation_pointing'], metadata['ra_pointing'], metadata['dec_pointing'],
    meta["rfstreams"]["0"]['frequencies'][12], meta['freq_res'], meta['int_time'], json.dumps(meta["rfstreams"]["0"]["xdelays"]),
    metadata['calibration'], None, metadata['calibrators'],
    None, None, None, None, None, None,
    len(meta['files']), False, 'unprocessed'))
    #update_observation(obsid, meta['obsname'], cur)
    return


def check_obsids(cur):
    """Return a list of all obsids currently saved in the database
    """
    cur.execute("""
                SELECT obs_id FROM observation
                """)
    return [o[0] for o in cur.fetchall()]

if __name__ == "__main__":

    ps = argparse.ArgumentParser(description='add observations to database')
    ps.add_argument('--obsids', type=str, help='List of obsids to import; format of file ("txt": single-column text file of obsids; "csv": (optionally multi-column) comma-separated file with a header starting with # and a column labelled obsid; "meta": download from the online MWA metadatabase.', default=None)
    ps.add_argument('-s', '--skip-existing', action='store_true', default=False, help='pull down a list of obsids initially and remove already known ids before attempting to download meta-data')

    args = ps.parse_args()

    if os.path.exists(args.obsids):
        filename, file_extension = os.path.splitext(args.obsids)
        if file_extension == ".txt":
            ids = np.loadtxt(args.obsids, comments="#", dtype=int, ndmin=1)
        else:
            print("Other file formats not yet enabled.")
            sys.exit(1)

    cur = dbconn.cursor()
    
    # Skip the existing obs_ids that are in the observation table
    if args.skip_existing:
        existing_obs = check_obsids(cur)
        ids = list( set(ids) - set(existing_obs) )

    print('\n{0} obs_ids to download... '.format(len(ids)))
    for count, obs_id in enumerate(ids):
        # A numpy int64 is not the same as a python int, and 
        # mysql connector gets a little upset. 
        print('{0}) {1}'.format(count, obs_id))
        copy_obs_info(int(obs_id),cur)
        dbconn.commit()

    dbconn.commit()
    dbconn.close()
