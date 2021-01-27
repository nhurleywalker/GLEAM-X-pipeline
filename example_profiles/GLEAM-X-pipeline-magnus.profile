#! /bin/bash -l

echo "loading gleam-x profile"

# Any system module file should be loaded here. Aside from singularity and slurm there are
# no additional modules that are expected to be needed
module load singularity

# Before running obs_*.sh scripts ensure the completed configuration file has been sourced. 
# As a convention when specifying paths below, please ensure that they do not end with a trailing '/', as
# this assists in readability when combining paths. 


# Basic configuration
cluster="magnus"            # System-wide name of cluster, e.g. "garrawarla". This does not have to have a one-to-one correspondance to the
                                # actual system name.
export GXUSER=$(whoami)         # User name of the operator running the pipeline. This is here to generate user-specific filenames and paths. 
                                # It is recommend to use the login account name, although in principal this is not critical and other approaches
                                # could be adopted
export GXVERSION='3.1.0'        # Version number of the pipeline. This should not be changed. Currently it is defined here but not used.  
export GXACCOUNT="pawsey0272"               # The SLURM account jobs will be run under. e.g. 'pawsey0272'. Empty will not pass through a 
                                # corresponding --account=${GXACCOUNT} to the slurm submission. Only relevant if SLURM is tracking time usage 
export GXBASE="/scratch/pawsey0272/${GXUSER}/GLEAM-X-pipeline" # Path to base of GLEAM-X Pipeline where the repository was 'git clone' into, including the folder name, e.g. "/astro/mwasci/tgalvin" 
export GXSCRATCH="/scratch/pawsey0272/${GXUSER}"     # Path to scratch space used for processing on the HPC environment, e.g. /scratch
export GXHOME="${GXSCRATCH}"    # HOME space for some tasks. In some system configurations singularity can not mount $HOMR, but applications (e.g. CASA, python) would like 
                                # one to be available to cache folders. This does not have to be an actual $HOME directory, just a folder with read and write access. 
                                # Suggestion is the same path as the scratch space, e.g. $GXSCRATCH. 
export GXCONTAINER="${GXSCRATCH}/gleamx_testing_small.img"  # Absolute path to the GLEAM-X singularity container, including the file name, e.g. "${GXSCRATCH}/gleamx.img"
                                              # This container is still being evaluated and available when requested from Tim Galvin. In a future update
                                              # the container will be automatically downloaded alongside other data dependencies. 

# SLURM compute schedular information
export GXCOMPUTER=${cluster}    # Maintained for compatability. Describes the name of the cluster, e.g. "magnus".
export GXCLUSTER=${cluster}     # Maintained for compatability. Describes the name of the cluster, e.g. "magnus".
export GXSTANDARDQ="workq"      # Slurm queue to submit tasks to, e.g. "workq". Available queues can be inspected using 'sinfo' on a system where the slurm schedular is available

# Compute node memory specification
export GXABSMEMORY=58           # Absolute memory a machine should be considered to have in GB, e.g. 60. This value is submitted to slurm via "--mem=${GXABSMEMORY}"
                                # For tasks that require only a small memory allocation, this option is ignored and a hard-coded value of "24G" is used. This is done
                                # to assist in quicker resource allocation 
export GXMEMORY=40              # Typical memory a program should use in GB, e.g. 50. This is used for tasks like 'calibrate' and 'wsclean' to attempt to limit
                                # its usage to the fit within the memory allocation alongside other overheads. It is recommended that this be ~10G smaller than
                                # GXABSMEMORY, although there is no technical reason it could be set otherwise. 

# Compute node CPU specification
export GXNCPUS=48               # Number of CPUs of each machine, e.g. 48. For tasks that have a 'core' like option this value is passed. 
export GXNLCPUS=48              # Number of logical CPUs on each machine, e.g. 48. This option may be phased out. 
export GXNPCPUS=24              # Number of physical CPUs on each machine, e.g. 24. This is meant to count only the physical cores available. 
export GXNCPULINE="--ntasks-per-node=${GXNPCPUS}"  # Informs the SLURM request how many CPUs should be allocated, e.g. "--ntasks-per-node=${GXNPCPUS}" 
                                # If unset the SLURM default will be used. For tasks that are not parallelisable (apply_cal, uvflag), 
                                # this option will be overwritten (if it is set) to ensure a single core is used.
                                # There may be some interaction between this line and $GXNCPUS when deployed. For instance, on magnus only 
                                # 24 cores may be requested in a slurm request, but there are 48 available in the job (logical hyper-threaded cores ignored in resource request) 

# SLURM job submission details 
export GXTASKLINE=                              # Reserved space for additional slurm sbatch options, if needed. This is passed to all SLURM sbatch calls. 
export GXLOG="${GXBASE}/log_${GXCLUSTER}"       # Path to output task logs, e.g. ${GXBASE}/queue/log_${GXCLUSTER}. It is recommended that this is cluster specific. 
export GXSCRIPT="${GXBASE}/script_${GXCLUSTER}" # Path to place generated template scripts. e.g. "${GXBASE}/script_${GXCLUSTER}". It is recommended that this is cluster specific.
export GXTRACK='track'                       # Directive to inform task tracking for meta-database. 'track' will track task progression. Anything else will disable tracking. 


export GXSSH="${GXBASE}/ssh_keys/gx_${GXUSER}"  # Path to SSH keys to be used for archiving. Keys names should follow a 'gx_${GXUSER}' convention, e.g. "${GXBASE}/ssh_keys/gx_${GXUSER}"
                                                # Ensure restricted folder/file permissions, e.g. cmod -R 700 "${GXBASE}/ssh_keys"
                                                # Keys can be generated with: ssh-keygen -t rsa -f "${GXBASE}/ssh_keys/gx_${GXUSER}"
                                                # This is used only in the archiving script, as on Magnus it appears singularity can not bind to $HOME correctly

# Data dependencies
export GXMWAPB="${GXBASE}/data/mwa_pb"  # The calibrate program requires the FEE model of the MWA primary beam.
                                        # This describes the path that containers the file mwa_full_embedded_element_pattern.h5
                                        # and can be downloaded from http://cerberus.mwa128t.org/mwa_full_embedded_element_pattern.h5
                                        # If this folder does not exist, it is created. 
export GXMWALOOKUP="${GXBASE}/data/pb"  # The MWA PB lookup HDF5's used by lookup_beam.py and lookup_jones.py. 
                                        # If this folder does not exist, it is created. 

# Details for obs_manta
# Data dependencies are downloaded into the directories below if the directories do not exist. 
export GXCOPYA=             # Account to submit obs_manta.sh job under, if time accounting is being performed by SLURM.
                            # Leave this empty if the job is to be submitted as the user and there is no time accounting.
export GXCOPYQ='copyq'      # A required parameter directing the job to a particular queue on $GXCOPYM. Set as just the queue name, e.g. 'copyq'
export GXCOPYM='zeus'       # A required parameter directing the job to be submitted to a particular machine. Set as just the machine name, e.g. 'zeus'

# Staging area
export GXSTAGE="${GXSCRATCH}/stage"  # To support the polarisation effort led by Xiang Zhang and George Heald at CSIRO, calibrated measurement sets
                            # will be placed into a staging area so that they may be remotely copied. Due to the CSIRO network security 
                            # set up, connections have to be initiated from their internal network, meaning the GLEAM-X pipeline will not
                            # be able to initiate the transfer. If you are *NOT* involved with the processing effort for all of the G0008
                            # data then you may ignore this. If you *ARE* involved, please reach out to a GLEAM-X member to ensure this
                            # is correctly configured and known on the CSIRO side. 

# Singularity bind paths
# This describes a set of paths that need to be available within the container for all processing tasks. Depending on the system
# and pipeline configuration it is best to have these explicitly set across all tasks. For each 'singularity run' command this
# SINGULARITY_BINDPATHS will be used to mount against. These GX variables should be all that is needed on a typical deployed 
# pipeline, but can be used to further expose/enhance functionality if desired. 
export SINGULARITY_BINDPATH="${HOME}:${HOME},${GXSCRIPT},${GXBASE},${GXSCRATCH},${GXSSH},${GXMWALOOKUP}:/pb_lookup,${GXMWAPB},${GXSTAGE}"



export PATH="${PATH}:${GXBASE}/bin" # Adds the obs_* script to the searchable path. 
export HOST_CLUSTER=${GXCLUSTER}    # Maintained for compatability. Will be removed soon. 

# Force matplotlib to write configuration to a location with write access. Attempting to fix issues on pawsey 
export MPLCONFIGDIR="${GXSCRATCH}"
#Redirect astropy cache and home location. Attempting to fix issue on pawsey.
export XDG_CONFIG_HOME="${GXSCRATCH}"
export XDG_CACHE_HOME="${GXSCRATCH}"

# Loads a file that contains secrets used throughout the pipeline. These include
# - MWA_ASVO_API_KEY
# - GXDBHOST
# - GXDBPORT
# - GXDBUSER
# - GXDBPASS
# This GXSECRETS file is expected to export each of the variables above. 
# This file SHOULD NOT be git tracked! 
GXSECRETS="${GXBASE}/secrets/gleamx_secrets.profile"
if [[ -f ${GXSECRETS} ]]
then
    source "${GXSECRETS}"
fi

# Check that required variables have a value. This perfoms a simple 'is empty' check
for var in GXCOMPUTER GXCLUSTER GXSTANDARDQ GXABSMEMORY GXMEMORY GXNCPUS GXNLCPUS GXNPCPUS GXUSER GXCOPYQ GXCOPYM GXLOG GXSCRIPT
do
    if [[ -z ${!var} ]]
    then
        echo "${var} is currently not configured, please ensure it was a valid value"
        return 1
    fi
done

# Check that the following values that point to a path actually exist. These are ones that (reasonably) should not
# automatically be created
for var in GXBASE GXSCRATCH GXHOME
do
    if [[ ! -d ${!var} ]]
    then
        echo "The ${var} configurable has the path ${!var}, which appears to not exist. Please ensure it is a valid path."
        return 1
    fi
done

# Creates directories as needed below for the mandatory paths if they do not exist
if [[ ! -d "${GXLOG}" ]]
then
    mkdir -p "${GXLOG}"
fi

if [[ ! -d "${GXSCRIPT}" ]]
then
    mkdir -p "${GXSCRIPT}"
fi

# Create the staging area if it has been configured, otherwise skip
if [[ ! -z "${GXSTAGE}" ]]
then
    if [[ ! -d "${GXSTAGE}" ]]
    then
        mkdir -p "${GXSTAGE}"
    fi
fi

# Go fourth and download the data dependencies
if [[ -d ${GXBASE} ]]
then
    if [[ ! -d ${GXMWAPB} ]]
    then
        echo "Creating ${GXMWAPB} and caching FEE hdf5 file"
        mkdir -p ${GXMWAPB} \
            && wget -P ${GXMWAPB} http://cerberus.mwa128t.org/mwa_full_embedded_element_pattern.h5
    fi

    if [[ ! -d ${GXMWALOOKUP} ]]
    then
        echo "Creating ${GXMWALOOKUP} and caching hdf5 lookup files"
        mkdir -p ${GXMWALOOKUP} \
            && wget -O pb_lookup.tar.gz -P ${GXMWALOOKUP} https://cloudstor.aarnet.edu.au/plus/s/77FRhCpXFqiTq1H/download \
            && tar -xzvf pb_lookup.tar.gz -C ${GXMWALOOKUP} \
            && rm pb_lookup.tar.gz

    fi
fi

