import urllib
import urllib2
import json
import sys
import os
import numpy as np
import argparse
import sqlite3

__author__ = "PaulHancock & Natasha Hurley-Walker"

# Append the service name to this base URL, eg 'con', 'obs', etc.
BASEURL = 'http://ws.mwatelescope.org/metadata/'
dbfile = '/group/mwasci/nhurleywalker/GLEAM-X-pipeline/db/GLEAM-X.sqlite'

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


#def update_observation(obsid, obsname, cur):
#    if 'CORR_MODE' in obsname:
#        return
#    elif 'FDS' in obsname:
#        # eg FDS_DEC-55.0_93
#        idx = obsname[3:-4]
#    elif 'GCN' in obsname:
#        idx = obsname[3:]
#    else:
#        idx = obsname
#    cur.execute("SELECT count(name) FROM grb WHERE fermi_trigger_id = ?", (idx,))
#    if cur.fetchone()[0] > 0:
#        cur.execute("SELECT name FROM grb WHERE fermi_trigger_id = ?", (idx,))
#        grb = cur.fetchone()[0]
#        cur.execute("UPDATE observation SET grb = ? WHERE obs_id =?", (grb, obsid))
#    return


def copy_obs_info(obsid, cur):
    cur.execute("SELECT count(*) FROM observation WHERE obs_id =?",(obsid,))
    if cur.fetchone()[0] > 0:
        print "already imported", obsid
        return
    meta = getmeta(service='obs', params={'obs_id':obsid})
    if meta is None:
        print obsid, "has no metadata!"
        return
    metadata = meta['metadata']
    
    cur.execute("""
    INSERT OR REPLACE INTO observation
    (obs_id, projectid,  lst_deg, starttime, duration_sec, obsname, creator,
    azimuth_pointing, elevation_pointing, ra_pointing, dec_pointing,
    cenchan, freq_res, int_time, delays,
    calibration, cal_obs_id, calibrators,
    peelsrcs, flags, selfcal, ion_phs_med, ion_phs_peak, ion_phs_std,
    nfiles, archived
    )
    VALUES (?,?,?,?,?,?,?,  ?,?,?,?,  ?,?,?,?,   ?,?,?,  ?,?,?,?,?,?,  ?,?);
    """, (
    obsid, meta['projectid'], metadata['local_sidereal_time_deg'], meta['starttime'], meta['stoptime']-meta['starttime'], meta['obsname'], meta['creator'],
    metadata['azimuth_pointing'], metadata['elevation_pointing'], metadata['ra_pointing'], metadata['dec_pointing'],
    meta["rfstreams"]["0"]['frequencies'][12], meta['freq_res'], meta['int_time'], json.dumps(meta["rfstreams"]["0"]["xdelays"]),
    metadata['calibration'], None, metadata['calibrators'],
    None, None, None, None, None, None,
    len(meta['files']), False))
    #update_observation(obsid, meta['obsname'], cur)
    return

#def update_grb_links(cur):
#    # associate each observation with the corresponding grb
#    cur.execute("SELECT obs_id, obsname FROM observation WHERE grb IS NULL")
#    # need to do this to exhaust the generator so we can reuse the cursor
#    obsids, obsnames = zip(*cur.fetchall())
#    for obsid, obsname in zip(obsids, obsnames):
#        update_observation(obsid, obsname, cur)
#
#    # now associate each calibration observation with a grb
#    # this relies on the calibration observation being within 150sec of the regular obs
#    cur.execute("""
#    SELECT o.obs_id, b.grb
#    FROM observation o JOIN observation b ON
#    o.obs_id - b.obs_id BETWEEN -150 AND 150
#    AND o.calibration AND b.grb IS NOT NULL
#    AND o.obs_id != b.obs_id
#    """)
#    ids, grbs = zip(*cur.fetchall())
#    for idx, grb in zip(ids, grbs):
#        cur.execute("UPDATE observation SET grb=? WHERE obs_id=?", (grb, idx))
#    return


if __name__ == "__main__":

    ps = argparse.ArgumentParser(description='add observations to database')
    ps.add_argument('--obsids', type=str, help='List of obsids to import; format of file ("txt": single-column text file of obsids; "csv": (optionally multi-column) comma-separated file with a header starting with # and a column labelled obsid; "meta": download from the online MWA metadatabase.', default=None)

    args = ps.parse_args()

    if os.path.exists(args.obsids):
        filename, file_extension = os.path.splitext(args.obsids)
        if file_extension == ".txt":
            ids = np.loadtxt(args.obsids, comments="#", dtype=int)
# Makes it work for single-line files
#            if len(ids.shape)==1:
#               ids = [ids]
        else:
            print "Other file formats not yet enabled."
            sys.exit(1)
#        elif file_extension == ".csv":
#        elif file_extension == ".xml":

    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    print len(ids)
    if len(ids) > 0:
        for obs_id in ids:
            print obs_id
            copy_obs_info(obs_id,cur)
            conn.commit()
        sys.exit()
    #obsdata = getmeta(service='find', params={'projectid':'D0009', 'limit':100000}) #'limit':10
#    obsdata = getmeta(service='find', params={'projectid':'G0008', 'mintime':'1201549600', 'maxtime': '1201550200', 'limit':10}) #'limit':10
    # For Jai's project - MAXI J1535 - XRB
    #obsdata = getmeta(service='find', params={'obsname':'J1535_%', 'limit':100000}) #'limit':10
#    for obs in obsdata:
#        obs_id = obs[0]
#        copy_obs_info(obs_id, cur)
#        conn.commit()
#    update_grb_links(cur)
    conn.commit()
    conn.close()
