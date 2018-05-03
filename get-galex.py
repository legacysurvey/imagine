import os
import sys
from astrometry.util.fits import *
from astrometry.util.multiproc import multiproc

#http://galex.stsci.edu/data/GR6/pipe/02-vsn/50270-AIS_270/d/01-main/0001-img/07-try/AIS_270_sg28-xd-mcat.fits.gz
# 'GR6/pipe/01-vsn/03000-MISDR1_24278_0266/d/01-main/0001-img/07-try/MISDR1_24278_0266-xd-mcat.fits.gz',

def _get_one(X):
    (tile, sv, path, band) = X
    if sv == -999:
        fnpart = '%s-%sd-intbgsub.fits.gz' % (tile, band)
    else:
        fnpart = '%s_sg%02i-%sd-intbgsub.fits.gz' % (tile, sv, band)
    fn = os.path.join('data','galex', tile, fnpart)
    if os.path.exists(fn):
        print('Exists:', fn)
        return
    dirnm = os.path.join('data', 'galex', tile)
    if not os.path.exists(dirnm):
        try:
            os.makedirs(dirnm)
        except:
            pass
    path = '/'.join(path.strip().split('/')[:-1])
    path += '/' + fnpart
    
    url = 'http://galex.stsci.edu/data/' + path
    cmd = 'wget -nv -O %s.tmp %s && mv %s.tmp %s' % (fn, url, fn, fn)
    print(cmd)
    rtn = os.system(cmd)
    #if rtn:
    #    sys.exit(-1)

if __name__ == '__main__':
    #T = fits_table('data/galex/galex_dstn.fit')
    T = fits_table('data/galex/galex-images.fits')
    args = []
    for tile,sv,path in zip(T.tilename, T.subvis, T.filenpath):
        tile = tile.strip()
        for band in ['n','f']:
            args.append((tile, sv, path, band))

    mp = multiproc(8)
    mp.map(_get_one, args)

    T.have_n = np.zeros(len(T), bool)
    T.have_f = np.zeros(len(T), bool)

    for i,(tile,sv,path) in enumerate(zip(T.tilename, T.subvis, T.filenpath)):
        tile = tile.strip()
        band = 'n'
        if sv == -999:
            fnpart = '%s-%sd-intbgsub.fits.gz' % (tile, band)
        else:
            fnpart = '%s_sg%02i-%sd-intbgsub.fits.gz' % (tile, sv, band)
        fn = os.path.join('data','galex', tile, fnpart)
        T.have_n[i] = os.path.exists(fn)
        band = 'f'
        if sv == -999:
            fnpart = '%s-%sd-intbgsub.fits.gz' % (tile, band)
        else:
            fnpart = '%s_sg%02i-%sd-intbgsub.fits.gz' % (tile, sv, band)
        fn = os.path.join('data','galex', tile, fnpart)
        T.have_f[i] = os.path.exists(fn)

    T.writeto('data/galex/galex-image-2.fits')
