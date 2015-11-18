import os
from glob import glob
from legacypipe.common import Decals, wcs_for_brick
from map.utils import tiles_touching_wcs

if __name__ == '__main__':

    decals = Decals()
    
    fns = glob('dr2p/coadd/*/*/*-image.jpg')
    fns.sort()
    for fn in fns:
        print 'File', fn
        (h,t) = os.path.split(fn)
        (h,t) = os.path.split(h)
        print 'Brick:', t
        brickname = t
        brick = decals.get_brick_by_name(brickname)
        print 'Got brick:', brick
        bwcs = wcs_for_brick(brick)

        for zoom in range(5, 13):
            print 'Zoom', zoom
            xx,yy = tiles_touching_wcs(bwcs, zoom)
            print len(xx), 'tiles touching WCS'

            
