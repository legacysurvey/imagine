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
    if not os.path.exists(fn):
        print('TILE NOT FOUND:', fn)
        continue
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



# Create redshift catalog kd-tree


dirs = glob('/global/cfs/cdirs/desi/spectro/redux/daily/tiles/cumulative/*')
dirs.sort()

allzbest = []

for dirnm in dirs:
    dates = glob('%s/*' % dirnm)
    dates.sort()
    if len(dates) < 1:
        print('???', dirnm)
        continue
    # take the last one!
    dirnm = dates[-1]
    fns = glob('%s/zbest-*.fits' % dirnm)
    fns.sort()
    for fn in fns:
        T = fits_table(fn)
        T.cut(T.targetid >= 0)
        T.cut(T.npixels > 0)
        if len(T) == 0:
            continue
        print(len(T), 'from', fn)
        RD = fits_table(fn, hdu=2, columns=['TARGETID','TARGET_RA','TARGET_DEC'])
        rdmap = dict([(t,(r,d)) for t,r,d in zip(RD.targetid, RD.target_ra, RD.target_dec)])
        rd = np.array([rdmap[t] for t in T.targetid])
        T.target_ra  = rd[:,0]
        T.target_dec = rd[:,1]
        allzbest.append(T)

allzbest = merge_tables(allzbest)
allzbest.writeto('data/allzbest.fits')

#cmd = 'startree -i data/allzbest.fits -R target_ra -D target_dec -PTk -o data/allzbest.kd.fits'
#os.system(cmd)

T = allzbest
#T = fits_table('data/allzbest.fits')
T.cut(T.npixels > 0)
T.rename('target_ra', 'ra')
T.rename('target_dec', 'dec')
names = []
for spectype,subtype,zwarn,z,zerr in zip(T.spectype, T.subtype, T.zwarn, T.z, T.zerr):
    spectype = spectype.strip()
    name = spectype
    sub = subtype
    if sub is not None:
        sub = sub.strip()
        if len(sub) > 0:
            name = name + ':%s'%sub
    if spectype.lower in ['galaxy', 'qso']:
        #name += ' %.3f &pm; %.3f' % (z, zerr)
        name += ' %.3f' % (z)
    if zwarn > 0:
        name += ' Zwarn=0x%x' % zwarn
    names.append(name)
T.name = np.array(names)
T.writeto('data/allzbest2.fits')

cmd = 'startree -i data/allzbest2.fits -PTk -o data/allzbest.kd.fits'
os.system(cmd)

