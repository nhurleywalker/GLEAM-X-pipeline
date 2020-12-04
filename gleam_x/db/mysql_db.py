#!/usr/bin/env python

"""Small set of utility functions to keep the mysql connections in one location. 
"""
import os
import mysql.connector as mysql

__author__ = "Tim Galvin"
dbname = "gleam_x"

# TODO: Remove this database_configuration business
try:
    import gleam_x.db.database_configuration as dbc

    dbconfig = dbc.dbconfig
except:
    try:
        host = os.environ["GXDBHOST"]
        port = os.environ["GXDBPORT"]
        user = os.environ["GXDBUSER"]
        passwd = os.environ["GXDBPASS"]

        dbconfig = {"host": host, "port": port, "user": user, "password": passwd}

    except:
        dbconfig = None

if dbconfig is None:
    raise ValueError(
        "Database configuration not correctly set. Either place an appropriate configuration into the gleam_x.db.database_configuration file or export GXDBHOST, GXDBPORT, GXDBUSER and GXDBPASS environment variables. "
    )

dbconn = "mysql://{0}:{1}@{2}:{3}/{4}".format(
    dbconfig["user"], dbconfig["password"], dbconfig["host"], dbconfig["port"], dbname
)


def connect(switch_db=True):
    """Returns an activate connection to the mysql gleam-x database
    
    Keyword Paramters:
        switch_db {bool} -- Switch to the gleam_x database before returning the connection object (Default: {True})
    """
    if dbconfig == None:
        raise ConnectionError(
            "No database connection configuration detected. Ensure an importable `database_configuration` or appropriately set GXDB* environment variables"
        )

    conn = mysql.connect(**dbconfig)

    if switch_db:
        conn.cursor().execute("USE {0}".format(dbname))

    return conn
