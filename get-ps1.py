from astrometry.util.fits import *
import sys
import os

args = sys.argv[1:]
if len(args) == 0:
    print('Usage: get-ps1.py <skycell>.<subcell> [...]')
    sys.exit(0)

bands = 'grz'
T = fits_table('data/ps1skycells.fits')
for arg in args:
    words = arg.split('.')
    cell = int(words[0], 10)
    subcell = int(words[1], 10)

    for band in bands:
        I = np.flatnonzero((T.projcell == cell) * (T.subcell == subcell) *
                           (T.filter == band))
        assert(len(I) == 1)
        i = I[0]

        url = 'ps1images.stsci.edu' + T.filename[i].strip()
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
