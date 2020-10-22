#!/usr/bin/env python
"""Some of the cleaned component models have the majority of their pixels presenting with values on the order of 1e-20, which have been introduced from the multiscale clean. This makes
it impossible to compress efficiently. 

Setting these to a constant number (i.e. zero) will let the compression work with extreme efficiency.
"""
from __future__ import print_function

__author__ = ["Tim Galvin",
              "Natasha Hurley-Walker"]

import numpy as np
from astropy.io import fits
from argparse import ArgumentParser

def clip_components(
    comp_file, write_out=True, clip_level=1e-10, summary=True
):
    """Accepts a cleaned component model and will clip out pixels between certain values, setting them to zero.

    Args:
        comp_file (str): Input cleaned component model to reset values to
        write_out (bool, optional): Creates a new file, with the `-clip.fits` suffix. Defaults to True.
        clip_level (float, optional): Pixels ub range (-clip_level, clip_level) are set to zero. Defaults to 1e-10.
        summary (bool, optional): Outputs a summary of the actions performed. Defaults to True
    """
    assert comp_file[-5:] == '.fits', 'Expected a `fits` files, but recieved {0}'.format(comp_file)
    
    comp_data = fits.getdata(comp_file)
    comp_head = fits.getheader(comp_file)

    copy_data = comp_data
    mask = np.abs(copy_data) < clip_level

    copy_data[mask] = 0

    if summary:
        print('Processed {0}'.format(comp_file))
        print('Clipping range is +/- {0}'.format(clip_level))
        print('{0} pixels in input model'.format(np.prod(comp_data.shape)))
        print('{0} pixels being set to zero'.format(np.sum(mask)))
        print('{0} pixels retained their original value'.format(np.sum(~mask)))

    if write_out:
        out_file = comp_file.replace('.fits', '-clip.fits')
        
        if summary:
            print('Writing to {0}'.format(out_file))

        fits.writeto(
            out_file,
            copy_data,
            comp_head,
            overwrite=True
        )



if __name__ == '__main__':
    parser = ArgumentParser(description='Clip pixels in a clean component model that appear to be meaningless (and prevent efficient compress!)')
    parser.add_argument('components', help='The clean comonent model in fits format')
    parser.add_argument('-c','--clip-level', default=1e-10, type=float, help='Pixels in the range +/- clip_level are set to zero')
    parser.add_argument('-q','--quiet', default=False, action='store_true', help='Suppressess output')
    parser.add_argument('-d', '--dry-run', default=False, action='store_true', help='Prevents any new files from being created')

    args = parser.parse_args()

    print(args)

    clip_components(
        args.components,
        write_out = not args.dry_run,
        clip_level=args.clip_level,
        summary = not args.quiet
    )
    