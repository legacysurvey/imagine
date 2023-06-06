from astrometry.util.fits import text_table_fields, fits_table, merge_tables
import sys
import os
import numpy as np
import fitsio
from glob import glob
import tempfile
from astrometry.libkd.spherematch import tree_build

basedir = 'data/desi-spectro-daily'

# Create tile kd-tree
if True:
    from astropy.table import Table
    TT = []
    # for surv,fn in [('main', '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-main.ecsv'),
    #                 ('sv1',  '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-sv1.ecsv'),
    #                 ('sv2',  '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-sv2.ecsv'),
    #                 ('sv3',  '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-sv3.ecsv'),
    # 
    for fn in ['/global/cfs/cdirs/desi/spectro/redux/daily/tiles-daily.csv']:
        t1 = Table.read(fn)
        t1.write('/tmp/t.fits', overwrite=True)
        T = fits_table('/tmp/t.fits')
        #T.about()
        #T.survey = np.array([surv] * len(T))
        TT.append(T)
    T = merge_tables(TT, columns='fillzero')
    #T.tilera  = T.ra
    #T.tiledec = T.dec
    T.ra  = T.tilera
    T.dec = T.tiledec

    for i,(prog,faprog) in enumerate(zip(T.program, T.faprgrm)):
        if prog.strip() == '':
            T.program[i] = faprog
    
    #     ts = '%06i' % tileid
    #     fn = 'data/desi-tiles/%s/fiberassign-%s.fits.gz' % (ts[:3], ts)
    #     T.found_tile[itile] = True
    # T.cut(T.found_tile)

    outfn = os.path.join(basedir, 'tiles2.fits')
    T.writeto(outfn)

    kdfn = os.path.join(basedir, 'tiles2.kd.fits')
    cmd = 'startree -i %s -R tilera -D tiledec -PTk -o %s' % (outfn, kdfn)
    os.system(cmd)
    print('Wrote tile kd-tree')

# Create redshift catalog kd-tree
if True:

    allzbest = []

    # Cached files & dates
    for date in ['202110', '202110-missing', '202202', '202302']:
        cachedfn = os.path.join(basedir, 'allzbest-%s.fits' % date)
        print('Reading cached spectra from', cachedfn, '...')
        T = fits_table(cachedfn)
        T.rename('ra',  'target_ra')
        T.rename('dec', 'target_dec')
        allzbest.append(T)
    #cache_cutoff = '20211100'
    #cache_cutoff = '20220300'
    cache_cutoff = '20230300'

    print('Finding zbest(redrock) files...')
    
    tiles = glob('/global/cfs/cdirs/desi/spectro/redux/daily/tiles/cumulative/*')
    # sort numerically
    nt = np.array([int(f.split('/')[-1]) for f in tiles])
    I = np.argsort(nt)
    tiles = [tiles[i] for i in I]

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
        #fns.extend(glob(date + '/zbest-*.fits'))
        thisfns = glob(date + '/redrock-*.fits')
        thisfns.sort()
        fns.extend(thisfns)
        print('Adding', len(thisfns), 'files from', date)

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
        thisfns = glob(date + '/redrock-*.fits')
        fns.extend(thisfns)
        print('Adding', len(thisfns), 'files from', date)

    # Are we producing a cache file?
    caching = False
    if caching:
        #cachedate = '20211100'
        #cachedate_name = '202110'
        cachedate = '20220300'
        cachedate_name = '202202'
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
        allzbest.writeto(os.path.join(basedir, 'allzbest-%s.fits' % cachedate_name))
        sys.exit(0)

    fitsfn = os.path.join(basedir, 'allzbest.fits')
    allzbest.writeto(fitsfn)

fitsfn = os.path.join(basedir, 'allzbest.fits')
outfn = os.path.join(basedir, 'allzbest.kd.fits')

from desi_spectro_kdtree import create_desi_spectro_kdtree

create_desi_spectro_kdtree(fitsfn, outfn)

