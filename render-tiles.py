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

    # HACK -- DR1
    B = fits_table('decals-bricks-in-dr1.fits')
    
    for zoom in opt.zoom:
        N = 2**zoom
        if opt.y1 is None:
            y1 = N
        else:
            y1 = opt.y1

        # HACK -- DR1
        # Find grid of Ra,Dec tile centers and select the ones near DECaLS bricks.
        rr,dd = [],[]
        yy = np.arange(opt.y0, y1)
        xx = np.arange(N)
        for y in yy:
            wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, 0, y)
            r,d = wcs.get_center()
            dd.append(d)
        for x in xx:
            wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, x, 0)
            r,d = wcs.get_center()
            rr.append(r)
        dd = np.array(dd)
        rr = np.array(rr)
        I = np.flatnonzero((dd >= opt.mindec) * (dd <= opt.maxdec))
        print 'Keeping', len(I), 'Dec points'
        dd = dd[I]
        yy = yy[I]
        print len(rr), 'RA points,', len(dd), 'Dec points'

        for iy,y in enumerate(yy):
            d = dd[iy]
            I,J,d = match_radec(d, rr, B.ra, B.dec, 0.25)
            keep = np.zeros(len(rr), bool)
            keep[I] = True
            print 'Keeping', sum(keep), 'tiles in row', y, 'Dec', d
            x = xx[keep]

            args = []
            for xi in x:
                args.append((zoom,xi,y))
            mp.map(_one_tile, args, chunksize=min(100, max(1, len(args)/opt.threads))
       continue

       
        
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
