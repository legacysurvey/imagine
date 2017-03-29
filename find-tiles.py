import matplotlib
matplotlib.use('Agg')
import pylab as plt

import os
import numpy as np
import fitsio


for basedir,tag in [#('data/tiles/decals-dr1j/1', 'image'),
                    #('data/tiles/decals-model-dr1j/1', 'model'),
                    #('data/tiles/decals-resid-dr1j/1', 'resid'),
                    #('data/tiles/unwise-w1w2/1', 'unwise'),
    #('data/tiles/decals-dr3/1', 'image'),
    ('data/tiles/decals-dr3-model/1', 'model'),
    ('data/tiles/decals-dr3-resid/1', 'resid'),
    ]:
    for zoom in range(0, 14):
        N = 2**zoom
        print 'Zoom', zoom, 'size', zoom
        #exists = np.zeros((N,N), np.uint8)
        sizes = np.zeros((N,N), np.int32)
        for x in range(N):
            dirnm = os.path.join(basedir, '%i'%zoom, '%i'%x)
            if not os.path.exists(dirnm):
                print 'No col', x
                continue
            dirlist = os.listdir(dirnm)
            print 'Found', len(dirlist), 'files in col', x
            for y in range(N):
                fn = '%i.jpg' % y
                if fn in dirlist:
                    st = os.lstat(os.path.join(dirnm, fn))
                    sizes[y,x] = st.st_size
                    # if os.path.islink(fn):
                    #     exists[y,x] = 1
                    # else:
                    #     exists[y,x] = 2

        plt.clf()
        plt.imshow(sizes, interpolation='nearest', origin='lower', cmap='hot')
        #vmin=0, vmax=2)
        plt.savefig('tiles-%s-zoom%i.png' % (tag, zoom))

        fitsio.write('tiles-%s-zoom%i.fits' % (tag, zoom), sizes)
