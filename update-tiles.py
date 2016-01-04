import sys
###
sys.path.insert(0, 'django-1.7')
###
import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'

from glob import glob
from legacypipe.common import Decals, wcs_for_brick
from map.utils import tiles_touching_wcs
from map.views import map_decals_dr2


class duck(object):
    pass

req = duck()
req.META = dict(HTTP_IF_MODIFIED_SINCE=None)

if __name__ == '__main__':

    decals = Decals()
    
    fns = glob('dr2p/coadd/*/*/*-image.jpg')
    fns.sort()
    bricknames = []
    for fn in fns:
        print 'File', fn
        (h,t) = os.path.split(fn)
        (h,t) = os.path.split(h)
        print 'Brick:', t
        brickname = t
        bricknames.append(brickname)

    for brickname in bricknames:
        scaledfns = glob('data/scaled/decals-dr2/*/%s/image-%s-*.fits' %
                         (brickname[:3], brickname))
        for s in scaledfns:
            print 'Deleting', s
            os.unlink(s)

    for brickname in bricknames:
        brick = decals.get_brick_by_name(brickname)
        print 'Got brick:', brick
        bwcs = wcs_for_brick(brick)

        for zoom in list(reversed(range(5, 13))):
            print 'Zoom', zoom
            xx,yy = tiles_touching_wcs(bwcs, zoom)
            print len(xx), 'tiles touching WCS'

            for x,y in zip(xx,yy):
                v = 2
                map_decals_dr2(req, v, zoom, x, y, savecache=True, forcecache=True,
                               ignoreCached=True,
                               hack_jpeg=True, drname='decals-dr2')


