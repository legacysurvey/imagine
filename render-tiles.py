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
        #map_sdss(req, version, zoom, x, y, savecache=True, forcecache=True)
        map_sdssco(req, version, zoom, x, y, savecache=True, forcecache=True,
                   return_if_not_found=True, hack_jpeg=True)

    elif kind in ['decals-dr2', 'decals-dr2-model', 'decals-dr2-resid']:
        v = 2
        kwa = {}
        if 'model' in kind:
            v = 1
            kwa.update(model=True, add_gz=True)
        if 'resid' in kind:
            v = 1
            kwa.update(resid=True, model_gz=True)

        print 'map_decals_dr2 kwargs:', kwa
        map_decals_dr2(req, v, zoom, x, y, savecache=True, forcecache=True,
                       hack_jpeg=True, drname='decals-dr2', **kwa)

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

def _bounce_sdss((args,kwargs)):
    (req,ver,zoom,x,y) = args
    fn = 'top-sdss-%i-%i-%i.fits' % (zoom, x, y)
    save = False
    if os.path.exists(fn):
        img = fitsio.read(fn)
        print 'Read', img.shape
        H,W,planes = img.shape
        ims = [img[:,:,i] for i in range(planes)]
    else:
        ims = map_sdss(*args, ignoreCached=True, get_images=True, **kwargs)
        if ims is None:
            return ims
        save = True

    # Save jpeg
    from decals import settings
    tag = 'sdss'
    pat = os.path.join(settings.DATA_DIR, 'tiles', tag, '%(ver)s',
                       '%(zoom)i', '%(x)i', '%(y)i.jpg')
    tilefn = pat % dict(ver=1, zoom=zoom, x=x, y=y)
    if not os.path.exists(tilefn):
        bands = 'gri'
        rgb = sdss_rgb(ims, bands)
        trymakedirs(tilefn)
        save_jpeg(tilefn, rgb)
        print 'Wrote', tilefn

    # Save FITS
    if save:
        d = np.dstack(ims)
        print 'writing', d.shape, 'to', fn
        fitsio.write(fn, d, clobber=True)

    return ims

def _bounce_decals_dr2((args,kwargs)):
    print 'Bounce_decals_dr2: kwargs', kwargs
    tag = 'image'
    if 'model' in kwargs:
        tag = 'model'
    if 'resid' in kwargs:
        tag = 'resid'
    (req,ver,zoom,x,y) = args
    print 'Tag', tag
    fn = 'top-dr2-%s-%i-%i-%i.fits' % (tag, zoom, x, y)
    if os.path.exists(fn):
        img = fitsio.read(fn)
        print 'Read', img.shape
        H,W,planes = img.shape
        ims = [img[:,:,i] for i in range(planes)]
        return ims

    ims = map_decals_dr2(*args, ignoreCached=True, get_images=True, write_jpeg=True,
                          hack_jpeg=True, forcecache=True, **kwargs)
    if ims is None:
        return ims
    # save FITS
    d = np.dstack(ims)
    print 'writing', d.shape, 'to', fn
    fitsio.write(fn, d, clobber=True)

    return ims

def top_levels(mp, opt):
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
    if opt.kind in ['image', 'model', 'resid', 'image-dr1k', 'sdss',
                    'decals-dr2', 'decals-dr2-model', 'decals-dr2-resid']:
        import pylab as plt
        from decals import settings
        from desi.common import get_rgb
        import fitsio
        from scipy.ndimage.filters import gaussian_filter
        from map.views import trymakedirs

        tagdict = dict(image='decals-dr1j', model='decals-model-dr1j',
                       resid='decals-resid-dr1j')
        tag = tagdict.get(opt.kind, opt.kind)
        del tagdict

        bouncemap = {'sdss': _bounce_sdss,
                     'decals-dr2': _bounce_decals_dr2,
                     'decals-dr2-model': _bounce_decals_dr2,
                     'decals-dr2-resid': _bounce_decals_dr2,
                     }
        bounce = bouncemap[opt.kind]

        rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)
        
        if opt.kind in ['decals-dr2', 'decals-dr2-model']:
            get_rgb = dr2_rgb
            rgbkwargs = {}

        ver = tileversions.get(opt.kind, [1])[-1]
        print 'Version', ver
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
            if 'model' in opt.kind:
                kwa.update(model=True, add_gz=True)
            elif 'resid' in opt.kind:
                kwa.update(resid=True, model_gz=True)

            xy = []
            if opt.y1 is None:
                opt.y1 = tiles
            if opt.x0 is None:
                opt.x0 = 0
            if opt.x1 is None:
                opt.x1 = tiles
            for y in range(opt.y0, opt.y1):
                for x in range(opt.x0, opt.x1):
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
            print 'Scale', scale
            for i,base in enumerate(bases):
                #base = gaussian_filter(base, 1.)
                base = (base[::2,::2] + base[1::2,::2] + base[1::2,1::2] + base[::2,1::2])/4.
                bases[i] = base

            tiles = 2**scale
            for y in range(tiles):
                for x in range(tiles):
                    ims = [base[y*tilesize:(y+1)*tilesize,
                                x*tilesize:(x+1)*tilesize] for base in bases]

                    if opt.kind == 'sdss':
                        bands = 'gri'
                        rgb = sdss_rgb(ims, bands)
                    else:
                        rgb = get_rgb(ims, bands, **rgbkwargs)

                    pp = patdata.copy()
                    pp.update(zoom=scale, x=x, y=y)
                    fn = pat % pp
                    trymakedirs(fn)
                    save_jpeg(fn, rgb)
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
    parser.add_option('--scale', action='store_true', help='Scale images?')
    parser.add_option('--coadd', action='store_true', help='Create SDSS coadd images?')
    parser.add_option('--grass', action='store_true', help='progress plot')

    opt,args = parser.parse_args()

    if len(opt.zoom) == 0:
        opt.zoom = [13]

    mp = multiproc(opt.threads)

    if opt.kind == 'sdss':
        if opt.maxdec is None:
            opt.maxdec = 90
        if opt.mindec is None:
            opt.mindec = -25
    else:
        if opt.maxdec is None:
            opt.maxdec = 40
        if opt.mindec is None:
            opt.mindec = -20

    if opt.top:
        top_levels(mp, opt)
        sys.exit(0)

    from legacypipe.common import Decals
    decals = Decals()

    if opt.near:
        B = decals.get_bricks()
        print len(B), 'bricks'

    if opt.scale:
        opt.near_ccds = True

    if opt.near_ccds:
        if opt.kind == 'sdss':
            C = fits_table(os.path.join(settings.DATA_DIR, 'sdss', 'window_flist.fits'),
                           columns=['rerun','ra','dec', 'run', 'camcol', 'field', 'score'])
            C.cut(C.rerun == '301')
            C.cut(C.score >= 0.6)
            #C.delete_column('rerun')
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

    if opt.coadd and opt.kind == 'sdss':
        from legacypipe.common import wcs_for_brick
        from map.views import trymakedirs

        B = decals.get_bricks()
        print len(B), 'bricks'
        B.cut((B.dec >= opt.mindec) * (B.dec < opt.maxdec))
        print len(B), 'in Dec range'
        B.cut((B.ra  >= opt.minra)  * (B.ra  < opt.maxra))
        print len(B), 'in RA range'

        if opt.queue:
            # ~ square-degree tiles
            # RA slices
            rr = np.arange(opt.minra , opt.maxra +1)
            dd = np.arange(opt.mindec, opt.maxdec+1)
            for rlo,rhi in zip(rr, rr[1:]):
                for dlo,dhi in zip(dd, dd[1:]):
                    print 'time python render-tiles.py --kind sdss --coadd --minra %f --maxra %f --mindec %f --maxdec %f' % (rlo, rhi, dlo, dhi)
            sys.exit(0)

        if opt.grass:
            basedir = settings.DATA_DIR
            codir = os.path.join(basedir, 'coadd', 'sdssco')
            rr,dd = [],[]
            for b in B:
                print 'Brick', b.brickname,
                fn = os.path.join(codir, b.brickname[:3], 'sdssco-%s-%s.fits' % (b.brickname, 'r'))
                print '-->', fn,
                if not os.path.exists(fn):
                    print
                    continue
                print 'found'
                rr.append(b.ra)
                dd.append(b.dec)
            import pylab as plt
            plt.clf()
            plt.plot(rr, dd, 'k.')
            plt.title('SDSS coadd tiles')
            plt.savefig('sdss.png')
            sys.exit(0)

        basedir = settings.DATA_DIR
        codir = os.path.join(basedir, 'coadd', 'sdssco')
        for b in B:
            print 'Brick', b.brickname
            wcs = wcs_for_brick(b, W=2400, H=2400, pixscale=0.396)
            bands = 'gri'
            dirnm = os.path.join(codir, b.brickname[:3])
            fns = [os.path.join(dirnm, 'sdssco-%s-%s.fits' % (b.brickname, band))
                   for band in bands]

            hdr = fitsio.FITSHDR()
            hdr['SURVEY'] = 'SDSS'
            wcs.add_to_header(hdr)

            if all([os.path.exists(fn) for fn in fns]):
                print 'Already exist'
                continue
            ims = map_sdss(req, 1, 0, 0, 0, get_images=True, wcs=wcs, ignoreCached=True,
                           forcescale=0)
            if ims is None:
                print 'No overlap'
                continue
            trymakedirs(os.path.join(dirnm, 'xxx'))
            for fn,band,im in zip(fns,bands, ims):
                fitsio.write(fn, im, header=hdr, clobber=True)
                print 'Wrote', fn

            # Also write scaled versions
            dirnm = os.path.join(basedir, 'scaled', 'sdssco')
            scalepat = os.path.join(dirnm, '%(scale)i%(band)s', '%(brickname).3s', 'sdssco-%(brickname)s-%(band)s.fits')
            for im,band in zip(ims,bands):
                scalekwargs = dict(band=band, brick=b.brickid, brickname=b.brickname)
                imwcs = wcs
                for scale in range(1, 7):
                    print 'Writing scale level', scale
                    im,imwcs,sfn = get_scaled(scalepat, scalekwargs, scale, None,
                                              wcs=imwcs, img=im, return_data=True)
        sys.exit(0)

    if opt.scale:
        if opt.kind == 'sdss':
            C.cut((C.dec >= opt.mindec) * (C.dec < opt.maxdec))
            print len(C), 'in Dec range'
            C.cut((C.ra  >= opt.minra)  * (C.ra  < opt.maxra))
            print len(C), 'in RA range'

            from astrometry.sdss import AsTransWrapper, DR9
            sdss = DR9(basedir=settings.SDSS_DIR)
            sdss.saveUnzippedFiles(settings.SDSS_DIR)
            sdss.setFitsioReadBZ2()
            if settings.SDSS_PHOTOOBJS:
                sdss.useLocalTree(photoObjs=settings.SDSS_PHOTOOBJS,
                                  resolve=settings.SDSS_RESOLVE)
            basedir = settings.DATA_DIR
            scaledir = 'sdss'
            dirnm = os.path.join(basedir, 'scaled', scaledir)
            for im in C:
                from map.views import _read_sip_wcs
                #if im.rerun != '301':
                #    continue
                for band in 'gri':
                    scalepat = os.path.join(dirnm, '%(scale)i%(band)s', '%(rerun)s', '%(run)i', '%(camcol)i', 'sdss-%(run)i-%(camcol)i-%(field)i-%(band)s.fits')
                    tmpsuff = '.tmp%08i' % np.random.randint(100000000)
                    basefn = sdss.retrieve('frame', im.run, im.camcol, field=im.field,
                                           band=band, rerun=im.rerun, tempsuffix=tmpsuff)
                    fnargs = dict(band=band, rerun=im.rerun, run=im.run,
                                  camcol=im.camcol, field=im.field)

                    scaled = 1
                    fn = get_scaled(scalepat, fnargs, scaled, basefn,
                                    read_base_wcs=read_astrans, read_wcs=_read_sip_wcs)
                    print 'get_scaled:', fn

            return 0

        else:
            assert(False)


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
