import fitsio
from glob import glob
from astrometry.util.fits import *
from collections import Counter

# Download tiles via
#vcp -v --quick vos:cfis/tiles_DR2/CFIS.39*.r.weight.fits.fz . &

#fns = glob('tiles-dr2/CFIS*.r.fits')
#fns = glob('tiles-dr2/CFIS*.u.fits')


#outfn = 'cfis-files-dr3-r.fits'
#fns = glob('/data/CFIS/tiles-dr3-compressed/CFIS.*.r.fits')
outfn = 'cfis-files-dr3-u.fits'
fns = glob('/data2/CFIS/tiles-dr3-compressed/CFIS.*.u.fits')

#outfn = 'cfis-files-dr2-r.fits'
#fns = glob('/data/CFIS/compressed/tiles-dr2/CFIS.*.r.fits')
#outfn = 'cfis-files-dr2-u.fits'
#fns = glob('/data/CFIS/compressed/tiles-dr2/CFIS.*.u.fits')

# 1 for fpack'ed
hdu = 1


#'/data2/CFIS/tiles-dr3/CFIS.*.r.fits')
fns.sort()
print(len(fns), 'files')
#fns = fns[:10]

T = fits_table()
keys = ('CRVAL1 CRPIX1 CD1_1 CD1_2 CRVAL2 CRPIX2 CD2_1 CD2_2 FILTER EXPTIME GAIN SATURATE IQFINAL'
).split()
zkeys = ('NAXIS1 NAXIS2').split()
for k in keys + zkeys + ['filename', 'grid1', 'grid2']:
    T.set(k.lower(), [])
for i,fn in enumerate(fns):
    if i % 1000 == 0:
        print(i, fn)
    hdr = fitsio.read_header(fn, ext=hdu)
    dirnm = os.path.basename(os.path.dirname(fn))
    fn = os.path.basename(fn)
    parts = fn.split('.')
    grid1 = parts[1]
    grid2 = parts[2]
    for k in keys:
        T.get(k.lower()).append(hdr[k])
    # fpack ZNAXIS1, ZNAXIS2
    for k in zkeys:
        if 'Z'+k in hdr:
            T.get(k.lower()).append(hdr['Z'+k])
        else:
            T.get(k.lower()).append(hdr[k])
    T.filename.append(os.path.join(dirnm, fn))
    T.grid1.append(int(grid1))
    T.grid2.append(int(grid2))

T.to_np_arrays()
#T.writeto(outfn)
#T = fits_table('cfis-files-dr3-r.fits')

T.ra = np.fmod((T.crval1+360), 360.)
T.dec = T.crval2

n1 = max(T.grid1) + 1
n2 = max(T.grid2) + 1
ra_grid = np.empty((n1, n2))
dec_grid = np.empty((n1, n2))
defval = -100
ra_grid[:,:] = defval
dec_grid[:,:] = defval

# It's a brick-like system, with bricks that cross RA=0.

for i,(grid1,grid2,ra,dec) in enumerate(zip(T.grid1, T.grid2, T.ra, T.dec)):
    ra_grid [grid1,grid2] = ra
    dec_grid[grid1,grid2] = dec

print('Unique Decs:', np.unique(dec_grid))

d = np.diff(np.unique(dec_grid))
(d,n) = Counter(d).most_common(1)[0]
decstep = d
print('Dec step:', decstep)

grid2tostep = {}

for j in range(n2):
    if np.all(dec_grid[:,j] == defval):
        continue
    print('grid2', j)
    #print('Decs:', dec_grid[:,j])
    #diff = np.diff(ra_grid[:,j])
    good = ra_grid[:,j] != defval
    diff = (ra_grid[1:,j] - ra_grid[:-1,j])
    diff = np.fmod((360. + diff), 360.)
    ok = good[1:] * good[:-1]
    diff = diff[ok]
    if len(diff) == 0:
        continue
    #print('Unique RA diffs:', np.unique(diff))
    assert(max(diff) - min(diff) < 1e-3)
    step = np.mean(diff)
    print('Mean step:', step)
    grid2tostep[j] = step

T.ra1 = np.empty(len(T))
T.ra1[:] = defval
T.ra2 = np.empty(len(T))
T.ra2[:] = defval
T.dec1 = np.empty(len(T))
T.dec1[:] = defval
T.dec2 = np.empty(len(T))
T.dec2[:] = defval
for i,(ra, dec, grid2) in enumerate(zip(T.ra, T.dec, T.grid2)):
    rastep = grid2tostep.get(grid2, None)
    if rastep is None:
        # Stepping not known... guess ra1,ra2
        print('SKIPPING RA STEP')
        assert(False)
        pass
    T.ra1[i] = np.fmod(360+(ra - rastep/2), 360.)
    T.ra2[i] = np.fmod(360+(ra + rastep/2), 360.)
    T.dec1[i] = dec - decstep/2
    T.dec2[i] = dec + decstep/2

#T.writeto('tiles.fits')
T.writeto(outfn)
    
