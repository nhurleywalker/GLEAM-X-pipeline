#! /bin/bash

usage()
{
echo "obs_copy_run.sh [-p project] [-a assigned] [-t] -o list_of_observations.txt

Given a set of obsid folders that have been processed initially, this script will assess whether a valid ao-solutions file exists. If it does not it is assumed that the calibration failed, and solutions should be copied over from one that is close in time.

  -p project  : project, (must be specified, no default)
  -t          : just run the check and present the obsids this would apply to, don't submit (default: False)
  -a assigned : output text file that maps an obsid to a correspond calibration obsid (default: assigned_solutions.txt)
  -o obslist  : the list of obsids to process" 1>&2;
exit 1;
}

test=1
calids="assigned_solutions.txt"

# parse args and set options
while getopts ':tp:o:a:' OPTION
do
    case "$OPTION" in
    p)
        project="${OPTARG}" ;;
	o)
	    obslist="${OPTARG}" ;;
    t)
        test=0 ;;
    a)
        calids="${OPTARG}" ;;
    ? | : | h)
            usage ;;
  esac
done

# Escape if usage is not correct
if [[ -z ${obslist} ]] || [[ ! -s ${obslist} ]] || [[ ! -e ${obslist} ]] || [[ -z $project ]]
then
    usage
fi

work="${GXSCRATCH}/${project}"
cd "${work}" || exit

if [[ ! -f ${GXCONTAINER} ]]
then
    echo "GXCONTAINER is currently set to ${GXCONTAINER}, and can not be found, but is required. Exiting."
    exit 1
fi

${GXCONTAINER} check_assign_solutions.py -t 0.25 assign "${obslist}" -n -c "${calids}"

for obsid in $(cat "${obslist}")
do 
    # Ensure the grep below is locked onto the first column
    calid=$(cat "${calids}" | grep -E "${obsid} [0-9]{10}" | cut -d ' ' -f2)
    if [[ "${obsid}" != "${calid}" ]]
    then
        echo "${obsid} does not equal ${calid}"
        if [[ $test -eq 1 ]]
        then
            dep=($(obs_apply_cal.sh -p "${project}" -c ${calid} $obsnum))
            depend=${dep[3]}
            echo "apply-cal jobid: $depend"

            dep=($(obs_uvflag.sh -p "${project}" -d $depend $obsnum))
            depend=${dep[3]}
            echo "uv-flag jobid: $depend"

            dep=($(obs_image.sh -p "${project}" -d $depend $obsnum))
            depend=${dep[3]}
            echo "imaging jobid: $depend"

            dep=($(obs_binoc.sh -p "${project}" -d $depend $obsnum))
            depend=${dep[3]}
            echo "binoc jobid: $depend"

            dep=($(obs_postimage.sh -p "${project}" -d $depend $obsnum))
            depend=${dep[3]}
            echo "post-processing jobid: $depend"

            dep=($(obs_archive.sh -p "${project}" -d $depend $obsnum))
            depend=${dep[3]}
            echo "archive jobid: $depend"
        fi
    fi
done