import sys
from astropy.coordinates import SkyCoord
from astropy import wcs
from astropy.io import fits
from astropy.time import Time
import astropy.units as u
import json
import mysql_db as mdb
import numpy as np
from populate_sources_table import Source
from check_src_fov import check_coords
from beam_value_at_radec import beam_value

__author__ = ["Natasha Hurley-Walker",
              "Tim Galvin"]

def insert_app(obs_id, source, appflux, infov, cur):
    """Saves the apparent flux of known sources based on the observation pointing
    direction and the mwa primary beam.

    Arguments:
        obs_id {int} -- GLEAM-X observation id
        source {str} -- Name of source to insert
        appflux {float} -- Brightness of source after applying MWA primary beam
        infov {bool} -- Is source within the field of view
        cur {mysql.connector.cursor.MySQLCursor} -- Open cursor to GLEAM-X database
    """
    cur.execute("""REPLACE INTO calapparent
                (obs_id, source, appflux, infov)
                VALUES (%s, %s, %s, %s); """,
                (obs_id, source, appflux, infov))
    return

def get_srcs(cur):
    """Returns the spectral properties described in the `sources` table.

    Arguments:
        cur {mysql.connector.cursor.MySQLCursor} -- Open cursor to GLEAM-X database
 
    Returns:
        {List} -- Result set of the executed SQL
    """
    srciter = cur.execute("""
    SELECT source, RAJ2000, DecJ2000, flux, alpha, beta
    FROM sources""")
    return cur.fetchall()

def get_obs(cur, obs_id = None):
    """
    Return a set of rows from the `observations` table. 

    Arguments:
        cur {mysql.connector.cursor.MySQLCursor} -- Open cursor to GLEAM-X database

    Keyword Arguments:
        obs_id {int} -- Limit the returned results to a single `obsid` (default: {None})
    """
    if obs_id is None:
        cur.execute("""SELECT obs_id, ra_pointing, dec_pointing, cenchan, starttime, delays
        FROM observation """)
        
    else:
        cur.execute(("SELECT obs_id, ra_pointing, dec_pointing, cenchan, starttime, delays "
                     "FROM observation WHERE obs_id = %s "), 
                     (obs_id, ))

        
    return cur.fetchall()

def create_wcs(ra, dec, cenchan):
    """Creates a fake WCS header to generate a MWA primary beam response

    Arguments:
        ra {float} -- Observation pointing direction in degrees
        dec {float} -- Observation pointing direction in degrees
        cenchan {float} -- Observation frequency in Hertz

    Returns:
        {astropy.wcs.WCS} -- WCS information describing the observation
    """
    pixscale = 0.5 / float(cenchan)
    w = wcs.WCS(naxis=2)
    w.wcs.crpix = [4000,4000]
    w.wcs.cdelt = np.array([-pixscale,pixscale])
    w.wcs.crval = [ra, dec]
    w.wcs.ctype = ["RA---SIN", "DEC--SIN"]
    w.wcs.cunit = ["deg","deg"]
    w._naxis1 = 8000
    w._naxis2 = 8000
    return w

if __name__ == "__main__":
    conn = mdb.connect()
    cur = conn.cursor()

    # TODO: Add a proper argument parser
    if len(sys.argv) == 1:
        print 'Getting all obsids from the user database...'
        obsids = get_obs(cur)
        print '...{0} obsids found'.format(len(obsids))
    else:
        print 'Reading obsids from {0}...'.format(sys.argv[1])
        obsids = [int(i.strip()) for i in open(sys.argv[1], 'r')]
        print '...{0} obsids found'.format(len(obsids))

        # This could be done with one call with a change to the SQL WHERE IN
        obsids = [list(get_obs(cur, obs_id=i))[0] for i in obsids]


    srclist = []
    for row in get_srcs(cur):
        srclist.append(Source(row[0],SkyCoord(row[1],row[2],unit=u.deg),row[3],row[4],row[5]))

    for row in obsids:
        w = create_wcs(row[1],row[2],row[3])
        t = Time(int(row[4]), format='gps')
        freq = 1.28 * row[3]
        for src in srclist:
            # Delays are stored as a string by json
            xx, yy = beam_value(src.pos.ra.deg, src.pos.dec.deg, t, json.loads(row[5]), freq*1.e6)
            # Ignoring spectral curvature parameter for now
            appflux = src.flux * ( (freq / 150.)**(src.alpha) ) * (xx+yy)/2.
            if np.isnan(appflux):
                appflux = 0.0
            
            print row[0], src.name, appflux, check_coords(w, src.pos)
            
            insert_app(row[0], src.name, float(appflux), check_coords(w, src.pos), cur)
    conn.commit()
    conn.close()
