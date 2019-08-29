#! /bin/bash

#! /bin/bash

usage()
{
echo "process.sh [-p project] [-q queue] obsnum
  -q queue   : job queue, default=workq
  -p project : project, (must be specified, no default)
  obsnum     : the obsid to process" 1>&2;
exit 1;
}

scratch="/astro"
group="/group"

# Supercomputer options
if [[ "${HOST:0:4}" == "zeus" ]]
then
    standardq="workq"
elif [[ "${HOST:0:4}" == "magn" ]]
then
    standardq="workq"
elif [[ "${HOST:0:4}" == "athe" ]]
then
    standardq="gpuq"
fi

# parse args and set options
while getopts ':p:q:' OPTION
do
    case "$OPTION" in
    q)
        standardq="${OPTARG}"
        ;;
    p)
        project=${OPTARG}
        ;;
    ? | : | h)
        usage
        ;;
  esac
done
# set the obsid to be the first non option
shift  "$(($OPTIND -1))"
obsnum=$1

if [[ -z ${obsnum} ]] || [[ -z $project ]]
then
    usage
fi

base="$scratch/mwasci/$USER/$project/"
code="$group/mwasci/$USER/GLEAM-X-pipeline/"

script="${code}queue/process_${obsnum}.sh"

if [[ -d $scratch/mwasci/$USER/$project/$obsnum/$obsnum.ms ]]
then

    cat ${code}/bin/chain.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                     -e "s:PROJECT:${project}:g" \
                                     -e "s:QUEUE:${standardq}:g" \
                                      > ${script}

    chmod +x ${script}
    ${script}
fi
