import os
from glob import glob
import numpy as np
import fitsio
from astrometry.util.fits import fits_table
from astrometry.util.multiproc import multiproc

def one_file(fn):
    fn = fn.strip()
    #fn = os.path.join('/data/CFIS', fn)
    #outfn = fn.replace('tiles-dr2', 'compressed/tiles-dr2')
    infn = os.path.join('/data2/CFIS/tiles-dr3-compressed', fn)
    #outfn = os.path.join('/data2/CFIS/tiles-dr3-compressed', fn)
    outfn = os.path.join('/data3/CFIS/tiles-dr3-compressed', fn)
    print(fn, infn, outfn)
    if os.path.exists(outfn):
        print('Exists:', outfn)
    img,hdr = fitsio.read(infn, header=True)

    wfn = os.path.join('/data/CFIS/weights-dr3', fn.replace('.fits', '.weight.fits.fz'))
    wt = fitsio.read(wfn)
    # that's it...
    img[wt == 0] = 0.

    # Blanton MAD sigmas: 2-3
    # qz -1e-4: files ~ 200 MB
    # qz -1e-3: files ~ 160 MB
    # qz -1e-2: files ~ 125 MB
    # qz -1e-1: files ~  88 MB
    finalfn = outfn
    tmpfn = outfn.replace('CFIS.', 'tmp.CFIS.')
    outfn = tmpfn + '[compress R 200 200; qz -1e-1]'
    fitsio.write(outfn, img, header=hdr, clobber=True)
    os.rename(tmpfn, finalfn)

    # cimg = fitsio.read(outfn)
    # print('RMS diff', np.sqrt(np.mean((cimg - img)**2)))
    # nz = np.sum(img != 0)
    # print('Non-zero pixels: %.3g %%' % (100. * nz / (img.shape[0]*img.shape[1])))
    # slice1 = (slice(0,-5,10),slice(0,-5,10))
    # slice2 = (slice(5,None,10),slice(5,None,10))
    # diff = np.abs(img[slice1] - img[slice2]).ravel()
    # diff = diff[diff != 0.]
    # mad = np.median(diff)
    # sig1 = 1.4826 * mad / np.sqrt(2.)
    # print('vs Blanton sigma', sig1)

def main():
    mp = multiproc(16)
    #mp = multiproc()
    #T = fits_table('data/cfis-r/cfis-tiles.fits')
    #mp.map(one_file, T.filename)

    #fns = glob('/data2/CFIS/tiles-dr3/CFIS.*.u.fits')
    fns = glob('/data2/CFIS/tiles-dr3-compressed/CFIS.*.fits')
    fns.sort()
    fns = [os.path.basename(fn) for fn in fns]
    mp.map(one_file, fns)

    #map(one_file, [fn for fn in T.filename])

if __name__ == '__main__':
    main()
