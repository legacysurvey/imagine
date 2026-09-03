import os
from glob import glob
from astrometry.util.util import Tan, anwcs_t
from astrometry.util.fits import fits_table
import fitsio
import numpy as np

import matplotlib
matplotlib.use('Agg')
import pylab as plt

def table_for_files(*fns):
    T = fits_table()
    T.ra = []
    T.dec = []
    T.crval1 = []
    T.crval2 = []
    T.crpix1 = []
    T.crpix2 = []
    T.cd11 = []
    T.cd12 = []
    T.cd21 = []
    T.cd22 = []
    T.width = []
    T.height = []
    #T.band = []
    T.median_g = []
    T.median_i = []
    T.filename_g = []
    T.brickname = []
    T.ra1 = []
    T.ra2 = []
    T.dec1 = []
    T.dec2 = []
    T.ext = []

    for i,fn in enumerate(fns):
        print('File', fn)
        F = fitsio.FITS(fn)

        fn_i = fn.replace('_g.fit', '_i.fit')
        FI = fitsio.FITS(fn_i)

        for e in range(1, len(F)):
            hdr = F[e].read_header()
            vv = []
            keys = ['crval1', 'crval2', 'crpix1', 'crpix2',
                    'cd1_1', 'cd1_2', 'cd2_1', 'cd2_2']
            for k in keys:
                vv.append(hdr[k.upper()])
            W = hdr['NAXIS1']
            H = hdr['NAXIS2']
            vv.append(W)
            vv.append(H)
            keys.extend(['width', 'height'])
            wcs = Tan(*[float(x) for x in vv])
            rc,dc = wcs.radec_center()
            vv.extend([rc,dc])
            keys.extend(['ra','dec'])
            #keys.append('band')
            #vv.append(hdr['FILTER'].split('.')[0])
            for k,v in zip(keys, vv):
                T.get(k.replace('_','')).append(v)

            T.filename_g.append(os.path.basename(fn))
            T.brickname.append(os.path.basename(fn).replace('_g.fit','') + '_' + '%02i' % e)
            T.ext.append(e)
            
            pix = F[e].read()
            T.median_g.append(np.median(pix.ravel()))

            wcs = anwcs_t(fn, e)
            #print('WCS:', wcs)

            xx = [1,      1, 1, (W+1)/2, W, (W+1)/2, 1,       1]
            yy = [1,(H+1)/2, H,       H, H,       H, H, (H+1)/2]
            ok,rr,dd = wcs.pixelxy2radec(xx, yy)
            # RA wrap
            if rc > 270:
                rr[rr < 90] += 360.
            elif rc < 90:
                rr[rr > 270] -= 360.

            r1 = rr.min()
            r1 = r1 + 360.*(r1 < 0)
            r2 = rr.max()
            r2 = r2 + -360.*(r2 > 360)
            T.ra1.append(r1)
            T.ra2.append(r2)
            T.dec1.append(dd.min())
            T.dec2.append(dd.max())

            hdr_i = FI[e].read_header()
            assert(hdr_i['FILTER'].split('.')[0] == 'i')
            pix = FI[e].read()
            T.median_i.append(np.median(pix.ravel()))
    T.to_np_arrays()
    return T

def main():
    fns = glob('data/pandas/m*_g.fit')
    fns.sort()
    for fn in fns:
        assert(fn.endswith('_g.fit'))

    #fns = fns[:8]
    from astrometry.util.multiproc import multiproc
    from astrometry.util.fits import merge_tables
    mp = multiproc(32)
    TT = mp.map(table_for_files, fns)
    T = merge_tables(TT)
    
    #T = table_for_files(fns)
    T.writeto('pandas.fits')
            
if __name__ == '__main__':
    main()
    
