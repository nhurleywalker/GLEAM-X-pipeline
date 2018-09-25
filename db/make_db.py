#! python
import sqlite3

__author__ = 'Paul Hancock & Natasha Hurley-Walker'

dbfile = 'GLEAM-X.sqlite'

schema = """
PRAGMA foreign_keys=ON;

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
CONSTRAINT job_task_id PRIMARY KEY (job_id,task_id)
);

CREATE TABLE sources
(
source TEXT,
ra FLOAT,
dec FLOAT,
flux FLOAT,
alpha FLOAT,
beta FLOAT
);

CREATE TABLE calapparent
(
obs_id INT,
source TEXT,
appflux FLOAT,
infov BOOL,
FOREIGN KEY(obs_id) REFERENCES observation(obs_id),
FOREIGN KEY(source) REFERENCES sources(source),
CONSTRAINT obs_src PRIMARY KEY(obs_id,source)
);
"""

def main():
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()
    for cmd in schema.split(';'):
        print cmd + ';'
        cur.execute(cmd)
    conn.close()

if __name__ == '__main__':
    main()
