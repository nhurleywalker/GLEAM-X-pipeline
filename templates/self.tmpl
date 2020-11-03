#! /bin/bash -l
#SBATCH --export=NONE
#SBATCH -M HOST
#SBATCH -p STANDARDQ
#SBATCH --account=ACCOUNT
#SBATCH --time=12:00:00
#SBATCH --nodes=1
TASKLINE

pipeuser=PIPEUSER

source /group/mwasci/$pipeuser/GLEAM-X-pipeline/GLEAM-X-pipeline.profile

function test_fail {
if [[ $1 != 0 ]]
then
    cd ${base}
    track_task.py fail --jobid=${SLURM_JOBID} --taskid=1 --finish_time=`date +%s`
    exit $1
fi
}

# Set version number
version=3.0 # First GLEAM-X pipeline data reduction April 2018
absmem=ABSMEM
obsnum=OBSNUM
datadir=DATADIR
# WSClean suffixes for subchannels and MFS
subchans="0000 0001 0002 0003"
# Minimum baseline of 75 lambda (=250m at 88 MHz) for self-calibration
minuv=75
# Depth of cleaning for initial images
tsigma=3

# Number of cores
cores=`grep -P '^core id\t' /proc/cpuinfo  | wc -l`

# Update database
track_task.py start --jobid=${SLURM_JOBID} --taskid=1 --start_time=`date +%s`

datadir=${datadir}/${obsnum}
cd ${datadir}

metafits=`ls -t ${obsnum}*metafits* | head -1`

# Set up telescope-configuration-dependent options
if [[ $obsnum -lt 1151402936 ]] ; then
    telescope="MWA128T"
    basescale=1.1
    imsize=4000
    robust=-1.0
elif [[ $obsnum -ge 1151402936 ]] && [[ $obsnum -lt 1191580576 ]] ; then
    telescope="MWAHEX"
    basescale=2.0
    imsize=2000
    robust=-2.0
elif [[ $obsnum -ge 1191580576 ]] ; then
    telescope="MWALB"
    basescale=0.6
    imsize=8000
    robust=0.0
fi

# Set up channel-dependent options
chan=`pyhead.py -p CENTCHAN ${metafits} | awk '{print $3}'`
bandwidth=`pyhead.py -p BANDWDTH ${metafits} | awk '{print $3}'`
centfreq=`pyhead.py -p FREQCENT ${metafits} | awk '{print $3}'`
chans=`pyhead.py -p CHANNELS ${metafits} | awk '{print $3}' | sed "s/,/ /g"`
chans=($chans)
    # Pixel scale
scale=`echo "$basescale / $chan" | bc -l` # At least 4 pix per synth beam for each channel
    # Naming convention for output files
lowfreq=`echo "$centfreq $bandwidth" | awk '{printf("%00d\n",$1-($2/2.)+0.5)}'`
highfreq=`echo "$centfreq $bandwidth" | awk '{printf("%00d\n",$1+($2/2.)+0.5)}'`
freqrange="${lowfreq}-${highfreq}"

# Set up position-dependent options
RA=`pyhead.py -p RA $metafits | awk '{print $3}'`
Dec=`pyhead.py -p Dec $metafits | awk '{print $3}'`

# Calculate min uvw in metres
minuvm=`echo "234 * $minuv / $chan" | bc -l`

# Check whether the phase centre has already changed
current=`chgcentre ${obsnum}.ms`
if [[ $current == *"shift"* ]]
then
    echo "Detected that this measurement set has already had its phase centre changed. Not shifting."
else
    # Determine whether to shift the pointing centre to be more optimally-centred on the peak of the primary beam sensitivity
    coords=`python /group/mwasci/$pipeuser/GLEAM-X-pipeline/bin/calc_pointing.py --metafits=${metafits}`
    echo "Optimally shifting co-ordinates of measurement set to $coords, with zenith shiftback."
    chgcentre ${obsnum}.ms $coords
    # Now shift the pointing centre to point straight up, which approximates minw without making the phase centre rattle around
    chgcentre -zenith -shiftback ${obsnum}.ms
fi

# Create a template image that has the same WCS as our eventual WSClean image
if [[ ! -e ${obsnum}_template.fits ]]
then
    wsclean -mgain 1.0 \
        -nmiter 1 \
        -niter 0 \
        -name ${obsnum}_template \
        -size ${imsize} ${imsize} \
        -scale ${scale:0:8} \
        -pol XX \
        -data-column CORRECTED_DATA \
        -channel-range 4 5 \
        -interval 14 15 \
        -nwlayers ${cores} \
        $obsnum.ms
    rm ${obsnum}_template-dirty.fits
    mv ${obsnum}_template-image.fits ${obsnum}_template.fits
fi

# Hardcoding John's PB script location for now
# Also hardcoding creating four sub-band beams
pols="XX XXi XY XYi YX YXi YY YYi"

for n in {0..3}
do
    i=$((n * 6))
    cstart=${chans[$i]}
    j=$((i + 5))
    cend=${chans[$j]}
    if [[ ! -e ${obsnum}_000${n}-${pol}-beam.fits ]]
    then
        python /group/mwasci/nhurleywalker/mwa_pb_lookup/lookup_jones.py ${obsnum} _template.fits ${obsnum}_000${n}- -c $cstart-$cend --wsclean_names --beam_path /group/mwasci/pb_lookup/gleam_jones.hdf5
    fi
    for pol in $pols
    do
# For WSClean
        ln -s ${obsnum}_000${n}-${pol}-beam.fits ${obsnum}_initial-000${n}-beam-${pol}.fits
# For PBCorrect
# requires bash 4.0+ to convert quickly to lower-case
        if [[ ${pol:2:1} != "i" ]]
        then
            ln -s ${obsnum}_000${n}-${pol}-beam.fits ${obsnum}_beam-000${n}-${pol,,}r.fits
        else
            ln -s ${obsnum}_000${n}-${pol}-beam.fits ${obsnum}_beam-000${n}-${pol,,}.fits
        fi
    done
done

# Initial clean
if [[ ! -e ${obsnum}_initial-MFS-XX-image.fits ]]
then

module load singularity
singularity exec -B /astro/mwasci/phancock -B /pawsey  -B "$PWD"  /group/mwasci/phancock/images/wsclean_2.9.2.img bash -c \
"wsclean -j $cores \
        -name ${obsnum}_initial \
        -size ${imsize} ${imsize} \
        -nmiter 1 \
        -niter 40000 \
        -threshold ${tsigma} \
        -pol XX,YY,YX,XY \
        -join-polarizations \
        -weight briggs ${robust} \
        -scale ${scale:0:8} \
        -mgain 0.85 \
        -channels-out 4 \
        -no-mf-weighting \
        -join-channels \
        ${obsnum}.ms"
fi

# Self-cal -- using the now-populated MODEL column
if [[ ! -e ${obsnum}_initial-0000-XX-image.fits ]]
then
    echo "Initial image did not generate! Something wrong with WSClean?"
    test_fail $?
fi

# Old school self-cal with polarisation taken into account
if [[ ! -d unused ]]
then
    mkdir unused
fi
for subchan in $subchans
do
# Make a primary-beam corrected model, for use NOW in calibrating
    pbcorrect ${obsnum}_initial-$subchan model.fits ${obsnum}_beam-$subchan ${obsnum}_initcor-${subchan}
# Set Q, U, V to zero
    mv ${obsnum}_initcor-${subchan}-Q.fits unused/
    mv ${obsnum}_initcor-${subchan}-U.fits unused/
    mv ${obsnum}_initcor-${subchan}-V.fits unused/
    # "Uncorrect" the beam
    pbcorrect -uncorrect ${obsnum}_initunc-${subchan} model.fits ${obsnum}_beam-${subchan} ${obsnum}_initcor-${subchan}
done

singularity exec -B /astro/mwasci/phancock -B /pawsey  -B "$PWD"  /group/mwasci/phancock/images/wsclean_2.9.2.img bash -c \
"wsclean -predict \
    -name ${obsnum}_initunc \
    -size ${imsize} ${imsize} \
    -pol xx,yy,xy,yx \
    -weight briggs -1.0 \
    -scale ${scale:0:8} \
    -channels-out 4 \
    ${obsnum}.ms"

calibrate -j ${cores} -minuv $minuvm ${obsnum}.ms ${obsnum}_self_solutions.bin | tee calibrate.log
aocal_plot.py --refant=127 ${obsnum}_self_solutions.bin
flaggedchans=`grep "gains to NaN" calibrate.log | awk '{printf("%03d\n",$2)}' | sort | uniq | wc -l`

if [[ $flaggedchans -gt 200 || ! -s ${obsnum}_self_solutions.bin ]]
then
    echo "More than a third of the channels were flagged!"
    echo "Do not apply these calibration solutions."
    mv ${obsnum}_self_solutions.bin ${obsnum}_self_solutions.bad
fi

track_task.py finish --jobid=${SLURM_JOBID} --taskid=1 --finish_time=`date +%s`
