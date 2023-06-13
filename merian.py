from glob import glob
from astrometry.util.fits import fits_table
from astrometry.util.util import Tan
import fitsio

class duck(object):
    pass

#fns = glob('data/merian/deepCoadd_calexp/*/*/N540/deepCoadd_calexp_*_N540_*.fits')

#'/global/cfs/cdirs/cosmo/work/merian/merian_images
fns = glob('data/merian/deepCoadd_calexp/*/*/N*/deepCoadd_calexp_*_*_*_hsc_rings_v1_DECam_runs_merian_dr1_wide_*.fits')
fns.sort()
print('Found', len(fns), 'files')

tract_patches = {}

for fn in fns:
    #print('File', fn)
    parts = fn.strip().split('/')
    tract,patch,band = parts[-4], parts[-3], parts[-2]

    if (tract,patch) in tract_patches:
        tract_patches[(tract,patch)].append((band, fn))
    else:
        tract_patches[(tract,patch)] = [(band, fn)]

print(len(tract_patches), 'unique tract,patches')
        
T = fits_table()
wcscols = ['crval1','crval2','crpix1','crpix2','cd1_1','cd1_2','cd2_1','cd2_2']
for col in ['filename', 'ra','dec', 'ra1','ra2','dec1','dec2', 'naxis1','naxis2',
            'brickname','tract','patch'] + wcscols:
    T.set(col, [])

bands = ['N540', 'N708']
for band in bands:
    T.set('has_%s' % band, [])
    
#tract_patches = set()
# for fn in fns:
# 
#     print('File', fn)
#     parts = fn.strip().split('/')
#     tract,patch = parts[-4], parts[-3]
# 
#     if (tract,patch) in tract_patches:
#         print('Already got tract,patch', tract,patch)
#         continue

for (tract,patch),bandfiles in tract_patches.items():

    fn = bandfiles[0][-1]

    have_bands = [b for b,f in bandfiles]
    for band in bands:
        T.get('has_%s' % band).append(band in have_bands)

    print('Tract,patch', tract,patch, 'has bands', have_bands, 'reading', fn)

    if len(set(have_bands)) < len(have_bands):
        print('Mismatch:', bandfiles)

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
    T.brickname.append('%s_%s' % (tract,patch))

    T.tract.append(tract)
    T.patch.append(patch)

    #tract_patches.add((tract,patch))

T.to_np_arrays()
T.writeto('merian-bricks.fits')
