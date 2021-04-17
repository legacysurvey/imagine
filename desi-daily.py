from astrometry.util.fits import text_table_fields
import os
import numpy as np
import fitsio
from glob import glob

# FIXME -- Should instead use
# /global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-sv3.ecsv

#/global/cfs/cdirs/desi/spectro/redux/daily/tiles.csv
T = text_table_fields('/global/cfs/cdirs/desi/spectro/redux/daily/tiles.csv')
#T.writeto('data/desi-spectro-daily/tiles.fits')
T.tilera  = np.zeros(len(T), np.float64)
T.tiledec = np.zeros(len(T), np.float64)
T.found_tile = np.zeros(len(T), bool)
for itile,(tileid,survey) in enumerate(zip(T.tileid, T.survey)):

    if survey.strip() == 'unknown':
        continue
    
    ts = '%06i' % tileid
    fn = 'data/desi-tiles/%s/fiberassign-%s.fits.gz' % (ts[:3], ts)

    # pat = '/global/cfs/cdirs/desi/spectro/redux/daily/tiles/%i/*/spectra-*.fits' % tileid
    # fns = glob(pat)
    # if len(fns) == 0:
    #     print('Failed to find file for', pat)
    #     continue
    # fn = fns[0]
    print('Reading', fn)
    F = fitsio.FITS(fn)
    hdr = F[0].read_header()
    ra,dec = hdr['TILERA'], hdr['TILEDEC']
    T.tilera [itile] = ra
    T.tiledec[itile] = dec
    T.found_tile[itile] = True

T.cut(T.found_tile)
T.writeto('data/desi-spectro-daily/tiles2.fits')    

cmd = 'startree -i data/desi-spectro-daily/tiles2.fits -R tilera -D tiledec -PTk -o data/desi-spectro-daily/tiles2.kd.fits'
os.system(cmd)
