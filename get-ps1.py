from astrometry.util.fits import *
import sys
import os

args = sys.argv[1:]
if len(args) == 0:
    print('Usage: get-ps1.py <skycell>.<subcell> [...]')
    sys.exit(0)

bands = 'griz'
T = fits_table('data/ps1skycells.fits')
all = False
for arg in args:
    if arg == 'all':
        all = True
    else:
        words = arg.split('.')
        cell = int(words[0], 10)
        subcell = int(words[1], 10)

    for band in bands:
        if all:
            I = np.flatnonzero(T.filter == band)
        else:
            I = np.flatnonzero((T.projcell == cell) * (T.subcell == subcell) *
                               (T.filter == band))
            assert(len(I) == 1)

        for i in I:
            cell = T.projcell[i]
            subcell = T.subcell[i]

            #url = 'http://ps1images.stsci.edu' + T.filename[i].strip()
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
