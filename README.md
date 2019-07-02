# GLEAM-X-pipeline

The goal of this pipeline is to reduce the data observed as part of the GLEAM-X project (G0008), but it is also applicable to many other MWA datasets. The pipeline is written for the Pawsey Magnus and Zeus systems which uses a SLURM job scheduler. It borrows significantly from the MWA-Fast-Transients pipeline written by Paul Hancock and Gemma Anderson: https://github.com/PaulHancock/MWA-fast-image-transients.

## Credits
Please credit Natasha Hurley-Walker, Paul Hancock, and Gemma Anderson if you use this code, or incorporate it into your own workflow. Please acknowledge the use of this code by citing this repository, and until we have a publication accepted on this work, we request that we be added as co-authors on papers that rely on this code.

## Structure
Code directory (git clone here): /group/mwasci/$USER/GLEAM-X-pipeline
- bin: executable files and template scripts
- db: database location and python scripts for updating the database
- queue: location from which scripts are run
- queue/logs: log files
Scratch directory (do processing here): /astro/mwasci/$USER/
- a project directory you name for yourself ($project in subsequent code)
- in each project directory, a set of obsids (usually $obsid in subsequent code)

## scripts and templates
Templates for scripts are `bin/*.tmpl`, these are modified by the `bin/obs_*.sh` scripts and the completed script is then put in `queue/<obsid>_*.sh` and submitted to SLURM.

## track_task.py
Used by the following scripts to track the submission/start/finish/fail of each of the jobs.
Not intended for use outside of these scripts.

### obs_manta.sh
Use the [ASVO-mwa](https://asvo.mwatelescope.org) service to do the cotter conversion and then download the resulting measurement set.

usage:
```
obs_manta.sh [-p project] [-d dep] [-q queue] [-s timeave] [-k freqav] [-t] -o list_of_observations.txt
  -d dep      : job number for dependency (afterok)
  -q queue    : job queue, default=copyq
  -p project  : project, (must be specified, no default)
  -s timeav   : time averaging in sec. default = 2 s
  -k freqav   : freq averaging in KHz. default = 40 kHz
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  -o obslist  : the list of obsids to process
```
uses templates:
- `manta.tmpl` (obsnum->OBSNUM/timeav->TRES/freqav->FRES)

### obs_autocal.sh
Generate calibration solutions for a given observation. Will use an A-team model in the anoko repository, or the GLEAM-based sky model in the GLEAM-X-pipeline/models directory, depending on the observation.

Usage:
```
obs_autocal.sh [-d dep] [-q queue] [-t] obsnum
  -p project : project, no default
  -d dep     : job number for dependency (afterok)
  -q queue   : job queue, default=workq
  -t         : test. Don't submit job, just make the batch file
               and then return the submission command
  obsnum     : the obsid to process
```

uses templates:
- `autocal.tmpl`
  - creates 3 time-step calibration solutions and compares them using aocal_diff.py to check the ionospheric variation (doesn't do a anything with that information at present)
  - creates a single time-step calibration solution like: `<obsnum>_<calmodel>_solutions_initial.bin`
  - plots the calibration solutions
