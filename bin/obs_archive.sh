#! /bin/bash

usage()
{
echo "obs_archive.sh [-d dep] [-p project] [-a account] [-u user] [-e endpoint] [-r remote_directory] [-t] obsnum

Archives the processed data products onto the data central archive system. By default traffic is routed through a nimbus instance, requiring a public ssh key to first be added to list of authorized keys. Data Central runs ownCloud, and at the moment easiest way through is a `davfs2` mount. Consult Natasha or Tim. 

  -d dep      : job number for dependency (afterok)
  -a account  : computing account, default pawsey0272
  -p project  : project, (must be specified, no default)
  -u user     : user name of system to archive to (default: 'ubuntu')
  -e endpoint : hostname to copy the archive data to (default: '146.118.69.100')
  -r remote   : remote directory to copy files to (default: '/mnt/dav/GLEAM-X/public/Archived_Obsids)
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  obsnum      : the obsid to process" 1>&2;
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
tst=
endpoint='146.118.69.100' #HOST is already used as a keyword in other script
user='ubuntu'
remote='/mnt/dav/GLEAM-X/public/Archived_Obsids'
# parse args and set options
while getopts ':td:a:p:u:h:r:' OPTION
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
	u)
        user=${OPTARG}
        ;;
    h)
        endpoint=${OPTARG}
        ;;
    r)
        remote=${OPTARG}
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
script="${code}queue/archive_${obsnum}.sh"
cat ${code}/bin/archive.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                 -e "s:BASEDIR:${base}:g" \
                                 -e "s:NCPUS:${ncpus}:g" \
                                 -e "s:HOST:${computer}:g" \
                                 -e "s:STANDARDQ:${standardq}:g" \
                                 -e "s:ACCOUNT:${account}:g" \
                                 -e "s:ENDUSER:${user}:g" \
                                 -e "s:ENDPOINT:${endpoint}:g" \
                                 -e "s:REMOTE:${remote}:g"> ${script}

output="${code}queue/logs/archive_${obsnum}.o%A"
error="${code}queue/logs/archive_${obsnum}.e%A"

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

echo "Submitted ${script} as ${jobid} . Follow progress here:"
echo $output
echo $error

