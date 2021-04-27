import os
import fitsio
import numpy as np
#from astrometry.util.fits import *
from map.views import get_layer
from viewer import settings
settings.READ_ONLY_BASEDIR = False

def run_one(X):
    layer,scale,ibrick,nbricks,brick,bands = X

    keep = False
    for band in bands:
        fn = layer.get_scaled_filename(brick, band, scale)

        pre = '%i/%i %s ' % (ibrick+1, nbricks, os.path.basename(fn))
        nz = 0
        if os.path.exists(fn):
            im = fitsio.read(fn)
            #print('Zeros: % 8i' % np.sum(im == 0), 'for', fn)
            nz = np.sum(im == 0)
            #print('%i/%i Has % 10i zeros:' % (ibrick+1, nbricks, nz), fn)
            pre = pre + ' has % 10i zeros:' % (nz)
            h,w = im.shape
            if nz < (0.01 * h*w):
                print(pre, 'Keeping')
                keep = True
                continue
            os.remove(fn)
    
        res = layer.create_scaled_image(brick, band, scale, fn)
        if res is None:
            # no images overlapping?
            print(pre, 'No overlap')
            continue

        # Read the resulting file
        im = fitsio.read(fn)
        h,w = im.shape
        nz2 = np.sum(im == 0)
        if nz2 == h*w:
            #print('  All zeros')
            print(pre, 'All zero')
            os.remove(fn)
            continue
        if nz2 == nz:
            print(pre, 'No change')
            #print('  No change')
        else:
            print(pre, 'Number of zeros changed: % 10i vs % 10i' % (nz2, nz))
        keep = True
    return keep

def main():
    from astrometry.util.multiproc import multiproc
    mp = multiproc(32)

    kind = 'ls-dr9-south'
    bands = 'grz'
    layer = get_layer(kind)
    #for scale in range(1,8):
    for scale in range(7,8):
        B = layer.get_bricks_for_scale(scale)
        print(len(B), 'bricks for scale', scale)
        print('Brick 0 is', B[0].brickname)

        N = len(B)

        # boolean results
        R = []
        
        #RESUME = 28500
        #RESUME = 64900
        #RESUME = 4000
        RESUME = 0
        for ibrick,brick in enumerate(B[:RESUME]):
            keep = False
            for band in bands:
                fn = layer.get_scaled_filename(brick, band, scale)
                if os.path.exists(fn):
                    keep = True
                    break
            R.append(keep)
            if ibrick%100 == 99:
                print('%i: keeping %i' % (ibrick+1, np.sum(R)))
        print('Resuming: brick', RESUME, 'is', B[RESUME].brickname)

        args = []
        for ibrick,brick in enumerate(B):
            if ibrick < RESUME:
                continue
            args.append((layer, scale, ibrick, N, brick, bands))
        R2 = mp.map(run_one, args)
        print(type(R2))
        R2 = list(R2)
        R.extend(R2)
        Ikeep = np.flatnonzero(R)

        B[np.array(Ikeep)].writeto('keep-survey-bricks-%i.fits.gz' % scale)
    
if __name__ == '__main__':
    main()
