from astrometry.util.fits import *
from astrometry.util.util import Tan
import fitsio
from glob import glob
import matplotlib
matplotlib.use('Agg')
import pylab as plt

hsc = fits_table()
hsc.filename = []
hsc.band = []
wcsvals = ['crval1','crval2','crpix1','crpix2','cd1_1','cd1_2','cd2_1','cd2_2']
for c in wcsvals:
    hsc.set(c, [])
hsc.width = []
hsc.height = []
hsc.ra = []
hsc.dec = []

# data/niji/9814/8,7/MBQ1/deepCoadd_calexp_9814_8,7_MBQ1_hsc_rings_v1_u_miyatake_mbq1_413_mask_nocenter_cv2_step3_20260412T173512Z.fits
# data/niji/9814/8,7/MBQ1/deepCoadd_calexp_9814_8,7_MBQ1_hsc_rings_v1_u_miyatake_mbq1_465_mask_nocenter_cv2_step3_20260414T021820Z.fits
# data/niji/9814/8,7/MBQ1/deepCoadd_calexp_9814_8,7_MBQ1_hsc_rings_v1_u_miyatake_mbq1_490_mask_nocenter_cv2_step3_20260414T021458Z.fits

bands = ['413', '439', '465', '490']

for band in bands:
    pat = '/global/cfs/cdirs/cosmo/webapp/viewer-dev/data/niji/*/*/*/deepCoadd_calexp_*_mbq1_%s_*.fits' % band
    fns = glob(pat)
    print('Band', band, ':', len(fns), 'files')

    for fn in fns:
        hdr = fitsio.read_header(fn, ext=1)
        wcs = Tan(hdr)
        r,d = wcs.radec_center()

        hsc.ra.append(r)
        hsc.dec.append(d)
        for c in wcsvals:
            hsc.get(c).append(hdr.get(c.upper()))
        hsc.width.append(hdr['NAXIS1'])
        hsc.height.append(hdr['NAXIS2'])
        hsc.band.append(band)
        parts = fn.split('/')
        path = '/'.join(parts[-4:])
        print(path)
        hsc.filename.append(path)

hsc.to_np_arrays()
hsc.writeto('niji.fits')

T = fits_table('niji.fits')

T.brickname = np.array(['_'.join(fn.split('/')[0:2]) for fn in T.filename])

# bricks = set()
# I = []
# for i,b in enumerate(T.brickname):
#     if b in bricks:
#         continue
#     bricks.add(b)

bricks,I = np.unique(T.brickname, return_index=True)

brickbands = dict([(b,[]) for b in bricks])
for brick,band in zip(T.brickname, T.band):
    brickbands[brick].append(band)
T.cut(I)

T.ra1 = np.zeros(len(T))
T.ra2 = np.zeros(len(T))
T.dec1 = np.zeros(len(T))
T.dec2 = np.zeros(len(T))
for band in bands:
    T.set('has_%s' % band, np.zeros(len(T), bool))

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

    for band in bands:
        T.get('has_%s' % band)[i] = (band in brickbands[t.brickname])
T.writeto('niji-bricks.fits')
