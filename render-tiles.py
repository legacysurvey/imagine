import sys

###
sys.path.insert(0, 'django-1.7')
###

import django
#django.setup()
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'


from map.views import *

from astrometry.util.multiproc import *
from astrometry.util.fits import *
from astrometry.libkd.spherematch import *

import logging
lvl = logging.DEBUG
logging.basicConfig(level=lvl, format='%(message)s', stream=sys.stdout)

class duck(object):
    pass

req = duck()
req.META = dict(HTTP_IF_MODIFIED_SINCE=None)

version = 1

def _one_tile((kind, zoom, x, y, ignore)):
    kwargs = dict(ignoreCached=ignore)
    # forcecache=False, return_if_not_found=True)
    if kind == 'sdss':
        print 'Zoom', zoom, 'x,y', x,y
        map_sdss(req, version, zoom, x, y, savecache=True)

    elif kind == 'decals-dr2':
        version = 2
        map_decals_dr2(req, version, zoom, x, y, savecache=True, forcecache=True,
                       hack_jpeg=True, drname='decals-dr2')

    elif kind in ['depth-g','depth-r','depth-z']:
        band = kind[-1]
        map_decam_depth(req, version, zoom, x, y, band=band,
                        savecache=True, **kwargs)
    elif kind == 'image-dr1k':
        map_decals_dr1k(req, version, zoom, x, y, savecache=True, 
                        forcecache=True, return_if_not_found=False, **kwargs)
    elif kind == 'model-dr1k':
        map_decals_model_dr1k(req, version, zoom, x, y, savecache=True, 
                              forcecache=True, return_if_not_found=False, **kwargs)

    elif kind == 'image-dr1n':
        map_decals_dr1n(req, version, zoom, x, y, savecache=True, 
                        forcecache=True, return_if_not_found=False, **kwargs)
    elif kind == 'model-dr1n':
        map_decals_model_dr1n(req, version, zoom, x, y, savecache=True, 
                              forcecache=True, return_if_not_found=False, **kwargs)
    elif kind == 'resid-dr1n':
        map_decals_resid_dr1n(req, version, zoom, x, y, savecache=True, 
                              forcecache=True, return_if_not_found=False, **kwargs)

    elif kind == 'image':
        map_decals_dr1j(req, version, zoom, x, y, savecache=True, 
                        forcecache=False, return_if_not_found=True)
                        #forcecache=True)
    elif kind == 'model':
        map_decals_model_dr1j(req, version, zoom, x, y, savecache=True, 
                              forcecache=True)
    elif kind == 'resid':
        map_decals_resid_dr1j(req, version, zoom, x, y, savecache=True, 
                              forcecache=True)
    elif kind == 'sfd':
        map_sfd(req, version, zoom, x, y, savecache=True)

    elif kind == 'unwise':
        map_unwise_w1w2(req, version, zoom, x, y, savecache=True,
                        ignoreCached=ignore)

def _bounce_one_tile(*args):
    try:
        _one_tile(*args)
    except KeyboardInterrupt:
        raise
    except:
        print 'Error in _one_tile(', args, '):'
        import traceback
        traceback.print_exc()


def _bounce_map_unwise_w1w2(args):
    return map_unwise_w1w2(*args, ignoreCached=True, get_images=True)
def _bounce_map_unwise_w3w4(args):
    return map_unwise_w3w4(*args, ignoreCached=True, get_images=True)


def _bounce_map_decals((args,kwargs)):
    print 'Bounce_map_decals:', args
    X = map_decals_dr1j(*args, ignoreCached=True, get_images=True, **kwargs)
    print 'Returning: type', type(X), X
    return X

def _bounce_map_decals_dr1k((args,kwargs)):
    print 'Bounce_map_decals_dr1k:', args
    X = map_decals_dr1k(*args, ignoreCached=True, get_images=True, **kwargs)
    print 'Returning: type', type(X), X
    return X

def top_levels(opt):
    if opt.kind in ['unwise', 'unwise-w3w4']:
        import pylab as plt
        from decals import settings
        from map.views import _unwise_to_rgb
        import fitsio

        if opt.kind == 'unwise-w3w4':
            tag = 'unwise-w3w4'
            bands = [3,4]
            bounce = _bounce_map_unwise_w3w4
        else:
            tag = 'unwise-w1w2'
            bands = [1,2]
            bounce = _bounce_map_unwise_w1w2

        pat = os.path.join(settings.DATA_DIR, 'tiles', tag, '%(ver)s',
                           '%(zoom)i', '%(x)i', '%(y)i.jpg')
        ver = 1
        patdata = dict(ver=ver)

        basescale = 2

        tilesize = 256
        tiles = 2**basescale
        side = tiles * tilesize

        basepat = 'base-%s-%i-%%s.fits' % (opt.kind, basescale)
        basefns = [basepat % band for band in bands]

        if not all([os.path.exists(fn) for fn in basefns]):
            bases = [np.zeros((side, side), np.float32) for band in bands]

            args = []
            for y in range(tiles):
                for x in range(tiles):
                    #print 'Base tile', x, y
                    args.append((req, ver, basescale, x, y))
            tiles = mp.map(bounce, args)
            for ims,arg in zip(tiles,args):
                x,y = arg[-2:]
                for im,base in zip(ims, bases):
                    if im is None:
                        continue
                    base[y*tilesize:(y+1)*tilesize,
                         x*tilesize:(x+1)*tilesize] = im

            for fn,base in zip(basefns, bases):
                fitsio.write(fn, base, clobber=True)
        else:
            print 'Reading', basefns
            bases = [fitsio.read(fn) for fn in basefns]

            if False:
                # Messin' around
                plt.figure(figsize=(8,8))
                plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
                #for S in [1000, 3000, 10000]:
                #for Q in [10, 25, 50]:
                S,Q = 3000,25
                im = _unwise_to_rgb([w1base, w2base], S=S, Q=Q)
                #plt.clf()
                #plt.imshow(im)
                plt.imsave('base-S%i-Q%s.png' % (S,Q), im)

                # Try converting to galactic coords...
                from astrometry.util.util import anwcs_create_mercator_2

                print 'Base images:', w1base.shape
                zoom = basescale
                h,w = w1base.shape
                zoomscale = 2.**zoom * (256./h)
                print 'Zoomscale', zoomscale
                wcs = anwcs_create_mercator_2(180., 0., w/2., h/2.,
                                              zoomscale, w, h, 1)

                wcs2 = anwcs_create_mercator_2(0., 0., w/2., h/2.,
                                               zoomscale, w, h, 1)

                print 'WCS:'
                for x,y in [(1,1), (1,h), (w,1), (w,h), (w/2,1), (w/2,h/2)]:
                    print 'x,y', (x,y), '-> RA,Dec', wcs.pixelxy2radec(x,y)[-2:]

                ok,ras,nil  = wcs2.pixelxy2radec(np.arange(w), np.ones(w))
                ok,nil,decs = wcs2.pixelxy2radec(np.ones(h), np.arange(h))
                print 'RAs', ras.shape
                print 'Decs', decs.shape

                lls = ras
                bbs = decs

                ll,bb = np.meshgrid(lls, bbs)
                print 'LL,BB', ll.shape, bb.shape

                from astrometry.util.starutil_numpy import lbtoradec

                ra,dec = lbtoradec(ll,bb)
                print 'RA,Dec', ra.shape, dec.shape

                ok,xx,yy = wcs.radec2pixelxy(ra, dec)
                print 'xx,yy', xx.shape, yy.shape

                lb1 = w1base[np.clip(np.round(yy-1).astype(int), 0, h-1),
                             np.clip(np.round(xx-1).astype(int), 0, w-1)]
                lb2 = w2base[np.clip(np.round(yy-1).astype(int), 0, h-1),
                             np.clip(np.round(xx-1).astype(int), 0, w-1)]

                lbim = _unwise_to_rgb(lb1, lb2, S=S,Q=Q)
                plt.imsave('lb.png', lbim)

                sys.exit(0)

        from scipy.ndimage.filters import gaussian_filter

        for scale in range(basescale-1, -1, -1):

            for i,base in enumerate(bases):
                base = gaussian_filter(base, 1.)
                base = (base[::2,::2] + base[1::2,::2] + base[1::2,1::2] + base[::2,1::2])/4.
                bases[i] = base

            tiles = 2**scale
            
            for y in range(tiles):
                for x in range(tiles):
                    ims = [base[y*tilesize:(y+1)*tilesize,
                                x*tilesize:(x+1)*tilesize] for base in bases]
                    tile = _unwise_to_rgb(ims, bands=bands)
                    pp = patdata.copy()
                    pp.update(zoom=scale, x=x, y=y)
                    fn = pat % pp
                    plt.imsave(fn, tile)
                    print 'Wrote', fn


    if opt.kind in ['depth-g', 'depth-r', 'depth-z']:
        import pylab as plt
        from decals import settings
        from scipy.ndimage.filters import gaussian_filter
        from map.views import trymakedirs

        tag = 'decam-' + opt.kind
        band = opt.kind[-1]
        ver = 1
        basescale = 5
        pat = os.path.join(settings.DATA_DIR, 'tiles', tag, '%(ver)s',
                           '%(zoom)i', '%(x)i', '%(y)i.jpg')
        patdata = dict(ver=ver)
        tilesize = 256
        tiles = 2**basescale
        side = tiles * tilesize
        
        base = np.zeros((side, side, 3), np.float32)
        for y in range(tiles):
            for x in range(tiles):
                dat = patdata.copy()
                dat.update(zoom=basescale, x=x, y=y)
                fn = pat % dat
                if not os.path.exists(fn):
                    print 'Does not exist:', fn
                    continue
                img = plt.imread(fn)
                base[y*tilesize:(y+1)*tilesize,
                     x*tilesize:(x+1)*tilesize,:] = img

        for scale in range(basescale-1, -1, -1):

            newbase = []
            for i in range(3):
                b = gaussian_filter(base[:,:,i], 1.)
                b = (b[ ::2, ::2] + b[1::2, ::2] +
                     b[1::2,1::2] + b[ ::2,1::2])/4.
                newbase.append(b)
            base = np.dstack(newbase)

            tiles = 2**scale
            for y in range(tiles):
                for x in range(tiles):
                    img = base[y*tilesize:(y+1)*tilesize,
                               x*tilesize:(x+1)*tilesize, :]

                    pp = patdata.copy()
                    pp.update(zoom=scale, x=x, y=y)
                    fn = pat % pp
                    trymakedirs(fn)
                    plt.imsave(fn, np.clip(np.round(img).astype(np.uint8), 0, 255))
                    print 'Wrote', fn


    ### HACK... factor this out...
    if opt.kind in ['image', 'model', 'resid', 'image-dr1k']:
        import pylab as plt
        from decals import settings
        from desi.common import get_rgb
        import fitsio
        from scipy.ndimage.filters import gaussian_filter
        from map.views import trymakedirs

        rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)

        tagdict = dict(image='decals-dr1j', model='decals-model-dr1j',
                       resid='decals-resid-dr1j')
                       
        tagdict['image-dr1k'] = 'decals-dr1k'

        tag = tagdict[opt.kind]
        del tagdict

        bounce = _bounce_map_decals
        if 'dr1k' in opt.kind:
            bounce = _bounce_map_decals_dr1k

        ver = 1
        basescale = 5

        pat = os.path.join(settings.DATA_DIR, 'tiles', tag, '%(ver)s',
                           '%(zoom)i', '%(x)i', '%(y)i.jpg')
        patdata = dict(ver=ver)

        tilesize = 256
        tiles = 2**basescale
        side = tiles * tilesize

        basepat = 'base-%s-%i-%%s.fits' % (opt.kind, basescale)
        bands = 'grz'

        basefns = [basepat % band for band in bands]
        if not all([os.path.exists(fn) for fn in basefns]):
            bases = [np.zeros((side, side), np.float32) for band in bands]

            args = []
            kwa = dict()
            if opt.kind == 'model':
                kwa.update(model=True)
            elif opt.kind == 'resid':
                kwa.update(resid=True)

            xy = []
            for y in range(tiles):
                for x in range(tiles):
                    args.append(((req, ver, basescale, x, y),kwa))
                    xy.append((x,y))
            tiles = mp.map(bounce, args)
            for ims,(x,y) in zip(tiles, xy):
                if ims is None:
                    continue
                for im,base in zip(ims, bases):
                    if im is None:
                        continue
                    base[y*tilesize:(y+1)*tilesize,
                         x*tilesize:(x+1)*tilesize] = im

            for fn,base in zip(basefns, bases):
                fitsio.write(fn, base, clobber=True)
        else:
            print 'Reading', basefns
            bases = [fitsio.read(fn) for fn in basefns]

        for scale in range(basescale-1, -1, -1):

            for i,base in enumerate(bases):
                #base = gaussian_filter(base, 1.)
                base = (base[::2,::2] + base[1::2,::2] + base[1::2,1::2] + base[::2,1::2])/4.
                bases[i] = base

            tiles = 2**scale
            for y in range(tiles):
                for x in range(tiles):
                    ims = [base[y*tilesize:(y+1)*tilesize,
                                x*tilesize:(x+1)*tilesize] for base in bases]

                    tile = get_rgb(ims, bands, **rgbkwargs)

                    pp = patdata.copy()
                    pp.update(zoom=scale, x=x, y=y)
                    fn = pat % pp
                    trymakedirs(fn)
                    plt.imsave(fn, tile)
                    print 'Wrote', fn



def main():
    import optparse

    parser = optparse.OptionParser()
    parser.add_option('--zoom', '-z', type=int, action='append', default=[],
                      help='Add zoom level; default 13')
    parser.add_option('--threads', type=int, default=1, help='Number of threads')
    parser.add_option('--y0', type=int, default=0, help='Start row')
    parser.add_option('--y1', type=int, default=None, help='End row (non-inclusive)')

    parser.add_option('--x0', type=int, default=None)
    parser.add_option('--x1', type=int, default=None)

    parser.add_option('-x', type=int)
    parser.add_option('-y', type=int)

    parser.add_option('--mindec', type=float, default=None, help='Minimum Dec to run')
    parser.add_option('--maxdec', type=float, default=None, help='Maximum Dec to run')

    parser.add_option('--minra', type=float, default=0.,   help='Minimum RA to run')
    parser.add_option('--maxra', type=float, default=360., help='Maximum RA to run')

    parser.add_option('--near', action='store_true', help='Only run tiles near bricks')

    parser.add_option('--near-ccds', action='store_true', help='Only run tiles near CCDs')

    parser.add_option('--queue', action='store_true', default=False,
                      help='Print qdo commands')

    parser.add_option('--all', action='store_true', help='Render all tiles')

    parser.add_option('--ignore', action='store_true', help='Ignore cached tile files',
                      default=False)

    parser.add_option('--top', action='store_true', help='Top levels of the pyramid')

    parser.add_option('--kind', default='image')

    opt,args = parser.parse_args()

    if len(opt.zoom) == 0:
        opt.zoom = [13]

    mp = multiproc(opt.threads)

    if opt.kind == 'sdss':
        if opt.maxdec is None:
            opt.maxdec = 90
        if opt.mindec is None:
            opt.mindec = -20
    else:
        if opt.maxdec is None:
            opt.maxdec = 40
        if opt.mindec is None:
            opt.mindec = -20

    if opt.top:
        top_levels(opt)
        sys.exit(0)

    from legacypipe.common import Decals
    decals = Decals()

    if opt.near:
        B = decals.get_bricks()
        print len(B), 'bricks'

    if opt.near_ccds:
        if opt.kind == 'sdss':
            C = fits_table(os.path.join(settings.DATA_DIR, 'sdss', 'window_flist.fits'),
                           columns=['rerun','ra','dec'])
            C.cut(C.rerun == '301')
            C.delete_column('rerun')
            # SDSS field size
            radius = 1.01 * np.hypot(10., 14.)/2. / 60.
            ccdsize = radius
            print len(C), 'SDSS fields'
        else:
            C = decals.get_ccds()
            print len(C), 'CCDs'
            ccdsize = 0.2

    if opt.x is not None:
        opt.x0 = opt.x
        opt.x1 = opt.x + 1
    if opt.y is not None:
        opt.y0 = opt.y
        opt.y1 = opt.y + 1

    for zoom in opt.zoom:
        N = 2**zoom
        if opt.y1 is None:
            y1 = N
        else:
            y1 = opt.y1

        if opt.x0 is None:
            opt.x0 = 0
        if opt.x1 is None:
            opt.x1 = N

        # Find grid of Ra,Dec tile centers and select the ones near DECaLS bricks.
        rr,dd = [],[]
        yy = np.arange(opt.y0, y1)
        xx = np.arange(opt.x0, opt.x1)

        if not opt.all:
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
            if len(dd) > 1:
                tilesize = max(np.abs(np.diff(dd)))
                print 'Tile size:', tilesize
            else:
                if opt.near_ccds or opt.near:
                    try:
                        wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, 0, opt.y0+1)
                        r2,d2 = wcs.get_center()
                    except:
                        wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, 0, opt.y0-1)
                        r2,d2 = wcs.get_center()
                    tilesize = np.abs(dd[0] - d2)
                    print 'Tile size:', tilesize
                else:
                    tilesize = 180.
            I = np.flatnonzero((dd >= opt.mindec) * (dd <= opt.maxdec))
            print 'Keeping', len(I), 'Dec points between', opt.mindec, 'and', opt.maxdec
            dd = dd[I]
            yy = yy[I]
            I = np.flatnonzero((rr >= opt.minra) * (rr <= opt.maxra))
            print 'Keeping', len(I), 'RA points between', opt.minra, 'and', opt.maxra
            rr = rr[I]
            xx = xx[I]
            
            print len(rr), 'RA points x', len(dd), 'Dec points'
            print 'x tile range:', xx.min(), xx.max(), 'y tile range:', yy.min(), yy.max()

        for iy,y in enumerate(yy):
            print
            print 'Y row', y

            if opt.near:
                d = dd[iy]
                I,J,dist = match_radec(rr, d+np.zeros_like(rr), B.ra, B.dec, 0.25 + tilesize, nearest=True)
                if len(I) == 0:
                    print 'No matches to bricks'
                    continue
                keep = np.zeros(len(rr), bool)
                keep[I] = True
                print 'Keeping', sum(keep), 'tiles in row', y, 'Dec', d
                x = xx[keep]
            elif opt.near_ccds:
                d = dd[iy]
                print 'RA range of tiles:', rr.min(), rr.max()
                print 'Dec of tile row:', d
                I,J,dist = match_radec(rr, d+np.zeros_like(rr), C.ra, C.dec, ccdsize + tilesize, nearest=True)
                if len(I) == 0:
                    print 'No matches to CCDs'
                    continue
                keep = np.zeros(len(rr), bool)
                keep[I] = True
                print 'Keeping', sum(keep), 'tiles in row', y, 'Dec', d
                x = xx[keep]
            else:
                x = xx

            if opt.queue:
                cmd = 'python -u render-tiles.py --zoom %i --y0 %i --y1 %i --kind %s' % (zoom, y, y+1, opt.kind)
                if opt.near_ccds:
                    cmd += ' --near-ccds'
                if opt.all:
                    cmd += ' --all'
                if opt.ignore:
                    cmd += ' --ignore'
                print cmd
                continue

            args = []
            for xi in x:
                args.append((opt.kind,zoom,xi,y, opt.ignore))
            print 'Rendering', len(args), 'tiles in row y =', y
            mp.map(_bounce_one_tile, args, chunksize=min(100, max(1, len(args)/opt.threads)))
            print 'Rendered', len(args), 'tiles'


if __name__ == '__main__':
    main()
