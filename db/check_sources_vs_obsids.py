import os
import sys
from astropy.coordinates import SkyCoord
from astropy import wcs
from astropy.io import fits
from astropy.time import Time
import astropy.units as u
from astropy.table import Table
import json
import mysql_db as mdb
import numpy as np
import argparse

from multiprocessing import Pool

from populate_sources_table import Source
from check_src_fov import check_coords
from beam_value_at_radec import beam_value

__author__ = ["Natasha Hurley-Walker",
              "Tim Galvin"]


NO_SRCS = 7 # Number of unique sources in the database. 
            # TODO: Make this something derived from the database


def create_conn_cur():
    """Creates a database connection and cursor object

    Returns:
        {mysql.connector.Connection} -- an open connection to the database
        {mysql.connector.Cursor} -- a cursor object read for work
    """
    conn = mdb.connect()
    cur = conn.cursor()

    return conn, cur


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
    cur.execute("""
                REPLACE INTO calapparent
               (obs_id, source, appflux, infov)
               VALUES (%s, %s, %s, %s); 
               """,
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
                         FROM sources
                         """)
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
        cur.execute("""
                    SELECT obs_id, ra_pointing, dec_pointing, cenchan, starttime, delays
                    FROM observation
                    """)
        
    else:
        cur.execute("""
                    SELECT obs_id, ra_pointing, dec_pointing, cenchan, starttime, delays 
                    FROM observation WHERE obs_id = %s 
                    """, 
                    (obs_id, ))

        
    return cur.fetchall()


def get_all_obsids():
    """Helper function to create a single database connection to get all obsids
    from the database without reinventing the whell. The database connection is
    killed to ensure no funny business with the multi-processing. 

    Returns:
        {list} -- a iterable with each element being an int
    """
    conn = mdb.connect()
    cur = conn.cursor()

    print 'Getting all obsids from the user database...'
    obsids = get_obs(cur)
    print '...{0} obsids found'.format(len(obsids))

    return [o[0] for o in obsids]


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


def check_for_obsid(cur, obsid):
    """For the given obsid calculate the apparent flux of sources and insert them
    into the database if they are not there
    """
    
    cur.execute("""
                SELECT count(*) FROM calapparent WHERE obs_id = %s
                """,
                (obsid, ))
    results = list(cur.fetchall()) 
    
    return True if results[0][0] == NO_SRCS else False


def insert_sources_obsid(obsid, force_update=False):
    """Insert the apparent brightness of each source into the database for the 
    provided obsid. By default, if it is detected that the obsid is already entered
    then the sources will not be entered into the database. 

    Arguments:
        obsid {int} -- observation ID number to inspection

    Keywork Arguments:
        force_update {bool} -- Perform check and database insert even is obsid has already been processed
    """
    if not isinstance(obsid, int):
        print 'Expected type `int` for obsid, received {0}'.format(type(obsid))
        return
    
    conn, cur = create_conn_cur()

    # No need to do anything further if the obsid is already in the databvase
    if check_for_obsid(cur, obsid) and not force_update:
        print 'Obsids already found for obsid {0}. Skipping.'.format(obsid)
        conn.close()
        return

    obs_details = list(get_obs(cur, obs_id=obsid))[0]

    # Get list of sources
    srclist = [Source(src[0],SkyCoord(src[1], src[2],unit=u.deg), src[3], src[4], src[5]) for src in get_srcs(cur)]

    # Create the WCS to create/evaluate the FEE beam
    w = create_wcs(obs_details[1], 
                  obs_details[2],
                  obs_details[3])
    t = Time(int(obs_details[4]), format='gps')
    freq = 1.28 * obs_details[3]
    
    xx_srcs, yy_srcs = beam_value(
                        [s.pos.ra.deg for s in srclist], 
                        [s.pos.dec.deg for s in srclist], 
                        t, 
                        json.loads(obs_details[5]), 
                        freq*1.e6
                    )

    for xx, yy, src in zip(xx_srcs, yy_srcs, srclist):
              
        # Ignoring spectral curvature parameter for now
        appflux = src.flux * ( (freq / 150.)**(src.alpha) ) * (xx+yy)/2.
        if np.isnan(appflux):
            appflux = 0.0
        
        insert_app(obs_details[0], src.name, float(appflux), check_coords(w, src.pos), cur)              

    conn.commit()
    conn.close()


def create_peel_model(sources):
    """Creates the mode to be used by calibrate to peel out sources from 
    parts of the visibility data. Assumes access to the GLEAM-X sky model.  
    
    Arguments:
        sources {Iterable} -- an iterable of known sources (identified by their name) that need to be peeled. 
    """
    # Do the things
    return ''


def update_db_with_peeled(obsid, sources, curr):
    """Update the observation table to record which sources were peeled. 
    
    Arguments:
        obsid {int} -- observation id to update
        sources {int} -- the list of peeled sources to insert
        curr {mysql.connector.Cursor} -- an activate cursor to use
    """
    curr.execute(
            """
            UPDATE observation
            SET peelsrcs=%s
            WHERE obs_id=%s
            """,
            (sources, obsid)
        )
    curr.commit()



def check_obsid_peel(obsid, local_sky, check_exists=True, min_threshold=0.):
    """Check to see whether a specified obsid has sources that need to be peeled
    
    Arguments:
        obsid {int} -- the observation id to inspect
        local_sky {astropy.table.Table} -- table with columns following the GLEAM-X sky model definition.  

    Keyword Arguments:
        check_exists {bool} -- will sanity check and ensure that an `obsid` is in `calapparent` table (default: {True})
        min_threshold {float} -- minimum flux to have before bothering with attempting to peel (default: {0.0})

    Returns:
    TODO
    """
    # Compute brightness of known sources if necessary
    if check_exists:
        insert_sources_obsid(obsid)

    conn, cur = create_conn_cur()

    # Get the brightness of known / scary sources
    cur.execute(
            """
            SELECT source, appflux 
            FROM calapparent
            WHERE obs_id = %s and infov=0
            """,
            (obsid, )
        )

    peel_sources = Table(
                       rows=list(cur.fetchall()),
                       names=['source', 'appflux']
                    )

    # TODO: No point going further if all known sources are sufficently faint
    if max(peel_sources['appflux']) < min_threshold:
        print 'No known bright sources require peeling. '
        return

    # Compute the FEE beam
    obs_details = list(get_obs(cur, obs_id=obsid))[0]
    w = create_wcs(obs_details[1], 
                  obs_details[2],
                  obs_details[3])
    t = Time(int(obs_details[4]), format='gps')
    freq = 1.28 * obs_details[3]

    xx_srcs, yy_srcs = beam_value(
                        local_model['RAJ2000'],
                        local_model['DEJ2000'], 
                        t, 
                        json.loads(obs_details[5]), 
                        freq*1.e6
                    )

    local_sky['obs_flux'] = local_sky['S_200'] * (freq / 200.)**(local_sky['alpha']) * (xx_srcs + yy_srcs)/2

    peel_mask = max(local_sky['obs_flux']) < peel_sources['appflux']

    if np.sum(peel_mask) > 0:
        print peel_sources['source'][peel_mask]
        model = create_peel_model(peel_sources['source'][peel_mask])

        return 


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Calculates and stores the apparent brightness of sources (stored in the GLEAM-X database)")
    parser.add_argument('-f', '--file', nargs=1, default=None, help='A text file of obsids to check')
    parser.add_argument('-o', '--obsid', nargs=1, default=None, help='A single obsid to check')
    parser.add_argument('-a', '--all-obsids', default=False, action='store_true', help='Calculate apparent of sources for all known obsids')
    parser.add_argument('-p', '--processes', default=1, type=int, help='How many parallel jobs to execute. Placeholder until hdf5 concurrent reads figured out.')
    parser.add_argument('-u', '--force-update', default=False, action='store_true', help='Force the insertion of an apparent brightness for all sources for all obsids')
    parser.add_argument('-c', '--peel-check', nargs=1, default=False, help='Return a log of objects that need to be peeled. Only relevant for when a single `obsid` is provided (whether via argument of via file)/')

    args = parser.parse_args()

    # Some sanity checks
    if all([args.file is None, args.obsid is None, args.all_obsids is False]):
        print 'Either `file`, `obsid` or `all-obsids` has to be set. Exiting. '
        sys.exit(1)

    # Configure the obsids to process
    if args.file is not None:
        obsids = [int(i.strip()) for i in open(sys.argx[1], 'r')]
    elif args.obsid is not None:
        obsids = (int(args.obsid), )
    else:
        obsids = get_all_obsids()

    print '{0} obsids to process'.format(len(obsids))

    # When no peeling is needed, can process all ids as specified
    if args.peel_check is False:
        if args.processes == 1:
            for count, obsid in enumerate(obsids):
                print '{0}) {1}'.format(count+1, obsid)
                insert_sources_obsid(obsid, force_update=args.force_update)

        else:
            print '\nAttempting with {0} spawned processes'.format(args.processes)
            print '\nWARNING: There appears to be some con-currency issues while reading the HDF5 files for the FEE. '

            sys.exit(1)

            # Because the `map` only takes an iterable and because everything in 
            # python is an object, wrap up what we need
            def worker(x): 
                insert_sources_obsid(x, force_update=args.force_update)
            
            pool = Pool(processes=args.processes)
            pool.map(worker, obsids)

    # Can not provide more than one obsid to look at at this time. 
    # can't see in pipeline when any more than one would be needed. 
    elif len(obdsids) == 1:
        components = Table.read(args.peel_check)

        print 'Loaded {0} table, with shape {1} components'.format(args.peel_check, len(components))
    
        check_obsid_peel(obsids[0], components)

    # Something went wrong, we shall end it here
    else:
        print '`--peel-check` ({0}) and provided obsids ({1}) appears misconfigured.'.format(args.peel_check, obsids)
        sys.exit(1)

