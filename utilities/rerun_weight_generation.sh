#! /bin/bash -l
# A script to regenerate the weight maps for specified obsid and subchan. 
# This was written to run against a set of obsids whose weght maps were
# filled with nans. It does not perform the larger post_imaging set of 
# tasks, and critically relies upon there being an rms map being present. 

set -x

if [[ $# -ne 2  ]]
then
    echo "rerun_weight_generation.sh obsid subchan"
    echo "obsid - the obsid to regenerate the weight map for. It is assumed that the script is invocated from the correct project directory. "
    echo "subchan - the subchan to recreate the weight map for."
    exit 1 
fi


obsid=$1
subchan=$2

if [ ! -d "${obsid}" ]
then
    echo "Directory ${obsid} does not exist. Exiting, "
    exit 1
fi

origdir=$(pwd)

cd "${obsid}" || exit 1

chans=($( pyhead.py -p CHANNELS "${obsid}.metafits" | awk '{print $3}' | sed "s/,/ /g" ))
if [[ ${subchan} == "MFS" ]]
then
    i=0
    j=23
else
    n=${subchan:3}
    i=$((n * 6))
    j=$((i + 5))
fi
cstart=${chans[$i]}
cend=${chans[$j]}

if [[ ! -e "${obsid}_deep-${subchan}-image-pb_warp-XX-beam.fits" ]] || [[ ! -e "${obsid}_deep-${subchan}-image-pb_warp-YY-beam.fits" ]]
then 
   echo "Creating the beam files"
    if [[ -e "${obsid}_deep-${subchan}-image-pb_warp-XX-beam.fits" ]]
    then 
        rm "${obsid}_deep-${subchan}-image-pb_warp-XX-beam.fits"
    fi
if [[ -e "${obsid}_deep-${subchan}-image-pb_warp-XX-beam.fits" ]]
    then 
        rm "${obsid}_deep-${subchan}-image-pb_warp-XX-beam.fits"
    fi

    lookup_beam.py "${obsid}" \
                    "_deep-${subchan}-image-pb_warp.fits" \
                    "${obsid}_deep-${subchan}-image-pb_warp-" \
                    -c "$cstart-$cend"
fi

if [[ -e "${obsid}_deep-${subchan}-image-pb_warp_weight.fits" ]]
then 
    echo "Removing existing weight map"
    rm "${obsid}_deep-${subchan}-image-pb_warp_weight.fits"
fi 

generate_weight_map.py "${obsid}_deep-${subchan}-image-pb_warp-XX-beam.fits" \
                       "${obsid}_deep-${subchan}-image-pb_warp-YY-beam.fits" \
                       "${obsid}_deep-${subchan}-image-pb_warp_rms.fits"

echo "Finished. Changing directory back to ${origdir}"
cd "${origdir}" || exit 1
