#! /bin/bash
usage()
{
echo "obs_infield_cal.sh [-d dep] [-q queue] [-c catalog] [-t] obsnum
  -d dep     : job number for dependency (afterok)
  -q queue   : job queue, default=gpuq
  -c catalog : catalogue file to use.
  -t         : test. Don't submit job, just make the batch file
               and then return the submission command
  obsnum     : the obsid to process" 1>&2;
exit 1;
}

# Supercomputer options
if [[ "${HOST:0:4}" == "gala" ]]
then
    computer="galaxy"
    account="mwasci"
    standardq="workq"
    absmem=60
#    standardq="gpuq"
#    absmem=30
elif [[ "${HOST:0:4}" == "magn" ]]
then
    computer="magnus"
    account="pawsey0272"
    standardq="workq"
    absmem=60
elif [[ "${HOST:0:4}" == "athe" ]]
then
    computer="athena"
    account="pawsey0272"
    standardq="gpuq"
    absmem=30 # Check this
fi

#initialize as empty
dep=
queue='-p gpuq'
catfile=
tst=

# parse args and set options
while getopts ':td:q:c:' OPTION
do
    case "$OPTION" in
	d)
	    dep=${OPTARG}
	    ;;

	c)
	    catfile=${OPTARG}
	    ;;
	q)
	    queue="-p ${OPTARG}"
	    ;;
	t)
	    tst=1
	    ;;
	? | : | h)
	    usage
	    ;;
  esac
done
# set the obsid to be the first non option
shift  "$(($OPTIND -1))"
obsnum=$1

set -u

# if obsid is empty then just pring help
if [[ -z ${obsnum} ]]
then
    usage
fi

if [[ -z ${catfile} ]]
then
    catfile="/group/mwa/software/MWA_Tools/MWA_Tools/catalogues/GLEAM_EGC.fits"
fi
if [[ ! -e ${catfile} ]]
then
    echo "Catalogue file not found:"
    echo ${catfile}
    exit 1
fi

# set dependency
if [[ ! -z ${dep} ]]
then
    dep="--dependency=afterok:${dep}"
fi

# start the real program
base='/astro/mwasci/phancock/D0009/'

script="${base}queue/infield_cal_${obsnum}.sh"
cat ${base}/bin/infield_cal.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                       -e "s:BASEDIR:${base}:g" \
                                       -e "s:CATFILE:${catfile}:g"  > ${script}

output="${base}queue/logs/infield_cal_${obsnum}.o%A"
error="${base}queue/logs/infield_cal_${obsnum}.e%A"

sub="sbatch --begin=now+15 --output=${output} --error=${error} ${dep} ${queue} ${script}"

if [[ ! -z ${tst} ]]
then
    echo "script is ${script}"
    echo "submit via:"
    echo "${sub}"
    exit 0
fi

# submit job
jobid=($(${sub}))
jobid=${jobid[3]}
taskid=0

# rename the err/output files as we now know the jobid
error=`echo ${error} | sed "s/%A/${jobid}/"`
output=`echo ${output} | sed "s/%A/${jobid}/"`

# record submission
python ${base}/bin/track_task.py queue --jobid=${jobid} --taskid=${taskid} --task='infield_cal' --submission_time=`date +%s` --batch_file=${script} \
                     --obs_id=${obsnum} --stderr=${error} --stdout=${output}

echo "Submitted ${script} as ${jobid}"
