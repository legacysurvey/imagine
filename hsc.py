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

for band in 'grz':
    pat = '/global/project/projectdirs/cosmo/work/hsc/dr1/wide/deepCoadd/HSC-%s/*/*/calexp-*.fits' % (band.upper())
    #pat = 'HSC-%s/*/*/calexp-*.fits' % (band.upper())
    fns = glob(pat)
    print('Band', band, ':', len(fns), 'files')

    pat2 = '/global/project/projectdirs/cosmo/work/hsc/dr1/deep/deepCoadd/HSC-%s/*/*/calexp-*.fits' % (band.upper())
    fns2 = glob(pat2)
    print('Band', band, ':', len(fns2), 'files from deep')
    fns = fns + fns2

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
        path = '/'.join(parts[-7:])
        print(path)
        hsc.filename.append(path)

hsc.to_np_arrays()
hsc.writeto('hsc.fits')

T = fits_table('hsc.fits')
## !  in wide, g=r=z coverage.  In deep, z is greatest
T.cut(T.band == 'z')

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
T.writeto('hsc-bricks.fits')
#T.writeto('~/cosmo/webapp/viewer-dev/data/hsc/hsc-bricks.fits')
