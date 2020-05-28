## Complementing GLEAM-X sky model with MARCO

Included in this directory is `skymodel_allsky_only_alpha.fits`. Areas of the sky visible from the MRO but not covered by GLEAM are filled in using  [MARCO](https://github.com/johnsmorgan/marco). For details on how this file is generated, see [here](https://github.com/johnsmorgan/marco/tree/master/gleam_sky_model).

NVSS_SUMSS_psfcal.fits was produced by selecting from NVSS:

sources that met all of these criteria:
 - No other NVSS source within a 3' radius
 - peak flux density at 1400 MHz > 52 mJy (scaling 250 mJy from 150 MHz with alpha = -0.7)
 - int / peak > 1.2
 - Dec >= -40

and from SUMSS:
 - No other SUMSS source within a 3' radius
 - peak flux density at 843 MHz > 75 mJy (scaling 250 mJy from 150 MHz with alpha = -0.7)
 - int / peak > 1.2
 - Dec < -40

I then renamed the columns to be more standard and concatenated the two tables together.
