#! /bin/bash

#! /bin/bash

usage()
{
echo "process.sh [-p project] [-a account] obsnum
  -a account : computing account, default pawsey0272
  -p project : project, (must be specified, no default)
  obsnum     : the obsid to process" 1>&2;
exit 1;
}

pipeuser=$(whoami)

scratch="/astro"
group="/group"

# parse args and set options
while getopts ':p:a:' OPTION
do
    case "$OPTION" in
    a)
        account=${OPTARG}
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


base="$scratch/mwasci/$pipeuser/$project/"
code="$group/mwasci/$pipeuser/GLEAM-X-pipeline/"
script="${code}queue/process_${obsnum}.sh"

echo $base
echo $code
echo $script

if [[ -z ${obsnum} ]] || [[ -z $project ]]
then
    usage
fi

if [[ -z ${account} ]]
then
    account=pawsey0272
fi


cat ${code}/bin/chain.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                 -e "s:PROJECT:${project}:g" \
                                 -e "s:ACCOUNT:${account}:g" \
                                  > ${script}

chmod +x ${script}
${script}
