from astrometry.util.fits import *
from astrometry.util.util import Tan

B = fits_table('galex-bricks.fits')

pixscale = 1.5
size = 2000

minx = size
maxx = 0.
miny = size
maxy = 0.

for b in B:
    cd = pixscale/3600.
    mid = size/2.+0.5
    wcs = Tan(b.ra, b.dec, mid, mid,
              -cd, 0., 0., cd, float(size), float(size))
    #rr,dd = wcs.pixelxy2radec([1., 1., 1.,   mid,  size, size, size, mid],
    #                          [1, mid, size, size, size, mid,  1.,    1.])
    #print('rr', rr, 'dd', dd, 'vs', b.ra1,b.ra2, b.dec1,b.dec2)
    ok,xx,yy = wcs.radec2pixelxy([b.ra,  b.ra1, b.ra1,b.ra1, b.ra2, b.ra2,b.ra2, b.ra],
                                 [b.dec1,b.dec1,b.dec,b.dec2,b.dec2,b.dec,b.dec1,b.dec2])
    #print('RA,Dec', b.ra, b.dec, 'x', xx.min(), xx.max(), 'y', yy.min(), yy.max())
    assert(np.all(xx > 1.))
    assert(np.all(yy > 1.))
    assert(np.all(xx < size))
    assert(np.all(yy < size))

    minx = min(minx, min(xx))
    miny = min(miny, min(yy))
    maxx = max(maxx, max(xx))
    maxy = max(maxy, max(yy))

print('Overall X:', minx, maxx, 'Y:', miny, maxy)
