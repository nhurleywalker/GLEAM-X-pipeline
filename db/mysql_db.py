#!/usr/bin/env python

"""Small set of utility functions to keep the mysql connections in one location. 

Consider moving this to a Django ORM to keep inline with potential updates to 
the GLEAM-X website
"""
import database_configuration as dbc
import mysql.connector as mysql

__author__ = 'Tim Galvin'

dbname = dbc.dbname 
dbconfig = dbc.dbconfig

def connect(switch_db=True):
    """Returns an activate connection to the mysql gleam-x database
    
    Keyword Paramters:
        switch_db {bool} -- Switch to the gleam_x database before returning the connection object (Default: {True})
    """
    # TODO: What to do if no connection can be established. Should a local SQL
    #       database be used and processing can continue? I'd prefer a blanket 
    #       no can do. 
    conn = mysql.connect(**dbconfig)
    
    if switch_db:
        conn.cursor().execute("USE {0}".format(dbname))

    return conn
