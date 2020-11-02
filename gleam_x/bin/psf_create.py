#!/usr/bin/env python

from __future__ import print_function, division

__author__ = ("Paul Hancock", "Natasha Hurley-Walker")
__date__ = "09/02/2016"

#image manipulation 
from scipy.interpolate import griddata
import healpy as hp
import numpy as np
import scipy
import scipy.stats
import math
import os, sys, re
import psutil

from astropy.io.votable import writeto as writetoVO
from astropy.table import Table, Column
from astropy.io.votable import parse_single_table
from astropy.io import fits
from astropy import wcs

from argparse import ArgumentParser


# read table and filter out the dodgy sources
def read_table(inputfile):
    """
    """
    hdu = fits.open(inputfile)
    # table = hdu[1].data
    return Table(hdu[1].data)


@np.vectorize
def unwrap(ang):
    r = ang - 2*np.pi*(ang//(2*np.pi))
    if r>np.pi:
        r -= 2*np.pi
    return r


# add a HEALPix pixel column to the table
def radec2hpix(ra, dec, order=4):
    phi = unwrap(np.radians(ra))
    theta = unwrap(np.radians(90-dec))
    return hp.ang2pix(2**order, theta, phi)


def get_neighbours(pix, order=4, nn=1):
    neighbours = set([pix])
    for i in range(nn):
        for p in neighbours.copy():
            theta,phi = hp.pix2ang(2**order,p)
            neighbours|= set(hp.pixelfunc.get_all_neighbours(2**order,theta,phi))
            neighbours -=set([-1])
    return list(neighbours)


def get_h_neighbours(pix, order=4, nn=1):
    neighbours = set([pix])
    for i in range (nn):
        for p in neighbours.copy():
            theta,phi = hp.pix2ang(2**order,p)
            nb = list(set(hp.pixelfunc.get_all_neighbours(2**order, theta, phi)) - set([-1]))
            nb_theta, nb_phi = zip(*[hp.pix2ang(2**order, a) for a in nb])
            mask = np.where(abs(nb_phi-phi) < 0.1)[0]
            neighbours |= set(nb[i] for i in mask)
    return list(neighbours)


def main():
    """
    """

    parser = ArgumentParser()
    parser.add_argument('--input', dest="input", default=None,
                      help="Input fits table to characterise.")
    parser.add_argument('--stepsize', dest="stepsize", default=1,
                      help="Specify step size in degrees (default = 1 deg)")
    parser.add_argument('--output', dest="output", default=None,
                      help="Output psf fits file -- default is based on input table")
    # parser.add_argument('--bmaj', dest="bmaj", default=None, type=float,
    #                   help="Original restoring beam major axis (default = search for matching fits file)")
    # parser.add_argument('--bmin', dest="bmin", default=None, type=float,
    #                   help="Original restoring beam minor axis (default = search for matching fits file)")
    parser.add_argument('--order', dest="order", default=4, type=int,
                      help='Healpix order')
    parser.add_argument('--zeropa', dest='zeropa', action='store_true', default=False,
                      help='For the psf position angle to be identically zero')
    # parser.add_argument("--reference-image", "-r",
    #                     dest="reference_image", type=str, default=None)
    options = parser.parse_args()

    # read and filter the data
    print('read and filter')
    table = read_table(options.input)

    print('add hpx column')
    # add a new column to the data - healpix pixel number
    ncol = Column(radec2hpix(table['ra'], table['dec'], order=options.order), 'hpx' )
    table.add_column(ncol)

    print('averaging')
    # iterate over the unique pixels in the data

    pixels = set()
    for p in set(table['hpx']):
        pixels |= set( get_neighbours(p, order=options.order, nn=2) )
    pix_dict = {}
    missed = []
    for p in pixels:
        # find all the neighbours
        nb = get_neighbours(p,order=options.order)
        src_mask = np.where(np.in1d(table['hpx'], nb))[0]
        if sum(src_mask)<5:
            missed.append(p)
        # calculate the median values of a/b/pa
        blur = np.mean((table[src_mask]['a']*table[src_mask]['b'])/(table[src_mask]["psf_a"]*table[src_mask]["psf_b"]))
        a = np.mean(table[src_mask]['a'])/3600.
        b = np.mean(table[src_mask]['b'])/3600.
        pa = np.mean(table[src_mask]['pa']) if not options.zeropa else 0
        # blur = np.mean(table[src_mask]['a']*table[src_mask]['b']*np.cos(np.radians(latitude-table[src_mask]['dec']))/(bmaj*bmin*3600*3600))
        
        nsrc = len(src_mask)
        pix_dict[p] = (a,b,pa,blur,nsrc)

    for m in missed:
        nb = get_h_neighbours(p,order=options.order, nn=2)
        src_mask = np.where(np.in1d(table['hpx'], nb))[0]
        # if sum(src_mask)<5:
        #     print m, src_mask, 'still missed'
        #     continue
        # else:
        #     print "fixed up",m
        ## calculate the median values of a/b/pa
        blur = np.mean((table[src_mask]['a']*table[src_mask]['b'])/(table[src_mask]["psf_a"]*table[src_mask]["psf_b"]))
        a = np.mean(table[src_mask]['a'])/3600.
        b = np.mean(table[src_mask]['b'])/3600.
        pa = np.mean(table[src_mask]['pa']) if not options.zeropa else 0
        # blur = np.mean(table[src_mask]['a']*table[src_mask]['b']*np.cos(np.radians(latitude-table[src_mask]['dec']))/(bmaj*bmin*3600*3600))
        nsrc = len(src_mask)
        pix_dict[p] = (a,b,pa,blur,nsrc)


    print('making car grid')
    # make a grid for our cartesian projection
    nx = int(360//options.stepsize)
    ny = int(180//options.stepsize)
    car = np.empty((4,ny,nx),dtype=np.float32)*np.nan
    
    # make an image header from scratch
    hd={}
    hd['SIMPLE']=True
    hd['BITPIX']=-32
    hd['NAXIS']=2
    hd['NAXIS1']=360
    hd['NAXIS2']=180
    hd['EQUINOX']=2000
    hd['RADESYS']='ICRS'
    hd['CDELT1']=options.stepsize
    hd['CRPIX1']= nx/2.0
    hd['CRVAL1']=180.0
    hd['CTYPE1']='RA---CAR'
    hd['CUNIT1']='deg'
    hd['CDELT2']=options.stepsize
    hd['CRVAL2']=0.0
    hd['CRPIX2']=ny/2.0
    hd['CTYPE2']='DEC--CAR'
    hd['CUNIT2']='deg'
    header = fits.Header.fromkeys(hd.keys())
    for k in hd.keys():
        header[k]=hd[k]

    # create the correct WCS
    mywcs = wcs.WCS(header)
    print("projecting hpx->car")
    # for each pixel in the cartesian grid, seek the value from the hpix grid
    for j in range(ny):
        for i in range(nx):
            ra, dec = mywcs.all_pix2world(i,j,0)
            if np.all(np.isfinite([ra ,dec])):
                p = radec2hpix(ra,dec,order=options.order)
            else:
                p=-1
            if p in pix_dict.keys():
                car[:,j,i]=pix_dict[p][:4]
            else:
                car[:,j,i]=[np.nan, np.nan, np.nan, np.nan]
    header['CTYPE3'] = ('Beam',"0=a,1=b,2=pa (degrees),3=blur")
    if options.output is None:
        # Try some common extensions
        options.output = options.input.replace('_comp_psfcat.fits','_psf.fits')
        # Last-ditch, call it psf.fits
        if options.output == options.input:
            options.output == "psf.fits"
    hdulist = fits.HDUList(fits.PrimaryHDU(header=header, data=car))
    hdulist.writeto(options.output, overwrite=True)
    print("wrote {}".format(options.output))



if __name__== "__main__":
    main()
