from astrometry.util.fits import *
from collections import Counter
import os
import sys
import time

from astrometry.util.util import Tan


T = fits_table('hsc-dr2b.fits')
T.band[:] = 'z'
#T.cut(T.band == 'z')
T.ra1 = np.zeros(len(T))
T.ra2 = np.zeros(len(T))
T.dec1 = np.zeros(len(T))
T.dec2 = np.zeros(len(T))
brickname = []
for i,t in enumerate(T):
    wcs = Tan(*[float(x) for x in
                [t.crval1, t.crval2, t.crpix1, t.crpix2, t.cd1_1, t.cd1_2, t.cd2_1, t.cd2_2,
                 t.width, t.height]])
    midy = (t.height+1)/2.
    midx = (t.width+1)/2.
    rr,dd = wcs.pixelxy2radec([1, t.width], [midy,midy])
    T.ra1[i] = min(rr)
    T.ra2[i] = max(rr)
    rr,dd = wcs.pixelxy2radec([midx,midx], [1, t.height])
    T.dec1[i] = min(dd)
    T.dec2[i] = max(dd)
    parts = t.filename.strip().split('/')
    brickname.append('%s_%s' % (parts[-3], parts[-2]))
T.brickname = np.array(brickname)
T.writeto('hsc-dr2-bricks.fits')

sys.exit(0)

T = fits_table('hsc-dr2.fits')
print(len(T), 'files')
#rds,U = np.unique([(r,d) for r,d in zip(T.ra, T.dec)], return_index=True, axis=0)
rds,U = np.unique(np.vstack((T.ra, T.dec)).T, return_index=True, axis=0)
print(len(rds), 'unique RA,Decs')

print(len(U), U.min(), U.max())

TU = T[U]
TU.has_g = np.zeros(len(TU), bool)
TU.has_r = np.zeros(len(TU), bool)
TU.has_z = np.zeros(len(TU), bool)
for ird,(r,d) in enumerate(rds):
    I = np.flatnonzero((T.ra == r) * (T.dec == d))
    for b in T.band[I]:
        TU.get('has_%s' % b)[ird] = True
TU.filename = np.array([f.replace('HSC-G', 'HSC-Z').replace('HSC-R', 'HSC-Z')
                        for f in TU.filename])
#TU.band[:] = 'z'
TU.writeto('hsc-dr2b.fits')

sys.exit(0)


TT = []
for layer in ['wide', 'dud']:

    Tall = fits_table('hsc-dr2-' + layer + '-index.fits', columns='filter patch tract crval1 crval2 crpix1 crpix2 cd1_1 cd1_2 cd2_1 cd2_2 naxis1 naxis2'.split())
    print(len(Tall), layer)

    Tall.f1 = np.array([f[0] for f in Tall.filter])
    print('filter1:', Counter(Tall.f1))

    for band in ['g','r','z']:
        T = Tall[Tall.f1 == band]
        print(len(T), 'band', band)
        filenames = []
        ras,decs = [],[]
        for i,t in enumerate(T):
            patch = t.patch.strip()
            F = band.upper()
            outdir = ('dr2/' + layer + '/HSC-%s/%i/%s' %
                      (F, t.tract, patch))
            outfn = os.path.join(outdir, 'calexp-HSC-%s-%i-%s.fits' %
                                 (F, t.tract, patch))
            filenames.append(outfn)

            wcs = Tan(t.crval1, t.crval2, t.crpix1, t.crpix2,
                      t.cd1_1, t.cd1_2, t.cd2_1, t.cd2_2,
                      float(t.naxis1), float(t.naxis2))
            r,d = wcs.radec_center()
            ras.append(r)
            decs.append(d)

        T.filename = np.array(filenames)
        T.ra = np.array(ras)
        T.dec = np.array(decs)

        TT.append(T)
T = merge_tables(TT)
T.delete_column('filter')
T.delete_column('patch')
T.delete_column('tract')
T.rename('f1', 'band')
T.rename('naxis1', 'width')
T.rename('naxis2', 'height')
T.writeto('hsc-dr2.fits')

sys.exit(0)

layer = 'wide'
#layer = 'dud'
#f = 'g'
f = 'r'
#f = 'z'
#T.cut(T.filter == f)

T = fits_table('hsc-dr2-' + layer + '-index.fits')
print(len(T), 'wide')
print('filter:', Counter(T.filter))
T.f1 = np.array([f[0] for f in T.filter])
print('filter1:', Counter(T.f1))

T.cut(T.f1 == f)
print(len(T), 'band', f)

# REVERSE
#T.cut(np.arange(len(T)-1, -1, -1))

#https://hsc-release.mtk.nao.ac.jp/archive/filetree/pdr2_wide/deepCoadd-results/HSC-R/9944/1,2/calexp-HSC-R-9944-1,2.fits

for i,t in enumerate(T):
    patch = t.patch.strip()
    F = f.upper()
    url = ('https://hsc-release.mtk.nao.ac.jp/archive/filetree/pdr2_' + layer + '/deepCoadd-results/HSC-%s/%i/%s/calexp-HSC-%s-%i-%s.fits' %
           (F, t.tract, patch, F, t.tract, patch))
    outdir = ('data/hsc/dr2/' + layer + '/HSC-%s/%i/%s' %
              (F, t.tract, patch))
    outfn = os.path.join(outdir, 'calexp-HSC-%s-%i-%s.fits' %
                         (F, t.tract, patch))

    if os.path.exists(outfn):
        cmd = 'fitsverify -q -e %s' % outfn
        print('%i of %i:' % (i+1,len(T)), cmd)
        rtn = os.system(cmd)
        if rtn == 0:
            continue

    try:
        os.makedirs(outdir)
    except:
        pass
    cmd = 'wget --user dstn --password %s -nv --continue %s -O %s' % (os.environ['HSC_PASS'], url, outfn)
    print()
    print('%i of %i:' % (i+1,len(T)), cmd)
    t0 = time.time()
    while True:
        rtn = os.system(cmd)
        if rtn == 0:
            break
        print('Failed:', rtn)
        time.sleep(5)
    t1 = time.time()
    filesize = os.stat(outfn).st_size
    print('Downloaded %.1f MB in %.1f sec = %.1f MB/sec' % (filesize/1e6, t1-t0, filesize/((t1-t0)*1e6)))

