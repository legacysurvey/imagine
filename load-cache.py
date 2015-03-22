import django
#django.setup()
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'

from map.views import *

from astrometry.util.multiproc import *

class duck(object):
    pass

req = duck()
req.META = dict(HTTP_IF_MODIFIED_SINCE=None)

version = 2

def _one_tile((zoom, x, y)):
    map_decals_dr1(req, version, zoom, x, y, savecache=True, forcecache=True)

def main():
    import optparse

    parser = optparse.OptionParser()
    parser.add_option('--zoom', type=int, action='append', default=[],
                      help='Add zoom level; default 14')
    parser.add_option('--threads', type=int, default=1, help='Number of threads')
    parser.add_option('--y0', type=int, default=0, help='Start row')
    opt,args = parser.parse_args()

    if len(opt.zoom) == 0:
        opt.zoom = [14]

    mp = multiproc(opt.threads)

    for zoom in opt.zoom:
        N = 2**zoom
        for y in range(opt.y0, N):
            wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, 0, y)
            r,d = wcs.get_center()
            print 'Zoom', zoom, 'y', y, 'center RA,Dec', r,d
            if d > 30 or d < -20:
                continue
            if d < 25:
                continue
            args = []
            for x in range(N):
                #wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, x, y)
                args.append((zoom,x,y))
            mp.map(_one_tile, args)



if __name__ == '__main__':
    main()
