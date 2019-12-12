#! /bin/bash

usage()
{
echo "obs_rfifind.sh [-d dep] [-p project] [-q queue] [-t] obsnum
  -d dep     : job number for dependency (afterok)
  -p project : project, (must be specified, no default)
  -t         : test. Don't submit job, just make the batch file
               and then return the submission command
  obsnum     : the obsid to process" 1>&2;
exit 1;
}
# No options for queue - has to be run on gpuq
#  -q queue   : job queue, default=workq
# Supercomputer options
if [[ "${HOST:0:4}" == "zeus" ]]
then
    computer="zeus"
# mwasci is SLAMMED -- used pawsey0272
    account="pawsey0272"
#    account="mwasci"
#    standardq="workq"
    ncpus=28
#    absmem=60
#    standardq="gpuq"
elif [[ "${HOST:0:4}" == "magn" ]]
then
    computer="magnus"
    account="pawsey0272"
#    standardq="workq"
    ncpus=24
#    absmem=60
elif [[ "${HOST:0:4}" == "athe" ]]
then
    computer="athena"
    account="pawsey0272"
#    standardq="gpuq"
#    absmem=30 # Check this
fi

scratch="/astro"
group="/group"

#initial variables
#queue="-p $standardq"
dep=
imscale=
pixscale=
clean=
tst=
# parse args and set options
while getopts ':td:p:' OPTION
do
    case "$OPTION" in
	d)
	    dep=${OPTARG}
	    ;;
    p)
        project=${OPTARG}
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

# We need to run everything on Zeus so that RADIANCE can use the gpuq
# And other things can be dependent on it

# 0) Run RADIANCE on the standard images
output="${code}queue/logs/raddeep_${obsnum}.o%A"
error="${code}queue/logs/raddeep_${obsnum}.e%A"
script="${code}queue/raddeep_${obsnum}.sh"
cat ${code}/bin/radiance.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                 -e "s:BASEDIR:${base}:g" \
                                 -e "s:OPTION:deep:g" \
                                 -e "s:HOST:zeus:g" \
                                 -e "s:STANDARDQ:gpuq:g" \
                                 -e "s:ACCOUNT:${account}:g" \
                                 -e "s:OUTPUT:${output}:g"\
                                 -e "s:ERROR:${error}:g" > ${script}

dep=($(sbatch -M zeus --begin=now+15 --output=${output} --error=${error} ${depend} ${queue} ${script}))
depend=${dep[3]}
echo "Radiance1 jobid: $depend"

# rename the err/output files as we now know the jobid
jobid=$depend
error=`echo ${error} | sed "s/%A/${jobid}/"`
output=`echo ${output} | sed "s/%A/${jobid}/"`

# record submission
taskid=1
track_task.py queue --jobid=${jobid} --taskid=${taskid} --task='rfifind' --submission_time=`date +%s` --batch_file=${script} \
                     --obs_id=${obsnum} --stderr=${error} --stdout=${output}

echo "Submitted ${script} as ${jobid}. Follow progress here:"
echo $output
echo $error

# 1) the RFI-finding imaging
script="${code}queue/rfifind_${obsnum}.sh"
output="${code}queue/logs/rfifind_${obsnum}.o%A"
error="${code}queue/logs/rfifind_${obsnum}.e%A"
# The script that will run on the results: radiance
cat ${code}/bin/rfifind.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                 -e "s:BASEDIR:${base}:g" \
                                 -e "s:NCPUS:${ncpus}:g" \
                                 -e "s:HOST:zeus:g" \
                                 -e "s:STANDARDQ:workq:g" \
                                 -e "s:ACCOUNT:${account}:g" \
                                 -e "s:OUTPUT:${output}:g"\
                                 -e "s:ERROR:${error}:g" > ${script}

dep=($(sbatch -M zeus --begin=now+15 --output=${output} --error=${error} --dependency=afterok:${depend} ${queue} ${script}))
depend=${dep[3]}
error=`echo ${error} | sed "s/%A/${depend}/"`
output=`echo ${output} | sed "s/%A/${depend}/"`
echo "RFI-Find jobid: $depend"
echo "Submitted ${script} as ${depend}. Follow progress here:"
echo $output
echo $error

# 2) another run of RADIANCE to test the RFI imaging images
script="${code}queue/radrfi_${obsnum}.sh"
output="${code}queue/logs/radrfi_${obsnum}.o%A"
error="${code}queue/logs/radrfi_${obsnum}.e%A"
cat ${code}/bin/radiance.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                 -e "s:BASEDIR:${base}:g" \
                                 -e "s:OPTION:rfi:g" \
                                 -e "s:HOST:zeus:g" \
                                 -e "s:STANDARDQ:gpuq:g" \
                                 -e "s:ACCOUNT:${account}:g" \
                                 -e "s:OUTPUT:${output}:g"\
                                 -e "s:ERROR:${error}:g" > ${script}

dep=($(sbatch -M zeus --begin=now+15 --output=${output} --error=${error} --dependency=afterok:${depend} ${queue} ${script}))
depend=${dep[3]}
error=`echo ${error} | sed "s/%A/${depend}/"`
output=`echo ${output} | sed "s/%A/${depend}/"`
echo "Radiance2 jobid: $depend"
echo "Submitted ${script} as ${depend}. Follow progress here:"
echo $output
echo $error

# 3) flagging the sub-bands depending on the output from RADIANCE
script="${code}queue/flagsubs_${obsnum}.sh"
output="${code}queue/logs/flagsubs_${obsnum}.o%A"
error="${code}queue/logs/flagsubs_${obsnum}.e%A"
cat ${code}/bin/flagsubs.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                 -e "s:BASEDIR:${base}:g" \
                                 -e "s:HOST:zeus:g" \
                                 -e "s:STANDARDQ:workq:g" \
                                 -e "s:ACCOUNT:${account}:g" \
                                 -e "s:OUTPUT:${output}:g"\
                                 -e "s:ERROR:${error}:g" > ${script}

dep=($(sbatch -M zeus --begin=now+15 --output=${output} --error=${error} --dependency=afterok:${depend} ${queue} ${script}))
depend=${dep[3]}
error=`echo ${error} | sed "s/%A/${depend}/"`
output=`echo ${output} | sed "s/%A/${depend}/"`
echo "Flagging jobid: $depend"
echo "Submitted ${script} as ${depend}. Follow progress here:"
echo $output
echo $error

#if [[ ! -z ${tst} ]]
#then
#    echo "script is ${script}"
#    echo "submit via:"
#    echo "${sub}"
#    exit 0
#fi
#    
## submit job
#jobid=($(${sub}))
#jobid=${jobid[3]}
#taskid=1

