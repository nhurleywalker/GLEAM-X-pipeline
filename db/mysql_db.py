#!/usr/bin/env python

"""Small set of utility functions to keep the mysql connections in one location. 
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
    conn = mysql.connect(**dbconfig)
    
    if switch_db:
        conn.cursor().execute("USE {0}".format(dbname))

    return conn
