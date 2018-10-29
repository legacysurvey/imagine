from astrometry.util.fits import *
import sys
import os
import argparse
from astrometry.libkd.spherematch import *

parser = argparse.ArgumentParser()
parser.add_argument('-r', dest='radius', type=float, help='Search radius in degrees',
                    default=1)
#parser.add_argument('--all', '-a', action='store_true', help='Retrieve all within range; default: nearest',
 #                   default=False)
parser.add_argument('--bands', default='grz', help='Bands to retrieve')
parser.add_argument('radec', nargs=2, type=float, help='RA,Dec coords to search')
args = parser.parse_args()

bands = args.bands
T = fits_table('data/ps1skycells.fits')
print(len(T), 'skycells')
from collections import Counter
print('Filters in skycells table:', Counter(T.filter))
print('bands:', bands)
for tf in np.unique(T.filter):
    print('filter', tf, 'in bands?', tf in bands)

isin = np.array([b in bands for b in T.filter])
print('is in:', Counter(isin))
T.cut(np.array([b in bands for b in T.filter]))
print('Kept', len(T), 'skycells')



ra,dec = args.radec
radius = args.radius
closest = False #not args.all

print('Searching RA,Dec', ra,dec, 'with radius', radius, 'deg')

I,J,d = match_radec(np.array([ra]), np.array([dec]), T.ra, T.dec, radius, nearest=closest)
print('Matched', len(J), 'sky cells')
T.cut(J)

T.writeto('skycells.fits')

for cell,subcell,fn,band in zip(T.projcell, T.subcell, T.filename, T.filter):
    #url = 'http://ps1images.stsci.edu' + fn.strip()
    #http://ps1images.stsci.edu/rings.v3.skycell/1333/015/rings.v3.skycell.1333.015.stk.g.unconv.fits

    url = 'http://ps1images.stsci.edu/rings.v3.skycell/%04i/%03i/rings.v3.skycell.%04i.%03i.stk.%s.unconv.fits' % (cell, subcell, cell, subcell, band)

    outdir = os.path.join('data', 'ps1', 'skycells', '%04i'%cell)
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    fn = 'ps1-%04i-%03i-%s.fits' % (cell, subcell, band)
    outfn = os.path.join(outdir, fn)
    if os.path.exists(outfn):
        print('File exists:', outfn)
        continue

    tmpoutfn = os.path.join(outdir, 'tmp-' + fn)
    cmd = 'wget -O %s "%s"' % (tmpoutfn, url)
    print(cmd)
    rtn = os.system(cmd)
    if rtn == 0:
        os.rename(tmpoutfn, outfn)
