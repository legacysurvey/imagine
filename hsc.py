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
        path = '/'.join(parts[-7:])
        print(path)
        hsc.filename.append(path)

hsc.to_np_arrays()
hsc.writeto('hsc.fits')

    # plt.clf()
    # plt.plot(ras, decs, '.', color=dict(z='m').get(band, band))
    # plt.savefig('hsc-%s.png' % band)
