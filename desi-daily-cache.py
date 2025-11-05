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
#if True:
if False:
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
    #for date in []:#'202110', '202110-missing', '202202', '202302']:
    for date in ['202310']:
        cachedfn = os.path.join(basedir, 'allzbest-%s.fits' % date)
        print('Reading cached spectra from', cachedfn, '...')
        T = fits_table(cachedfn)
        T.rename('ra',  'target_ra')
        T.rename('dec', 'target_dec')
        allzbest.append(T)
    #cache_cutoff = '20211100'
    #cache_cutoff = '20220300'
    #cache_cutoff = '20230300'
    cache_cutoff = '20231100'
    #cache_cutoff = '19000000'

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

        # HACK!!!
        #if len(thisfns) > 0:
        #    continue

        if len(thisfns) == 0:
            thisfns = glob(date + '/zbest-*.fits')
        
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
    caching = True
    if caching:
        #cachedate = '20211100'
        #cachedate_name = '202110'
        #cachedate = '20231100'
        #cachedate_name = '202310'
        cachedate = '20251100'
        cachedate_name = '202510'
        # print('Dates:')
        # for fn in fns:
        #     print('  ', fn)
        #     print('  date', os.path.basename(os.path.dirname(fn)))
        #     print('  date before cachedate:', os.path.basename(os.path.dirname(fn)) <= cachedate)
        fns = [fn for fn in fns if os.path.basename(os.path.dirname(fn)) <= cachedate]
        
    if True:
        for fn in fns:

            #if fn != '/global/cfs/cdirs/desi/spectro/redux/daily/tiles/cumulative/325/20210406/zbest-2-325-thru20210406.fits':
            #    continue
            
            T = fits_table(fn)
            #if not np.any((T.targetid >= 0) * (T.npixels > 0)):
            #if not np.any(T.npixels > 0):
            #    continue
            if len(T) == 0:
                continue
            print(len(T), 'from', fn)

            # Older data model?
            is_zbest = os.path.basename(fn).startswith('zbest-')

            extra_cols = []
            if not is_zbest:
                extra_cols.append('COADD_EXPTIME')
            # The other HDUs (aside from EXP_FIBERMAP) are row-matched.
            RD = fits_table(fn, hdu=2, columns=['TARGETID','TARGET_RA','TARGET_DEC',
                                                'TILEID', 'FIBER',] + extra_cols)
            if is_zbest:
                # Ugh, this is per-exposure
                tidmap = dict([(tid,i) for i,tid in enumerate(RD.targetid)])
                I = np.array([tidmap[tid] for tid in T.targetid])
                T.target_ra = RD.target_ra[I]
                T.target_dec = RD.target_dec[I]
                T.tileid = RD.tileid[I]
                T.fiber = RD.fiber[I]
            else:
                T.target_ra = RD.target_ra
                T.target_dec = RD.target_dec
                #T.night = RD.night
                #T.expid = RD.expid
                T.tileid = RD.tileid
                T.fiber = RD.fiber
                T.coadd_exptime = RD.coadd_exptime

            # TSNR2 values
            cols = ['TSNR2_BGS', 'TSNR2_LRG', 'TSNR2_ELG', 'TSNR2_QSO', 'TSNR2_LYA']
            if is_zbest:
                coadd_fn = fn.replace('zbest-', 'coadd-')
                F = fitsio.FITS(coadd_fn)
                hdu = F['scores'].get_info()['hdunum']
                SNR = fits_table(coadd_fn, hdu=hdu-1) #, columns=cols)
            else:
                SNR = fits_table(fn, hdu=4, columns=cols)
            snrcols = SNR.get_columns()
            for c in cols:
                c = c.lower()
                if c in snrcols:
                    v = SNR.get(c)
                else:
                    # Some zbest tiles (tileid > 80k) don't have all/any of the TSNR2 fields.
                    v = np.zeros(len(SNR), np.float32)
                T.set(c, v)

            # exposure x target table
            extra_columns = []
            if is_zbest:
                # UGH tile 80254 and others lack extime!!
                hdu = 2
                t0 = fits_table(fn, hdu=hdu, rows=[0])
                if 'exptime' in t0.get_columns():
                    extra_columns.append('EXPTIME')
            else:
                hdu = 3
            exp = fits_table(fn, hdu=hdu,
                             columns=['TARGETID', 'MJD', 'FIBERSTATUS'] + extra_columns)
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

            if 'exptime' in exp.get_columns():
                # Sum to get coadd_exptime
                target_exptime = {}
                for tid,t in zip(exp.targetid[I], exp.exptime[I]):
                    target_exptime[tid] = target_exptime.get(tid, 0) + t
                T.coadd_exptime = np.array([target_exptime.get(tid, 0) for tid in T.targetid])

            #T.cut((T.targetid >= 0) * (T.npixels > 0))
            #T.cut(T.npixels > 0)

            for c in ['chi2', 'coeff', 'deltachi2', 'z', 'zerr']:
                T.set(c, T.get(c).astype(np.float32))

            for c in ['ncoeff', 'npixels', 'zwarn']:
                v = T.get(c)
                vv = v.astype(np.int16)
                assert(np.all(v == vv))
                T.set(c, vv)

            allzbest.append(T)
    
    allzbest = merge_tables(allzbest, columns='fillzero')
    #allzbest.cut(allzbest.npixels > 0)
    allzbest.rename('target_ra', 'ra')
    allzbest.rename('target_dec', 'dec')
    if caching:
        outfn = os.path.join(basedir, 'allzbest-%s.fits' % cachedate_name)
        allzbest.writeto(outfn)
        print('Wrote', outfn)
        #allzbest.writeto(os.path.join(basedir, 'allzbest-%s-zbest.fits' % cachedate_name))
        sys.exit(0)

    fitsfn = os.path.join(basedir, 'allzbest.fits')
    allzbest.writeto(fitsfn)

fitsfn = os.path.join(basedir, 'allzbest.fits')
outfn = os.path.join(basedir, 'allzbest.kd.fits')

from desi_spectro_kdtree import create_desi_spectro_kdtree

create_desi_spectro_kdtree(fitsfn, outfn)

