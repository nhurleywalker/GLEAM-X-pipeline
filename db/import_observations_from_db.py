import urllib
import urllib2
import json
import sys
import os
import numpy as np
import argparse
import sqlite3
import mysql_db as mdb

__author__ = "PaulHancock & Natasha Hurley-Walker"

# Append the service name to this base URL, eg 'con', 'obs', etc.
BASEURL = 'http://ws.mwatelescope.org/metadata/'

dbconn = mdb.connect()

# Function to call a JSON web service and return a dictionary: This function by Andrew Williams
def getmeta(service='obs', params=None):
    """
    Given a JSON web service ('obs', find, or 'con') and a set of parameters as
    a Python dictionary, return a Python dictionary containing the result.
    """
    if params:
        data = urllib.urlencode(params)  # Turn the dictionary into a string with encoded 'name=value' pairs
    else:
        data = ''
    # Validate the service name
    if service.strip().lower() in ['obs', 'find', 'con']:
        service = service.strip().lower()
    else:
        print "invalid service name: %s" % service
        return
    # Get the data
    try:
        print BASEURL + service + '?' + data
        result = json.load(urllib2.urlopen(BASEURL + service + '?' + data))
    except urllib2.HTTPError as error:
        print "HTTP error from server: code=%d, response:\n %s" % (error.code, error.read())
        return
    except urllib2.URLError as error:
        print "URL or network error: %s" % error.reason
        return
    # Return the result dictionary
    return result


def copy_obs_info(obsid, cur):
    cur.execute("SELECT count(*) FROM observation WHERE obs_id = %s",(obsid,))
    if cur.fetchone()[0] > 0:
        print "already imported", obsid
        return
    meta = getmeta(service='obs', params={'obs_id':obsid})
    if meta is None:
        print obsid, "has no metadata!"
        return
    metadata = meta['metadata']
    
    cur.execute("""
    INSERT INTO observation
    (obs_id, projectid,  lst_deg, starttime, duration_sec, obsname, creator,
    azimuth_pointing, elevation_pointing, ra_pointing, dec_pointing,
    cenchan, freq_res, int_time, delays,
    calibration, cal_obs_id, calibrators,
    peelsrcs, flags, selfcal, ion_phs_med, ion_phs_peak, ion_phs_std,
    nfiles, archived
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
    """, (
    obsid, meta['projectid'], metadata['local_sidereal_time_deg'], meta['starttime'], meta['stoptime']-meta['starttime'], meta['obsname'], meta['creator'],
    metadata['azimuth_pointing'], metadata['elevation_pointing'], metadata['ra_pointing'], metadata['dec_pointing'],
    meta["rfstreams"]["0"]['frequencies'][12], meta['freq_res'], meta['int_time'], json.dumps(meta["rfstreams"]["0"]["xdelays"]),
    metadata['calibration'], None, metadata['calibrators'],
    None, None, None, None, None, None,
    len(meta['files']), False))
    #update_observation(obsid, meta['obsname'], cur)
    return


if __name__ == "__main__":

    ps = argparse.ArgumentParser(description='add observations to database')
    ps.add_argument('--obsids', type=str, help='List of obsids to import; format of file ("txt": single-column text file of obsids; "csv": (optionally multi-column) comma-separated file with a header starting with # and a column labelled obsid; "meta": download from the online MWA metadatabase.', default=None)

    args = ps.parse_args()

    if os.path.exists(args.obsids):
        filename, file_extension = os.path.splitext(args.obsids)
        if file_extension == ".txt":
            ids = np.loadtxt(args.obsids, comments="#", dtype=int, ndmin=1)
        else:
            print "Other file formats not yet enabled."
            sys.exit(1)


    cur = dbconn.cursor()
    print len(ids)
    for obs_id in ids:
        copy_obs_info(obs_id,cur)

    dbconn.commit()
    dbconn.close()
