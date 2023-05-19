from glob import glob
from astrometry.util.fits import fits_table
from astrometry.util.util import Tan
import fitsio

# Find 'brick' files for N540, assume the same ones exist for other bands.

class duck(object):
    pass

fns = glob('data/merian/deepCoadd_calexp/*/*/N540/deepCoadd_calexp_*_N540_*.fits')

T = fits_table()
wcscols = ['crval1','crval2','crpix1','crpix2','cd1_1','cd1_2','cd2_1','cd2_2']
for col in ['filename', 'ra','dec', 'ra1','ra2','dec1','dec2', 'naxis1','naxis2',
            'brickname'] + wcscols:
    T.set(col, [])

for fn in fns:
    hdr = fitsio.read_header(fn, ext=1)
    fn = fn.replace('data/merian/','')
    T.filename.append(fn)
    t = duck()
    for col in wcscols:
        v = hdr[col.upper()]
        T.get(col).append(v)
        setattr(t, col, v)
    v = hdr['ZNAXIS1']
    T.naxis1.append(v)
    t.width = v
    v = hdr['ZNAXIS2']
    T.naxis2.append(v)
    t.height = v
    t.filename = fn
    
    #wcs = Tan(fn, 1)
    wcs = Tan(*[float(x) for x in
                [t.crval1, t.crval2, t.crpix1, t.crpix2, t.cd1_1, t.cd1_2, t.cd2_1, t.cd2_2,
                 t.width, t.height]])
    r,d = wcs.radec_center()
    T.ra.append(r)
    T.dec.append(d)

    midy = (t.height+1)/2.
    midx = (t.width+1)/2.
    rr,dd = wcs.pixelxy2radec([1, t.width], [midy,midy])
    T.ra1.append(min(rr))
    T.ra2.append(max(rr))
    rr,dd = wcs.pixelxy2radec([midx,midx], [1, t.height])
    T.dec1.append(min(dd))
    T.dec2.append(max(dd))
    parts = t.filename.strip().split('/')
    T.brickname.append('%s_%s' % (parts[-4], parts[-3]))

T.to_np_arrays()
T.writeto('merian-bricks.fits')
