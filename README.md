# GLEAM-X-pipeline

The goal of this pipeline is to reduce the data observed as part of the GLEAM-X project (G0008), but it is also applicable to many other MWA datasets. The pipeline was originally written for the Pawsey Magnus and Zeus systems, but has been adapted for compatibility with wider HPC systems. Software dependencies are built within a singularity container, which is subsequently used throughout the execution of the pipeline.  

It borrows significantly from the MWA-Fast-Transients pipeline written by Paul Hancock and Gemma Anderson: https://github.com/PaulHancock/MWA-fast-image-transients.

## Credits
Please credit Natasha Hurley-Walker, Paul Hancock, Gemma Anderson, John Morgan, Stefan Duchesne, and Tim Galvin, if you use this code, or incorporate it into your own workflow. Please acknowledge the use of this code by citing this repository, and until we have a publication accepted on this work, we request that we be added as co-authors on papers that rely on this code.

## Overall Design
The pipeline is divided into two main components. The first is a set of bash scripts that direct the processing of the pipeline, and the second is a set ofpython codes that implement specialised methods. 

Each stage within the pipeline has at least two bash scripts associated with it. One is a template script, which contains special placeholders which represent observation specific values. The second is a generating script. Based on user specifications, the generating script will adapt the template for processing, replacing the placeholder values with there actual values appropriate for processing. The mechanism used to do this substitution is a `sed` command within the generating script. In general, template scripts end in `tmpl` and are placed in the `templates` sub-directory, and the generating scripts have filenames beginning with either `obs` or `drift` and are placed in the `bin` directory. These `obs` and `drift` scripts are also responsible for submitting work to the SLURM scheduler. 

The python codes are stored under the `gleam_x` sub-directory in a structure that is `pip` installable, if required. These codes have been updated to `python3`. Although some effort has been made to maintain backwards compatibility with `python2`, this is not guaranteed. Many of these python codes are called as standard command line programs within the pipeline, and have python module dependencies that should be standardised. For this reason, the `gleam_x` python module is installed within the context of the singularity container. When deploying the pipeline for use, it is not necessary to `pip install` the python module within this repository so that it is accessible as part of the larger HPC environment. 

Throughout all tasks there is the expectation of certain GLEAM-X environment varibles being present. These describe the 'set-up' of the HPC, and include configurables like the path to scratch space, compute node specifications, data dependency locations, among other things. These GLEAM-X environment variables are described in the template profile. 

Generated scripts are executed entirely within the singularity container context. This includes calls to `gleam_x` python scripts, which are bundled within the container. The `obs_*.sh` are executed on the host system (i.e. outside the container), and will submit the generated script to the SLURM schedular for execution. When SLURM allocates a resource, it first load the singularity container and then pas it the generated script for execution. 

## Structure of pipeline
Code directory:
- bin: contains the bash scripts that generate files for execution
- templates: the template bash scripts that are used as the basis to generate submittable scripts
- containers: a container related space, currently containing the build script for the singularity container for reference
- models: Sky model files
- gleam_x: Python module containing the GLEAM-X python code 

In the base path there are two files of importance:
- setup.py: file that allows for `gleam_x` to be installed as a python module
- GLEAM-X-pipeline-template.profile: a template of the GLEAM-X configuration

## track_task.py
Used throughout the pipeline to track the submission/start/finish/fail of each of the jobs. This is dependent on a properly configured mysql server managing an existing database. The database tables could be created using the `make_db.py` located within the `gleam_x/db` directory. Additionally, the `track_task.py` script will only execute correctly if account details required to authenticate against the mysql served are set as GLEAM-X environment variables. If these details aren't provided (or the tracking has been disabled), `track_task.py` will simply exit with a small message. 

`track_task.py` is a script distributed with the `gleam_x` python module that makes up a component of this repository and is not intended for use outside of these scripts.

## Template configuration script

We provide `GLEAM-X-pipeline-template.profile` as an example configuration file that needs to be updated for the exact HPC system the GLEAM-X pipeline is being deployed on. Each environment variable also carries with it a brief description of its purporse and expected form.

When running the completed template file for the first time, a set of folders are created, and data dependencies are automatically downloaded following the specification set. This should be a 'one-and-done' operation, but if locations are updated at a later time (or are accidently deleted) they would be reissued. 

It will be necessary to `source` the completed template file before running any of the `obs` scripts. This will export all GLEAM-X configurables into the environment of spawned processes. 

The template example configuration profile also references a secrets file. It is intended that this file (which is not included in this repository) would contain user authentication details required for aspects of the pipeline, including the downloading of MWA data from ASVO and authentication against the mysql database. This file is intentionally not included in this repository in an effort to ensure secrets are not accidently commited and made available. 

NOTE: The GLEAM-X secrets file is still being tested for reliability, and its use at the moment should be done with caution as it could change. 

## Singularity Container

The build recipe for the singularity container is included under the `containers` folder. Unfortunately, the `mwa-reduce` is a critical dependency and is only accessible to members of the MWA collaboration. For this reason, it may not be possible to build the singularity container yourself. 

We are happy to distribute the container to anyone upon request. In a future release we plan on having the GLEAM-X singularity container automatically download alongside the data dependencies. 

## Steps to deploy

The following steps should install the pipeline for use on a HPC system with a SLURM schedular:
- `git clone` this repository
- Copy the `GLEAM-X-pipeline-template.profile` file (e.g. `cp GLEAM-X-pipeline-template.profile GLEAM-X-pipeline-hpc.profile`), and edit based on the desired system configuration
- Build the singularity container (if you have access to the `mwa-reduce` repository), or contact a member of the group for the current container
- Run the configuration file to create directories and download data dependencies, e.e `source GLEAM-X-pipeline-hpc.pipeline`
- If archiving using the GLEAM-X store (see the next subsection) reach out to a GLEAM-X member for further details

All compiled software is already prebuilt in the singularity container. There is no need to install any python modules on the host system, as all python code is executed within the context of the singularity container. 

The pipeline expects that a completed configuration profile and has been completed and loaded (using `source`) before running any of the associated `obs_*.sh` scripts. It is recommended that you `source` the completed configuration file in your `bash_profile`, so that it is loaded on login. *A word of warning*. If you adopt this approach and your home directory (where `bash_profile` usually resides) is shared among multiple clusters, special care should be taken to ensure you `source` the correct profile. 

## SSH keys and archiving

The GLEAM-X team have secured an ongoing archive at Data Central (https://datacentral.org.au/) that is used to save completed pipeline data products. These are copied as part of an archive stage using a numbus instance as a tunnel. To successfully run this stage your public ssh key has to be approved and stored as an allowed user. Reach out to one of the GLEAM-X members for assistance. 

As a note - within the Pawsey system it has been found that the singularity container is not able to consistently bind to the home directory of the user, meaning that the users default ssh credentials are not accessible. For this reason the current suggestion is to create a ssh keypair specific to the GLEAM-X pipeline. The ideal location would be with $GXBASE directory, however any path would be acceptable if you have read/write permission. Creating the ssh keypair is not part of the current version of the configuration template, but such a keypair can be created with `ssh-keygen -t rsa -f "${GXBASE}/ssh_keys/gx_${GXUSER}"` after the GLEAM-X configuration profile has been loaded. The archive stage expects the key to follow a `gx_${GXUSER}` format. This may change in a future release. 

## Example workflow

A typical workflow might look like:
   - Look on the MWA metadata pages for a set of observations of interest: http://ws.mwatelescope.org/admin/observation/observationsetting/ or http://ws.mwatelescope.org/metadata/find
   - Download the list of observation IDs to a text file
   - Go to your configured scratch space ($GXSCRATCH) and create a project directory with whatever pithy name you feel is appropriate
   - Put the text file there, and then run obs_manta.sh on it to download that list of observations
   - Once they have downloaded, for each observation, run `obs_autoflag.sh` and `obs_autocal.sh`
   - Look at the calibraton solutions, and if they generally look OK, for each observation, run `obs_apply_cal.sh` to apply them
   - Run `obs_uvflag.sh` to flag potential RFI
   - Run some deep imaging via `obs_image.sh`
   - Run the post-imaging processing via `obs_postimage.sh` to perform source-finding, ionospheric de-warping, and flux density scaling to GLEAM.

## Ongoing issues
This section briefly outlines the current areas of development and are included as a note for users of future changes:
- GXSECRETS
  - This is still being tested, with tweaks being made to the container to be support the desired behaviour

- `obs_manta.sh`
  - This is currently being tested after being ported to use the GLEAM-X configuration profile approach that generalises it away from a `zeus/pawsey` specific setup

- Intermittent `obs_archive.sh` issues
  - There appears to be some stability issues when running `obs_archive.sh`. Rsync reports some source files do not exist, when in fact they do, and are accessible manually. This may be related to the use of webDAV as an interface, and some form of time out on the remote system (test observation has alredy been archived, so rsync attempts to scan/update)

` HOME not binding correctly under some conditions
  - It appears that under some conditions (likely a network mount point not being followed correctly or singularity version mismatch) that singularity is having difficulty binding to a users $HOME directory. This happens consistently within the pawsey environment. A ticket has been raised and the issue is being investigated. 

## Features to implement
We plan to:

- To support the polarisation component of GLEAM-X, a stage (likely to be included as part of `obs_archive.sh`) will copy data to a staging area, where it will be copied into the CSIRO network at a later time. 

- To automatically download the GLEAM-X singularity container, if not already present

## Detailed script descriptions

### obs_manta.sh
Use the [ASVO-mwa](https://asvo.mwatelescope.org) service to do the cotter conversion and then download the resulting measurement set. No matter which cluster the jobs are submitted from, they will always run on the Zeus copyq.

usage:
```
obs_manta.sh [-p project] [-d dep] [-q queue] [-s timeave] [-k freqav] [-t] -o list_of_observations.txt
  -d dep      : job number for dependency (afterok)
  -q queue    : job queue, default=copyq
  -p project  : project, (must be specified, no default)
  -s timeav   : time averaging in sec. default = 4 s
  -k freqav   : freq averaging in KHz. default = 40 kHz
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  -o obslist  : the list of obsids to process
```
uses templates:
- `manta.tmpl` (obsnum->OBSNUM/timeav->TRES/freqav->FRES)

### obs_autocal.sh
Generate calibration solutions for a given observation using the GLEAM-based sky model in the GLEAM-X-pipeline/models directory.

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

### obs_apply_cal.sh
Apply a pre-existing calibration solution to a measurement set.

Usage:
```
obs_apply_cal.sh [-p project] [-d dep] [-q queue] [-c calid] [-t] [-n] obsnum
  -p project  : project, no default
  -d dep      : job number for dependency (afterok)
  -q queue    : job queue, default=gpuq
  -c calid    : obsid for calibrator.
                project/calid/calid_*_solutions.bin will be used
                to calibrate if it exists, otherwise job will fail.
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  obsnum      : the obsid to process
```

uses templates:
- `apply_cal.tmpl` (obsnum->OBSNUM, cal->CALOBSID)
  - applies the calibration solution from one data set to another

### obs_uvflag.sh
Scan the visibility data and flag for RFI

Usage:
```
obs_uvflag.sh [-p project] [-d dep] [-a account] [-z] [-t] obsnum
  -p project : project, no default
  -d dep     : job number for dependency (afterok)
  -z         : Debugging mode: flag the CORRECTED_DATA column
                instead of flagging the DATA column
  -t         : test. Don't submit job, just make the batch file
               and then return the submission command
  obsnum     : the obsid to process, or a text file of obsids (newline separated). 
               A job-array task will be submitted to process the collection of obsids. 
```
uses templates:
  - `uvflag.tmpl`
    - scans the visibility data and fits a trend as a function of uv-distance
    - visibilities outside a running mean/std region are flagged
    - uses a python script (`ms_flag_by_uvdist.py`) that is distributed with the `gleam_x` python module

### obs_image.sh
Image a single observation.

Usage: 
```
obs_image.sh [-d dep] [-p project] [-q queue] [-t] obsnum
  -d dep     : job number for dependency (afterok)
  -q queue   : job queue, default=workq
  -p project : project, (must be specified, no default)
  -t         : test. Don't submit job, just make the batch file
               and then return the submission command
  obsnum     : the obsid to process
```
uses templates:
- `image.tmpl`
  - Make four channels and an MFS image
  - Stokes I
  - Joined-channel clean
  - Auto-mask 3-sigma; auto-threshold 1-sigma


### obs_postimage.sh
Perform post-imaging correction on a image, including corrections to account for the distortion of the ionosphere. 

Usage:
```
obs_postimage.sh [-d dep] [-p project] [-a account] [-t] obsnum
  -d dep     : job number for dependency (afterok)
  -p project : project, (must be specified, no default)
  -t         : test. Don't submit job, just make the batch file
               and then return the submission command
  obsnum     : the obsid to process, or a text file of obsids (newline separated). 
               A job-array task will be submitted to process the collection of obsids.
```
uses templates:
  - `postimage.tmpl`
    - performs an `aegean` to perform source finding
    - `fits_warp` and `flux_warp` correct the image for effects of ionosphere
    - source finding is performed again on the corrected image

### obs_archive.sh
Copies selected GLEAM-X data products over to the Data Central archive. This isrequired only for those doing bulk processing of data directly related to G0008. 

Usage:
```
obs_archive.sh [-d dep] [-p project] [-a account] [-u user] [-e endpoint] [-r remote_directory] [-t] obsnum

Archives the processed data products onto the data central archive system. By default traffic is routed through a nimbus instance, requiring a public ssh key to first be added to list of authorized keys. Data Central runs ownCloud, and at the moment easiest way through is a davfs2 mount. Consult Natasha or Tim. 

  -d dep      : job number for dependency (afterok)
  -p project  : project, (must be specified, no default)
  -u user     : user name of system to archive to 
  -e endpoint : hostname to copy the archive data to 
  -r remote   : remote directory to copy files to
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  obsnum      : the obsid to process, or a text file of obsids (newline separated). 
               A job-array task will be submitted to process the collection of obsids.
```
uses templates:
  - `archive.tmpl`
    - requires access to GLEAM-X nimbus instance