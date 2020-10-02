#! /bin/bash -l

echo "loading profile"
# TODOs:
# Ensure that there is a chgcentre in the wsclean container and update chgcentre
# Get a CASA container and remove the GXCASA_LOCATION
# Remove the module loads that are redundant with the songularirt containers
# MWA_PB_LOOKUP needs to be packaged somehow as well
# Set up alias terms for the singularity containers called throughout the pipeline?
# Need to refine the mwa_pb_lookup in postimage.tmpl
#            - python /group/mwasci/nhurleywalker/mwa_pb_lookup/lookup_beam.py


if [[ ! -z "$SLURM_CLUSTER_NAME" ]]
then
  # we are on a worker node
  cluster=$SLURM_CLUSTER_NAME
else
  # we are on a login node
  cluster=$PAWSEY_CLUSTER
fi

if [[ "${cluster}" == "zeus" ]]
then
    echo "Zeus!"
    module load pawseytools
    module use /group/mwa/software/modulefiles
    module load manta-ray-client
    module load pigz
    module load MWA_Tools/mwa-sci_test
    module load wsclean/master
    module load wcstools/3.8.7
    module load singularity
    module load python-casacore

    export PATH=${PATH}:/group/mwasci/$USER/bin/
    export PYTHONPATH=$PYTHONPATH:/group/mwasci/$USER/lib/python2.7/site-packages/:~/lib/
    
    GXUSER=$(whoami)
    export GXUSER
    export GXBASE="/group/mwasci/${GXUSER}/GLEAM-X-pipeline"
    export GXSCRATCH="/scratch1/mwasci${GXUSER}"
    export GXCONTAINERS="/pawsey/mwa/singularity"
    export GXCOMPUTER="zeus"
    export GXCLUSTER="zeus"
    export GXSTANDARDQ="workq"
    export GXABSMEM=120
    export GXMEMORY=110
    export GXNCPUS=28
    export GXTASKLINE="#SBATCH --ntasks=${GXNCPUS}"
    export GXLOG="${GXBASE}/queue/logs"
    export GXFMODELS="/group/mwasci/code/anoko/mwa-reduce/models"
    export GXMWAPB="/group/mwasci/software/mwa_pb/mwa_pb/data/"
    GXCASA_LOCATION="/group/mwasci/software/casa-release-5.1.2-4.el7/bin/casa"
    export GXCASA_LOCATION
    GXPBLOOKUP="/group/mwasci/nhurleywalker/mwa_pb_lookup/lookup_jones.py"
    export GXPBLOOKUP
    GXPBLOOKUPBEAM=/group/mwasci/pb_lookup/gleam_jones.hdf5
    export GXPBLOOKUPBEAM

    # TODO: Update to be more consistent with the above lookup
    GXBEAMLOOKUP=/group/mwasci/nhurleywalker/mwa_pb_lookup/lookup_beam.py
    export GXBEAMLOOKUP
    GXBEAMLOOKUPBEAM="/group/mwasci/pb_lookup/gleam_xx_yy.hdf5"
    export GXBEAMLOOKUPBEAM

elif [[ "${cluster}" == "magnus" ]]
then
    echo "Magnus!"
    module load pawseytools
    module use /group/mwa/software/modulefiles
    module load MWA_Tools/mwa-sci 
    module load pigz
    module load wsclean/master
    module load wcstools/3.8.7
    module load singularity

    export PATH=${PATH}:/group/mwasci/$USER/bin/
    export PYTHONPATH=$PYTHONPATH:/group/mwasci/$USER/lib/python2.7/site-packages/:~/lib/
    
    GXUSER=$(whoami)
    export GXUSER
    export GXBASE="/group/mwasci/${GXUSER}/GLEAM-X-pipeline"
    export GXSCRATCH="/scratch1/mwasci${GXUSER}"
    export GXCONTAINERS="/pawsey/mwa/singularity"
    export GXCOMPUTER="zeus"
    export GXCLUSTER="zeus"
    export GXSTANDARDQ="workq"
    export GXABSMEM=60
    export GXMEMORY=50
    export GXNCPUS=48
    export GXTASKLINE=""
    export GXLOG="${GXBASE}/queue/logs"
    export GXFMODELS="/group/mwasci/code/anoko/mwa-reduce/models"
    export GXMWAPB="/group/mwasci/software/mwa_pb/mwa_pb/data/"
    GXCASA_LOCATION=/group/mwasci/software/casa-release-5.1.2-4.el7/bin/casa
    export GXCASA_LOCATION
    GXPBLOOKUP="/group/mwasci/nhurleywalker/mwa_pb_lookup/lookup_jones.py"
    export GXPBLOOKUP
    GXPBLOOKUPBEAM=/group/mwasci/pb_lookup/gleam_jones.hdf5
    export GXPBLOOKUPBEAM

    # TODO: Update to be more consistent with the above lookup
    GXBEAMLOOKUP=/group/mwasci/nhurleywalker/mwa_pb_lookup/lookup_beam.py
    export GXBEAMLOOKUP
    GXBEAMLOOKUPBEAM="/group/mwasci/pb_lookup/gleam_xx_yy.hdf5"
    export GXBEAMLOOKUPBEAM
else
    echo "Where am i?"
fi

# Create the log directory if it does not exists
if [[ ! -d "${GXLOG}" ]]
then
    mkdir -p "${GXLOG}"
fi

export GXVERSION='3.0.0'

export HOST_CLUSTER=$cluster

export PATH=${PATH}:/group/mwasci/$USER/bin/:"${GXBASE}/bin:${GXBASE}/db"
export PYTHONPATH=$PYTHONPATH:/group/mwasci/$USER/lib/python2.7/site-packages/:~/lib/
export PYTHONPATH=$PYTHONPATH:"${GXBASE}/bin:${GXBASE}/db"

# Add your MWA ASVO key to 'mwa_asvo_api.key'
MWA_ASVO_API_KEY=$(cat "${GXBASE}/mwa_asvo_api.key")
export MWA_ASVO_API_KEY