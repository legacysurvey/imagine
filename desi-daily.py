from astrometry.util.fits import text_table_fields, fits_table, merge_tables
import sys
import os
import numpy as np
import fitsio
from glob import glob
import tempfile
from astrometry.libkd.spherematch import tree_build

basedir = 'data/desi-spectro-daily'

def create_tile_kd():
    from astropy.table import Table
    TT = []
    for fn in ['/global/cfs/cdirs/desi/spectro/redux/daily/tiles-daily.csv']:
        t1 = Table.read(fn)
        t1.write('/tmp/t.fits', overwrite=True)
        T = fits_table('/tmp/t.fits')
        TT.append(T)
    T = merge_tables(TT, columns='fillzero')
    T.ra  = T.tilera
    T.dec = T.tiledec

    for i,(prog,faprog) in enumerate(zip(T.program, T.faprgrm)):
        if prog.strip() == '':
            T.program[i] = faprog

    outfn = os.path.join(basedir, 'tiles2.fits')
    T.writeto(outfn)

    kdfn = os.path.join(basedir, 'tiles2.kd.fits')
    cmd = 'startree -i %s -R tilera -D tiledec -PTk -o %s' % (outfn, kdfn)
    os.system(cmd)
    print('Wrote tile kd-tree')

# Create tile kd-tree
if True:
    create_tile_kd(basedir)
    
    # for surv,fn in [('main', '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-main.ecsv'),
    #                 ('sv1',  '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-sv1.ecsv'),
    #                 ('sv2',  '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-sv2.ecsv'),
    #                 ('sv3',  '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-sv3.ecsv'),
    # 

# Create redshift catalog kd-tree
if True:

    allzbest = []

    # Cached files & dates
    for date in ['202310']: #'202110', '202110-missing', '202202', '202302']:
        cachedfn = os.path.join(basedir, 'allzbest-%s.fits' % date)
        print('Reading cached spectra from', cachedfn, '...')
        T = fits_table(cachedfn)
        T.rename('ra',  'target_ra')
        T.rename('dec', 'target_dec')
        allzbest.append(T)

        #T.about()
    #cache_cutoff = '20211100'
    #cache_cutoff = '20220300'
    #cache_cutoff = '20230300'
    cache_cutoff = '20231100'

    print('Finding zbest(redrock) files...')
    
    tiles = glob('/global/cfs/cdirs/desi/spectro/redux/daily/tiles/cumulative/*')
    # sort numerically
    nt = np.array([int(f.split('/')[-1]) for f in tiles])
    I = np.argsort(nt)
    tiles = [tiles[i] for i in I]

    fns = []
    for tile in tiles:
        dates = glob(tile + '/20*')
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

    # tiles = glob('/global/cfs/cdirs/desi/spectro/redux/daily/attic/rerunarchive-20211029/tiles/cumulative/*')
    # for tile in tiles:
    #     dates = glob(tile + '/*')
    #     if len(dates) == 0:
    #         continue
    #     dates.sort()
    #     date = dates[-1]
    #     justdate = os.path.basename(date)
    #     #print('Date:', justdate)
    #     if cache_cutoff is not None:
    #         if justdate <= cache_cutoff:
    #             print('Skipping (cached):', date)
    #             continue
    #     thisfns = glob(date + '/redrock-*.fits')
    #     fns.extend(thisfns)
    #     print('Adding', len(thisfns), 'files from', date)

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
            # Don't cut until the end because other tables are row-aligned!!
            #T.cut(T.targetid >= 0)
            #T.cut(T.npixels > 0)
            #if len(T) == 0:
            #if np.all(T.npixels == 0):
            #    continue
            print(len(T), 'from', fn)
            #'NIGHT', 'EXPID',
            RD = fits_table(fn, hdu=2, columns=['TARGETID','TARGET_RA','TARGET_DEC',
                                                'TILEID', 'FIBER',
                                                'COADD_EXPTIME',])
            rdmap = dict([(t,i) for i,t in enumerate(RD.targetid)])
            I = np.array([rdmap[t] for t in T.targetid])
            RD = RD[I]

            T.target_ra = RD.target_ra
            T.target_dec = RD.target_dec
            #T.night = RD.night
            #T.expid = RD.expid
            T.tileid = RD.tileid
            T.fiber = RD.fiber
            T.coadd_exptime = RD.coadd_exptime

            # TSNR2 values
            cols = ['TSNR2_BGS', 'TSNR2_LRG', 'TSNR2_ELG', 'TSNR2_QSO', 'TSNR2_LYA']
            SNR = fits_table(fn, hdu=4, columns=cols)
            for c in SNR.get_columns():
                T.set(c, SNR.get(c))

            exp = fits_table(fn, hdu=3, columns=['TARGETID', 'MJD', 'FIBERSTATUS'])
            # keep exposures where fibers were not bad
            exp.cut(exp.fiberstatus == 0)
            # update in order of increasing MJD to end up with the max.
            target_maxmjd = {}
            I = np.argsort(exp.mjd)
            for tid,mjd in zip(exp.targetid[I], exp.mjd[I]):
                target_maxmjd[tid] = mjd
            target_minmjd = {}
            # Reverse order for min MJD
            I = I[-1::-1]
            for tid,mjd in zip(exp.targetid[I], exp.mjd[I]):
                target_minmjd[tid] = mjd
            T.minmjd = np.array([target_minmjd.get(tid, 0) for tid in T.targetid])
            T.maxmjd = np.array([target_maxmjd.get(tid, 0) for tid in T.targetid])
            
            for c in ['chi2', 'coeff', 'deltachi2', 'z', 'zerr']:
                T.set(c, T.get(c).astype(np.float32))
            for c in ['ncoeff', 'npixels', 'zwarn']:
                T.set(c, T.get(c).astype(np.int16))

            #T.cut(T.npixels > 0)

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

obsfn = os.path.join(basedir, 'desi-obs.fits')
subcols = ['targetid', 'zwarn', 'npixels', 'tileid', 'fiber',
           'tsnr2_bgs', 'tsnr2_lrg', 'tsnr2_elg', 'tsnr2_qso', 'tsnr2_lya',
           'minmjd', 'maxmjd', 'ra', 'dec', 'coadd_exptime']
allzbest.writeto(obsfn, columns=subcols)
obskd = os.path.join(basedir, 'desi-obs.kd.fits')
create_desi_spectro_kdtree(obsfn, obskd)
