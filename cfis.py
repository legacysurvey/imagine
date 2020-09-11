import fitsio
from glob import glob
from astrometry.util.fits import *

# Download tiles via
#vcp -v --quick vos:cfis/tiles_DR2/CFIS.39*.r.weight.fits.fz . &

fns = glob('tiles-dr2/CFIS*.r.fits')
fns.sort()
print(len(fns), 'files')
#fns = fns[:10]

T = fits_table()
keys = ('NAXIS1 NAXIS2 CRVAL1 CRPIX1 CD1_1 CD1_2 CRVAL2 CRPIX2 CD2_1 CD2_2 FILTER EXPTIME GAIN SATURATE IQFINAL'
).split()
for k in keys + ['filename', 'grid1', 'grid2']:
    T.set(k, [])
for i,fn in enumerate(fns):
    if i % 1000 == 0:
        print(i, fn)
    hdr = fitsio.read_header(fn)
    dirnm = os.path.basename(os.path.dirname(fn))
    fn = os.path.basename(fn)
    parts = fn.split('.')
    grid1 = parts[1]
    grid2 = parts[2]
    for k in keys:
        T.get(k).append(hdr[k])
    T.filename.append(os.path.join(dirnm, fn))
    T.grid1.append(grid1)
    T.grid2.append(grid2)

T.to_np_arrays()
T.writeto('cfis-files.fits')
