#! python
from __future__ import print_function
from  gleam_x.db import mysql_db as mdb
import sys

__author__ = ['Paul Hancock', 
              'Natasha Hurley-Walker',
              'Tim Galvin']

dbname = mdb.dbname

schema = """
CREATE DATABASE {0};

USE {0};

CREATE TABLE observation
(
obs_id INT PRIMARY KEY,
projectid TEXT,
lst_deg FLOAT,
starttime TEXT,
duration_sec INT,
obsname TEXT,
creator TEXT,
azimuth_pointing FLOAT,
elevation_pointing FLOAT,
ra_pointing FLOAT,
dec_pointing FLOAT,
cenchan INT,
freq_res FLOAT,
int_time FLOAT,
delays TEXT,
calibration BOOL,
cal_obs_id INT,
calibrators TEXT,
peelsrcs TEXT,
flags TEXT,
selfcal BOOL,
ion_phs_med INT,
ion_phs_peak INT,
ion_phs_std INT,
archived BOOL,
nfiles INT,
status TEXT,
FOREIGN KEY(cal_obs_id) REFERENCES observation(obs_id)
);

CREATE TABLE processing
(
job_id INT,
task_id INT,
host_cluster VARCHAR(255),
submission_time INT,
task TEXT,
user TEXT,
start_time INT,
end_time INT,
obs_id INT,
status TEXT,
batch_file TEXT,
stderr TEXT,
stdout TEXT,
output_files TEXT,
FOREIGN KEY(obs_id) REFERENCES observation(obs_id),
CONSTRAINT job_task_id PRIMARY KEY (job_id,task_id,host_cluster)
);

CREATE TABLE sources
(
source VARCHAR(255) NOT NULL,
RAJ2000 FLOAT,
DecJ2000 FLOAT,
flux FLOAT,
alpha FLOAT,
beta FLOAT,
PRIMARY KEY (source)
);

CREATE TABLE calapparent
(
obs_id INT,
source VARCHAR(255),
appflux FLOAT,
infov BOOL,
FOREIGN KEY(obs_id) REFERENCES observation(obs_id),
FOREIGN KEY(source) REFERENCES sources(source),
CONSTRAINT obs_src PRIMARY KEY (obs_id,source)
);

CREATE TABLE mosaic
(
mos_id INT AUTO_INCREMENT PRIMARY KEY,
obs_id INT,
job_id INT,
task_id INT,
host_cluster VARCHAR(255),
user TEXT,
subband TEXT,
status TEXT,
submission_time INT,
start_time INT,
end_time INT,
FOREIGN KEY(obs_id) REFERENCES observation(obs_id)
);
""".format(dbname)

def main():
    conn = mdb.connect()
    cur = conn.cursor()
    
    for cmd in schema.split(';'):
        if cmd.strip() == "":
            continue

        print(cmd + ';')
        cur.execute(cmd)
    conn.close()

if __name__ == '__main__':

    main()
