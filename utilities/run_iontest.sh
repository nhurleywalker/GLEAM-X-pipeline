#! /bin/bash -l
# A script to run just the iontest component of autocal.tmpl
# During a large processing run TJG was not activating this 
# routine. This script will create the solutions file across
# if the phasemap.png file is not detected. 
# Although a solutions file has already been applied, the
# relative statistics across the three time periods should 
# still be valid. 


set -x

if [[ $# -ne 2  ]]
then
    echo "run_iontest.sh basedir oblist"
    echo "project - the project code that contains the collection of obsids to process. This is combined with the GXSCRATCH variable"
    echo "obslist - the text file containing observation IDs to process, separated by new lines"
    exit 1 
fi

project=$1
basedir="${GXSCRATCH}/${project}"

cd "${basedir}" || exit 1

obslist=$2
taskid=${SLURM_ARRAY_TASK_ID}

numfiles=$(wc -l "${obslist}" | awk '{print $1}')

if [[ $taskid -gt $numfiles ]]
then
    echo "Task id ${taskid} larger than ${numfiles}. Nothing to do. Exiting. "
    exit 0
fi

obsnum=$(sed -n -e "${SLURM_ARRAY_TASK_ID}"p "${obslist}")

function test_fail {
if [[ $1 != 0 ]]
then
    exit "$1"
fi
}

echo "Project code is: ${project}"
echo "Base directory is: ${basedir}"
echo "Observation list is: ${obslist}"
echo "Obsid is: ${obsnum}"

# MWA beam information
MWAPATH="${GXMWAPB}"

obsdir="${basedir}/${obsnum}"
cd "${obsdir}" ||  exit 1

metafits="${obsnum}.metafits"
if [[ ! -e ${metafits} ]] || [[ ! -s ${metafits} ]]
then
    wget -O "${metafits}" http://ws.mwatelescope.org/metadata/fits?obs_id=${obsnum}
    test_fail $?
fi

chan=$( pyhead.py -p CENTCHAN "$metafits" | awk '{print $3}' )
refant=127

# GLEAM-X sky model
catfile="${GXBASE}/models/GGSM.fits"

# MWA beam information
MWAPATH="${GXMWAPB}"
cores=${GXNCPUS}

# Minimum baseline of 75 lambda (=250m at 88 MHz) for calibration
minuv=75
RA=$( pyhead.py -p RA "$metafits" | awk '{print $3}' )
Dec=$( pyhead.py -p DEC "$metafits" | awk '{print $3}' )
chan=$( pyhead.py -p CENTCHAN "$metafits" | awk '{print $3}' )
# uv range for calibration based on GLEAM-based sky model
# Calibrate takes a maximum uv range in metres
# Calculate min uvw in metres
minuvm=$(echo "234 * ${minuv} / ${chan}" | bc -l)
# In wavelengths, maximum 128T baseline at 200MHz was 1667 lambda long
# 300/1.28 * 1667 = 390000
# Calculate max uvw in metres
maxuvm=$(echo "390000 / (${chan} + 11)" | bc -l)

# Interval for ionospheric triage (in time steps)
# Typically we have 2-minute observations which have been averaged to 4s
# So in total they contain 30 time steps
# Do do useful ionospheric differencing we need to compare the start and the end
ts=10

if [[ ! -e "${obsnum}_local_gleam_model.txt" ]]
then
    crop_catalogue.py --ra="${RA}" --dec="${Dec}" --radius=30 --top-bright=200 --metafits="${metafits}" \
                        --catalogue="${catfile}" --fluxcol=S_200 --plot "${obsnum}_local_gleam_model.png" \
                        --output "${obsnum}_cropped_catalogue.fits"
    vo2model.py --catalogue="${obsnum}_cropped_catalogue.fits" --point --output="${obsnum}_local_gleam_model.txt" \
                --racol=RAJ2000 --decol=DEJ2000 --acol=a --bcol=b --pacol=pa --fluxcol=S_200 --alphacol=alpha
fi
calmodel="${obsnum}_local_gleam_model.txt"

if [[ ! -e "${obsnum}_phasemap.png" ]]
then
    echo "Performing ionospheric triage. "
    # Ionospheric triage
    solutions="${obsnum}_${calmodel%%.txt}_solutions_ts${ts}.bin"
    # Remove duplicate obsnum
    solutions="${solutions/${obsnum}_${obsnum}_/${obsnum}_}"
    
    calibrate \
            -t ${ts} \
            -j ${cores} \
            -absmem ${GXMEMORY} \
            -m "${calmodel}" \
            -minuv ${minuvm} \
            -maxuv ${maxuvm} \
            -applybeam -mwa-path "${MWAPATH}" \
            "${obsnum}.ms" \
            "${solutions}"
    
    echo "Ionospheric calibration finished. Creating plots and statistics. "
    aocal_plot.py --refant="${refant}" --amp_max=2 "${solutions}"
    aocal_diff.py --metafits="${metafits}" --names "${solutions}"
    iono_update.py --ionocsv "${obsnum}_ionodiff.csv"
fi