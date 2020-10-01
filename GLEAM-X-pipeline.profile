#! /bin/bash -l

echo "loading profile"

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