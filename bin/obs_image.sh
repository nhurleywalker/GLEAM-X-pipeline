#! /bin/bash

usage()
{
echo "obs_image.sh [-d dep] [-p project] [-a account] [-z] [-t] obsnum
  -d dep     : job number for dependency (afterok)
  -a account : computing account, default pawsey0272
  -p project : project, (must be specified, no default)
  -z         : Debugging mode: image the CORRECTED_DATA column
                instead of imaging the DATA column
  -t         : test. Don't submit job, just make the batch file
               and then return the submission command
  obsnum     : the obsid to process" 1>&2;
exit 1;
}

# Supercomputer options
if [[ "${HOST:0:4}" == "zeus" ]]
then
    computer="zeus"
    standardq="workq"
    ncpus=28
#    absmem=60
#    standardq="gpuq"
elif [[ "${HOST:0:4}" == "magn" ]]
then
    computer="magnus"
    standardq="workq"
    ncpus=24
#    absmem=60
elif [[ "${HOST:0:4}" == "athe" ]]
then
    computer="athena"
    standardq="gpuq"
#    absmem=30 # Check this
fi

scratch="/astro"
group="/group"

#initial variables
dep=
imscale=
pixscale=
clean=
tst=
debug=
# parse args and set options
while getopts ':tzd:a:p:' OPTION
do
    case "$OPTION" in
	d)
	    dep=${OPTARG}
	    ;;
    a)
        account=${OPTARG}
        ;;
    p)
        project=${OPTARG}
        ;;
    z)
        debug=1
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

queue="-p $standardq"
base="$scratch/mwasci/$USER/$project/"
code="$group/mwasci/$USER/GLEAM-X-pipeline/"

# if obsid is empty then just print help

if [[ -z ${obsnum} ]] || [[ -z $project ]] || [[ ! -d ${base} ]]
then
    usage
fi

if [[ ! -z ${dep} ]]
then
    depend="--dependency=afterok:${dep}"
fi

if [[ -z ${account} ]]
then
    account=pawsey0272
fi

# start the real program

script="${code}queue/image_${obsnum}.sh"
cat ${code}/bin/image.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                 -e "s:BASEDIR:${base}:g" \
                                 -e "s:NCPUS:${ncpus}:g" \
                                 -e "s:HOST:${computer}:g" \
                                 -e "s:STANDARDQ:${standardq}:g" \
                                 -e "s:DEBUG:${debug}:g" \
                                 -e "s:ACCOUNT:${account}:g" > ${script}

output="${code}queue/logs/image_${obsnum}.o%A"
error="${code}queue/logs/image_${obsnum}.e%A"

sub="sbatch --begin=now+15 --output=${output} --error=${error} ${depend} ${queue} ${script}"
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
taskid=1

# rename the err/output files as we now know the jobid
error=`echo ${error} | sed "s/%A/${jobid}/"`
output=`echo ${output} | sed "s/%A/${jobid}/"`

# record submission
track_task.py queue --jobid=${jobid} --taskid=${taskid} --task='image' --submission_time=`date +%s` --batch_file=${script} \
                     --obs_id=${obsnum} --stderr=${error} --stdout=${output}

echo "Submitted ${script} as ${jobid}. Follow progress here:"
echo $output
echo $error

