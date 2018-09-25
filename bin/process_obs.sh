#! /bin/bash

grb=$1

if [[ ! ${grb} ]]
then
    echo "process_obs.sh obsid"
    exit 1
fi

# determine the obsid and name of the calibrator associated with this GRB
res=(`sqlite3 db/MWA-GRB.sqlite "SELECT obs_id, obsname FROM observation WHERE grb=\"${grb}\" AND calibration" | tr "|" " "`)
calid=${res[0]}
calname=${res[1]}

solutions=`ls processing/${calid}/${calid}*solutions.bin 2>/dev/null`
if [[ $? ]]
then
    # the solutions don't exist so we must make them
    echo "Making calibration solutions"
    # setting calname means that we chain onto calculating the calibration solution
    ./bin/obs_dl.sh ${calid} 0 0 ${calname}
    exit $?
fi

echo "Solutions exist, proceccing target observations"
obsids=(`sqlite3 db/MWA-GRB.sqlite "SELECT obs_id FROM observation WHERE grb=\"${grb}\" AND NOT calibration"`)
depend=0
for id in obsids
do
    # do all the processing for this obsid
    # supplying the calibration id means that we chain onto applying the cal solution and then imaging
    dep=(`./bin/obs_dl.sh ${id} ${depend} ${calid} 0`)
    if [[ $? ]]
    then
	depend=${dep[3]}
    else
	exit $?
    fi
done
    
