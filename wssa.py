from astrometry.util.util import *
from astrometry.util.fits import *
import fitsio
import os
import numpy as np

T = fits_table('data/wssa/tiles/wisetile-index-allsky.fits.gz')
print(len(T), 'tiles')

T.magzp = np.zeros(len(T), np.float32)
T.ra1 = np.zeros(len(T), np.float32)
T.ra2 = np.zeros(len(T), np.float32)

ddec = 5.
T.dec1 = np.maximum(-90., T.dec - ddec)
T.dec2 = np.minimum(+90., T.dec + ddec)

decs = np.unique(T.dec)
for d in decs:
    print('Dec', d)
    I = np.flatnonzero(T.dec == d)
    print('RAs:', T.ra[I])
    print('dRA:', np.diff(T.ra[I]))
    if len(I) == 1:
        T.ra1[I] = 0.
        T.ra2[I] = 360.
    else:
        dra = np.diff(T.ra[I])[0]
        T.ra1[I] = T.ra[I] - dra/2.
        T.ra2[I] = T.ra[I] + dra/2.
T.ra1 += (T.ra1 < 0)*360.
T.ra2 += (T.ra2 > 360)*(-360.)

for ii,t in enumerate(T):
    fn = os.path.join('data','wssa','tiles',t.fname+'.gz')
    print('File', fn)
    cmd = 'imcopy data/wssa/tiles/%s.gz"+1" data/wssa/%s' % (t.fname, t.fname)
    print(cmd)
    if os.system(cmd):
        break
    fn = 'data/wssa/'+t.fname.strip()
    hdr = fitsio.read_header(fn)
    zp = hdr['MAGZP']
    print('ZP', zp)
    T.magzp[ii] = zp

T.writeto('data/wssa/wssa-bricks.fits')

