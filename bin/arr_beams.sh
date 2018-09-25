#! /bin/bash

usage()
{
echo "arr_beams.sh [-d dep] [-q queue] [-b beamlist] [-c] [-t] obsnum
  -d dep     : job number for dependency (afterok)
  -q queue   : job queue, default=host-dependent
  -b beamlist: full path to text list of obsids to use to generate beams
  -t         : test. Don't submit job, just make the batch file
               and then return the submission command" 1>&2;
exit 1;
}

# Supercomputer options
if [[ "${HOST:0:4}" == "gala" ]]
then
    computer="galaxy"
    account="mwasci"
    standardq="workq"
    absmem=60
    scratch="/astro"
    group="/group"
#    standardq="gpuq"
#    absmem=30
elif [[ "${HOST:0:4}" == "magn" ]]
then
    computer="magnus"
    account="pawsey0272"
    standardq="workq"
    absmem=60
    scratch="/astro"
    group="/group"
elif [[ "${HOST:0:4}" == "athe" ]]
then
    computer="athena"
    account="pawsey0272"
    standardq="gpuq"
    absmem=30 # Check this
    scratch="/astro"
    group="/group"
fi

#initial variables
base="$scratch/mwasci/$USER/GLEAMX/"
code="$group/mwasci/$USER/GLEAM-X-pipeline/"
queue="-p $standardq"
beamlist=
dep=
tst=

# parse args and set options
while getopts ':tb:d:q:p:' OPTION
do
    case "$OPTION" in
	d)
	    dep=${OPTARG}
	    ;;
	q)
	    queue="-p ${OPTARG}"
	    ;;
	b)
	    beamlist=${OPTARG}
	    ;;
	t)
	    tst=1
	    ;;
	? | : | h)
	    usage
	    ;;
  esac
done

# if beamlist is not specified or an empty file then just print help

if [[ -z ${beamlist} ]] || [[ ! -s ${beamlist} ]] || [[ ! -e ${beamlist} ]]
then
    usage
else
    numbeams=`wc -l ${beamlist} | awk '{print $1}'`
fi

listbase=`basename ${beamlist}`
listbase=${listbase%%.*}

if [[ ! -z ${dep} ]]
then
    depend="--dependency=afterok:${dep}"
fi

# start the real program

script="${code}queue/pbeams_${listbase}.sh"
cat ${code}/bin/pbeams.tmpl | sed -e "s:BASEDIR:${base}:g" \
                                 -e "s:ABSMEM:${absmem}:g" \
                                 -e "s:BEAMLIST:${beamlist}:g" \
                                 -e "s:NUMBEAMS:${numbeams}:g" \
                                 -e "s:HOST:${computer}:g" \
                                 -e "s:STANDARDQ:${standardq}:g" \
                                 -e "s:ACCOUNT:${account}:g" > ${script}

output="${code}queue/logs/pbeams_${listbase}.o%A_%a"
error="${code}queue/logs/pbeams_${listbase}.e%A_%a"

sub="sbatch --output=${output} --error=${error} ${depend} ${queue} ${script}"
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

echo "Submitted ${script} as ${jobid}. Follow progress here:"
echo $output*
echo $error*
