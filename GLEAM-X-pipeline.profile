#! /bin/bash -l

echo "loading profile"
# TODOs:
# Test calling scripts of (after optparse to argparse or urllib2 to requests)
#       - calc_pointing,py
#      - crop_catalogue.py
#      - new_fk5_template.py
#      - vo2model.py
#      - check_src_fov.py
#     - generate_beam_list.py
#     - import_observation_from_db.py
# remove urllib2 from:
#     - iono_update.py
# Need to update track_task.py
#     - needs to contain the connection information
# Set up alias terms for the singularity containers called throughout the pipeline?
# Remove the mwapy.pb from:
#     - beam_value_at_radec.py
#          - made pb_lookup a python module to replace this. Waiting for QA from JM. 


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
    export GXABSMEM=120
    export GXMEMORY=110
    export GXNCPUS=28
    export GXTASKLINE="#SBATCH --ntasks=${GXNCPUS}"
    export GXLOG="${GXBASE}/queue/logs"
    export GXFMODELS="/group/mwasci/code/anoko/mwa-reduce/models"
    export GXTRACK='track'

elif [[ "${cluster}" == "magnus" ]]
then
    echo "Magnus!"
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
    export GXTRACK='track'
else
    echo "Where am i? Apparently ${cluster}"
    exit 1
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