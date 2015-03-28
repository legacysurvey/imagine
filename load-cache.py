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

version = 1

def _one_tile((zoom, x, y)):
    map_decals_dr1d(req, version, zoom, x, y, savecache=True, 
                    forcecache=False, return_if_not_found=True)
                    #forcecache=True)

def main():
    import optparse

    parser = optparse.OptionParser()
    parser.add_option('--zoom', '-z', type=int, action='append', default=[],
                      help='Add zoom level; default 14')
    parser.add_option('--threads', type=int, default=1, help='Number of threads')
    parser.add_option('--y0', type=int, default=0, help='Start row')
    parser.add_option('--y1', type=int, default=None, help='End row (non-inclusive)')

    parser.add_option('--maxdec', type=float, default=40, help='Maximum Dec to run')
    parser.add_option('--mindec', type=float, default=-20, help='Minimum Dec to run')

    parser.add_option('--queue', action='store_true', default=False,
                      help='Print qdo commands')

    opt,args = parser.parse_args()

    if len(opt.zoom) == 0:
        opt.zoom = [14]

    mp = multiproc(opt.threads)

    for zoom in opt.zoom:
        N = 2**zoom
        if opt.y1 is None:
            y1 = N
        else:
            y1 = opt.y1

        for y in range(opt.y0, y1):
            wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, 0, y)
            r,d = wcs.get_center()
            print 'Zoom', zoom, 'y', y, 'center RA,Dec', r,d
            if d > opt.maxdec or d < opt.mindec:
                continue

            if opt.queue:
                print 'python -u load-cache.py --zoom %i --y0 %i --y1 %i' % (zoom, y, y+1)
                continue

            args = []
            for x in range(N):
                #wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, x, y)
                args.append((zoom,x,y))
            mp.map(_one_tile, args, chunksize=min(100, max(1, len(args)/opt.threads)))



if __name__ == '__main__':
    main()
