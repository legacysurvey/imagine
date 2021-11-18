from astrometry.util.fits import text_table_fields, fits_table, merge_tables
import sys
import os
import numpy as np
import fitsio
from glob import glob
import tempfile
from astrometry.libkd.spherematch import tree_build

# Create tile kd-tree
if True:
    from astropy.table import Table
    TT = []
    for surv,fn in [('main', '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-main.ecsv'),
                    ('sv1',  '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-sv1.ecsv'),
                    ('sv2',  '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-sv2.ecsv'),
                    ('sv3',  '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-sv3.ecsv'),
               ]:
        t1 = Table.read(fn)
        t1.write('/tmp/t.fits', overwrite=True)
        T = fits_table('/tmp/t.fits')
        #T.about()
        T.survey = np.array([surv] * len(T))
        TT.append(T)
    T = merge_tables(TT, columns='fillzero')
    T.tilera  = T.ra
    T.tiledec = T.dec
    #     ts = '%06i' % tileid
    #     fn = 'data/desi-tiles/%s/fiberassign-%s.fits.gz' % (ts[:3], ts)
    #     T.found_tile[itile] = True
    # T.cut(T.found_tile)

    T.writeto('data/desi-spectro-daily/tiles2.fits')    
    
    cmd = 'startree -i data/desi-spectro-daily/tiles2.fits -R tilera -D tiledec -PTk -o data/desi-spectro-daily/tiles2.kd.fits'
    os.system(cmd)

    print('Wrote tile kd-tree')

# Create redshift catalog kd-tree
if True:

    allzbest = []

    # Cached file & date
    cachedfn = 'data/allzbest-%s.fits' % '202110'
    print('Reading cached spectra from', cachedfn, '...')
    T = fits_table(cachedfn)
    T.rename('ra',  'target_ra')
    T.rename('dec', 'target_dec')
    allzbest.append(T)
    cache_cutoff = '20211100'

    print('Finding zbest files...')
    
    tiles = glob('/global/cfs/cdirs/desi/spectro/redux/daily/tiles/cumulative/*')
    fns = []
    for tile in tiles:
        dates = glob(tile + '/*')
        if len(dates) == 0:
            continue
        dates.sort()
        date = dates[-1]
        justdate = os.path.basename(date)
        #print('Date:', justdate)
        if cache_cutoff is not None:
            if justdate <= cache_cutoff:
                print('Skipping (cached):', date)
                continue
        fns.extend(glob(date + '/zbest-*.fits'))

    tiles = glob('/global/cfs/cdirs/desi/spectro/redux/daily/attic/rerunarchive-20211029/tiles/cumulative/*')
    for tile in tiles:
        dates = glob(tile + '/*')
        if len(dates) == 0:
            continue
        dates.sort()
        date = dates[-1]
        justdate = os.path.basename(date)
        #print('Date:', justdate)
        if cache_cutoff is not None:
            if justdate <= cache_cutoff:
                print('Skipping (cached):', date)
                continue
        fns.extend(glob(date + '/redrock-*.fits'))

    # Are we producing a cache file?
    caching = False
    if caching:
        cachedate = '20211100'
        cachedate_name = '202110'
        # print('Dates:')
        # for fn in fns:
        #     print('  ', fn)
        #     print('  date', os.path.basename(os.path.dirname(fn)))
        #     print('  date before cachedate:', os.path.basename(os.path.dirname(fn)) <= cachedate)
        fns = [fn for fn in fns if os.path.basename(os.path.dirname(fn)) <= cachedate]
        
    if True:
        for fn in fns:
            T = fits_table(fn)
            T.cut(T.targetid >= 0)
            T.cut(T.npixels > 0)
            if len(T) == 0:
                continue
            print(len(T), 'from', fn)
            #'NIGHT', 'EXPID',
            RD = fits_table(fn, hdu=2, columns=['TARGETID','TARGET_RA','TARGET_DEC',
                                                'TILEID', 'FIBER'])
            rdmap = dict([(t,i) for i,t in enumerate(RD.targetid)])
            I = np.array([rdmap[t] for t in T.targetid])
            RD = RD[I]

            T.target_ra = RD.target_ra
            T.target_dec = RD.target_dec
            #T.night = RD.night
            #T.expid = RD.expid
            T.tileid = RD.tileid
            T.fiber = RD.fiber
            allzbest.append(T)
    
    allzbest = merge_tables(allzbest, columns='fillzero')
    allzbest.cut(allzbest.npixels > 0)
    allzbest.rename('target_ra', 'ra')
    allzbest.rename('target_dec', 'dec')
    if caching:
        allzbest.writeto('data/allzbest-%s.fits' % cachedate_name)
        sys.exit(0)
        
    allzbest.writeto('data/allzbest.fits')

outfn = 'data/allzbest.kd.fits'

with tempfile.TemporaryDirectory() as tempdir:
    
    sfn = os.path.join(tempdir, 'allzbest.kd.fits')
    fitsfn = 'data/allzbest.fits'

    cmd = 'startree -i %s -PTk -o %s' % (fitsfn, sfn)
    os.system(cmd)
    
    T = fits_table(sfn, columns=['targetid'])
    ekd = tree_build(np.atleast_2d(T.targetid.copy()).T.astype(np.uint64),
                     bbox=False, split=True)
    ekd.set_name('targetid')

    efn = os.path.join(tempdir, 'ekd.fits')
    ekd.write(efn)

    # merge
    cmd = 'fitsgetext -i %s -o %s/ekd-%%02i -a' % (efn, tempdir)
    print(cmd)
    rtn = os.system(cmd)
    assert(rtn == 0)

    cmd = 'cat %s %s/ekd-0[12345] > %s' % (sfn, tempdir, outfn)
    print(cmd)
    rtn = os.system(cmd)
    assert(rtn == 0)
