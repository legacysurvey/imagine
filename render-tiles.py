from __future__ import print_function
import os
import sys
from glob import glob
import numpy as np

#sys.path.insert(0, 'django-1.9')
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'viewer.settings'

from viewer import settings
settings.READ_ONLY_BASEDIR = False
#settings.DEBUG_LOGGING = True

from map.views import *

from astrometry.util.multiproc import *
from astrometry.util.fits import *
from astrometry.libkd.spherematch import *

import logging
#lvl = logging.DEBUG
lvl = logging.INFO
logging.basicConfig(level=lvl, format='%(message)s', stream=sys.stdout)

class duck(object):
    pass

req = duck()
req.META = dict(HTTP_IF_MODIFIED_SINCE=None)
req.GET  = dict()


version = 1

def get_version(kind):
    return 1

def _one_tile(X):
    (kind, zoom, x, y, ignore, get_images) = X
    kwargs = dict(ignoreCached=ignore,
                  get_images=get_images)

    print()
    print('one_tile: zoom', zoom, 'x,y', x,y)

    v = version
    
    # forcecache=False, return_if_not_found=True)
    if kind == 'sdss':
        print('Zoom', zoom, 'x,y', x,y)
        v = 1
        layer = get_layer('sdssco')
        return layer.get_tile(req, v, zoom, x, y, savecache=True, forcecache=True,
                              **kwargs)

    elif kind == 'sdss2':
        v = 1
        layer = get_layer(kind)
        return layer.get_tile(req, v, zoom, x, y, savecache=True, forcecache=True,
                              **kwargs)
        
    elif kind == 'ps1':
        print('Zoom', zoom, 'x,y', x,y)
        from map import views
        get_tile = views.get_tile_view('ps1')
        get_tile(req, version, zoom, x, y, savecache=True,
                 return_if_not_found=True)

    elif kind in ['decals-dr5', 'decals-dr5-model', 'decals-dr5-resid',
                  'mzl1s+bass-dr6', 'mzls+bass-dr6-model', 'mzls+bass-dr6-resid']:
        v = 1
        layer = get_layer(kind)
        return layer.get_tile(req, v, zoom, x, y, savecache=True, forcecache=True,
                              **kwargs)

    elif kind in ['eboss']:
        v = 1
        layer = get_layer(kind)
        return layer.get_tile(req, v, zoom, x, y, savecache=True, forcecache=True,
                              **kwargs)
        
    elif kind in ['decaps2', 'decaps2-model', 'decaps2-resid']:
        v = 2
        # layer = get_layer(kind)
        # print('kind', kind, 'zoom', zoom, 'x,y', x,y)
        # return layer.get_tile(req, v, zoom, x, y, savecache=True, forcecache=True,
        #                       get_images=get_images, ignoreCached=True)
        
    elif kind == 'sfd':
        v = 2
        layer = sfd_layer
        layer.get_tile(req, v, zoom, x, y, savecache=True)
        #map_sfd(req, version, zoom, x, y, savecache=True)
    elif kind == 'halpha':
        map_halpha(req, version, zoom, x, y, savecache=True)

    elif kind == 'unwise':
        map_unwise_w1w2(req, version, zoom, x, y, savecache=True,
                        ignoreCached=ignore)
        print('unWISE zoom', zoom, 'x,y', x,y)

    elif kind in ['unwise-neo2', 'unwise-neo3']:
        from map import views
        view = views.get_tile_view(kind)
        return view(req, version, zoom, x, y, savecache=True, **kwargs)

    from map import views
    view = views.get_tile_view(kind)
    return view(req, v, zoom, x, y, savecache=True, **kwargs)

def _bounce_one_tile(*args):
    try:
        _one_tile(*args)
    except KeyboardInterrupt:
        raise
    except:
        print('Error in _one_tile(', args, '):')
        import traceback
        traceback.print_exc()

def _bounce_map_unwise_w1w2(args):
    return map_unwise_w1w2(*args, ignoreCached=True, get_images=True)
def _bounce_map_unwise_w3w4(args):
    return map_unwise_w3w4(*args, ignoreCached=True, get_images=True)

def _bounce_sdssco(X):
    (args,kwargs) = X
    (req,ver,zoom,x,y) = args
    fn = 'top-sdss-%i-%i-%i.fits' % (zoom, x, y)
    save = False
    if os.path.exists(fn):
        img = fitsio.read(fn)
        print('Read', img.shape)
        H,W,planes = img.shape
        ims = [img[:,:,i] for i in range(planes)]
    else:
        #ims = map_sdss(*args, ignoreCached=True, get_images=True, **kwargs)
        ims = map_sdssco(*args, ignoreCached=True, get_images=True, 
                          hack_jpeg=True, **kwargs)
        if ims is None:
            return ims
        save = True

    # Save jpeg
    #tag = 'sdss'
    tag = 'sdssco'
    pat = os.path.join(settings.DATA_DIR, 'tiles', tag, '%(ver)s',
                       '%(zoom)i', '%(x)i', '%(y)i.jpg')
    tilefn = pat % dict(ver=1, zoom=zoom, x=x, y=y)
    if not os.path.exists(tilefn):
        bands = 'gri'
        rgb = sdss_rgb(ims, bands)
        trymakedirs(tilefn)
        save_jpeg(tilefn, rgb)
        print('Wrote', tilefn)

    # Save FITS
    if save:
        d = np.dstack(ims)
        print('writing', d.shape, 'to', fn)
        fitsio.write(fn, d, clobber=True)

    return ims

def _bounce_decals_dr3(X):
    (args,kwargs) = X
    print('Bounce_decals_dr3: kwargs', kwargs)
    tag = 'image'
    if 'model' in kwargs:
        tag = 'model'
    if 'resid' in kwargs:
        tag = 'resid'
    (req,ver,zoom,x,y) = args
    print('Tag', tag)
    fn = 'top-dr3-%s-%i-%i-%i.fits' % (tag, zoom, x, y)
    if os.path.exists(fn):
        img = fitsio.read(fn)
        print('Read', img.shape)
        H,W,planes = img.shape
        ims = [img[:,:,i] for i in range(planes)]
        return ims

    ims = map_decals_dr3(*args, ignoreCached=True, get_images=True, write_jpeg=True,
                          hack_jpeg=True, forcecache=True, **kwargs)
    if ims is None:
        return ims
    # save FITS
    d = np.dstack(ims)
    print('writing', d.shape, 'to', fn)
    fitsio.write(fn, d, clobber=True)

    return ims

def top_levels(mp, opt):
    from map.views import save_jpeg, trymakedirs

    import pylab as plt
    from viewer import settings
    import fitsio
    from scipy.ndimage.filters import gaussian_filter
    from map.views import _unwise_to_rgb
    tag = opt.kind

    from map.views import get_layer
    layer = get_layer(opt.kind)

    bands = layer.get_bands()

    print('Layer:', layer)
    #print('Survey:', layer.survey)
    #print('  cache_dir:', layer.survey.cache_dir)

    rgbkwargs = {}
    if opt.kind in ['unwise-neo2', 'unwise-neo3', 'unwise-neo4', 'unwise-neo6', 'unwise-neo7',
                    'unwise-cat-model']:
        bands = [1, 2]
    elif opt.kind == 'unwise-w3w4':
        bands = [3, 4]
    elif opt.kind == 'sdss2':
        bands = 'gri'
    elif opt.kind == 'galex':
        bands = ['n','f']
    elif opt.kind == 'ztf':
        bands = 'gri'
    elif opt.kind == 'wssa':
        bands = ['x']
    elif 'vlass' in opt.kind:
        bands = [1]
    #else:
    #    bands = 'grz'

    if opt.bands is not None:
        bands = opt.bands
    print('Bands', bands)

    ver = tileversions.get(opt.kind, [1])[-1]
    print('Version', ver)
    basescale = 5

    #if opt.kind  in ['ls-dr10-early', 'ls-dr10', 'ls-dr10-model', 'ls-dr10-resid',
    #                 'ls-dr10-grz', 'ls-dr10-model-grz', 'ls-dr10-resid-grz',]:
    if 'ls-dr10' in opt.kind:
        ## UGH, this is because there is some problem with the tiling so that scale 5, y=26 fails
        ## to find any bricks touching, and rather than figure it out I just backed out the scale.
        basescale = 6
    
    pat = os.path.join(settings.DATA_DIR, 'tiles', tag, '%(ver)s',
                       '%(zoom)i', '%(x)i', '%(y)i.jpg')
    patdata = dict(ver=ver)

    tilesize = 256
    tiles = 2**basescale
    side = tiles * tilesize

    if opt.kind in ['ls-dr10', 'ls-dr10-model', 'ls-dr10-resid']:
        # Split survey with different colormaps for north/south (grz/griz).
        decsplit = 32.375

        modres = opt.kind.replace('ls-dr10','')
        
        from astrometry.util.starutil_numpy import radectolb
        import pylab as plt
        from map.views import save_jpeg, trymakedirs
        tilesplits = {}
        dec = decsplit
        fy = 1. - (np.log(np.tan(np.deg2rad(dec + 90)/2.)) - -np.pi) / (2.*np.pi)
        for zoom in range(basescale, -1, -1):
            n = 2**zoom
            y = int(fy * n)
            print('Zoom', zoom, '-> y', y)
            # ok,rr,dd = wcs.pixelxy2radec([1,1], [1,256])
            # #print('Decs', dd)
            for x in range(n):
                X = get_tile_wcs(zoom, x, y)
                wcs = X[0]
                H,W = wcs.shape
                #px = W//2 + 0.5
                #py = np.arange(1, H+1)
                px,py = np.meshgrid(np.arange(1, W+1), np.arange(1, H+1))
                rr,dd = wcs.pixelxy2radec(px, py)[-2:]
                ll,bb = radectolb(rr.ravel(), dd.ravel())
                ngc = (bb.reshape(dd.shape) > 0.)
                topmask = (dd >= decsplit) * ngc

                topfn = 'data/tiles/ls-dr9-north%s/1/%i/%i/%i.jpg' % (modres, zoom,x,y)
                botfn = 'data/tiles/ls-dr10-south%s/1/%i/%i/%i.jpg' % (modres, zoom,x,y)

                if not os.path.exists(topfn):
                    toprgb = np.zeros((256,256,3), np.uint8)
                else:
                    toprgb = plt.imread(topfn)
                if not os.path.exists(botfn):
                    botrgb = np.zeros((256,256,3), np.uint8)
                else:
                    botrgb = plt.imread(botfn)

                for i in range(3):
                    #botrgb[topmask,:,:] = toprgb[topmask,:,:]
                    botrgb[:,:,i][topmask] = toprgb[:,:,i][topmask]
                outfn = 'data/tiles/ls-dr10%s/1/%s/%i/%i.jpg' % (modres,zoom,x,y)
                trymakedirs(outfn)
                save_jpeg(outfn, botrgb)
                print('Wrote', outfn)
                
        return

    
    basepat = 'base-%s-%i-%%s.fits' % (opt.kind, basescale)

    basefns = [basepat % band for band in bands]
    print('Looking for', basefns)
    if not all([os.path.exists(fn) for fn in basefns]):
        bases = [np.zeros((side, side), np.float32) for band in bands]

        args = []
        xy = []
        if opt.y1 is None:
            opt.y1 = tiles
        if opt.x0 is None:
            opt.x0 = 0
        if opt.x1 is None:
            opt.x1 = tiles
        for y in range(opt.y0, opt.y1):
            for x in range(opt.x0, opt.x1):
                args.append((opt.kind, basescale, x, y, False, True))
                xy.append((x,y))

        tiles = mp.map(_one_tile, args)

        for ims,(x,y) in zip(tiles, xy):

            #for a,(x,y) in zip(args, xy):
            #print('_one_tile args:', a)
            #ims = _one_tile(a)
            #print('-> ', ims)

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
        print('Reading', basefns)
        bases = [fitsio.read(fn) for fn in basefns]

    for scale in range(basescale, -1, -1):
        print('Scale', scale)
        print('Layer:', layer)
        print('Bands:', bands)

        tiles = 2**scale
        for y in range(tiles):
            for x in range(tiles):
                ims = [base[y*tilesize:(y+1)*tilesize,
                            x*tilesize:(x+1)*tilesize] for base in bases]
                rgb = layer.get_rgb(ims, bands, **rgbkwargs)
                pp = patdata.copy()
                pp.update(zoom=scale, x=x, y=y)
                fn = pat % pp
                trymakedirs(fn)
                save_jpeg(fn, rgb)
                print('Wrote', fn)

        for i,base in enumerate(bases):
            if 'vlass' in opt.kind:
                base = np.maximum(np.maximum(base[::2,::2], base[1::2,::2]),
                                  np.maximum(base[1::2,1::2], base[::2,1::2]))
            else:
                base = (base[::2,::2] + base[1::2,::2] + base[1::2,1::2] + base[::2,1::2])/4.
            bases[i] = base


def _layer_get_filename(args):
    layer,brick,band,scale,force,deps = args

    if force:
        fn = layer.get_scaled_filename(brick, band, scale)
        if os.path.exists(fn):
            os.remove(fn)

    if deps:
        fn = layer.get_scaled_filename(brick, band, scale)
        if os.path.exists(fn) and layer.needs_recreating(brick, band, scale):
            print('Need to re-create', fn, 'due to modified dependencies')
            os.remove(fn)

    fn = layer.get_filename(brick, band, scale)
    print(fn)

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

    parser.add_option('--minra', type=float, default=None,   help='Minimum RA to run')
    parser.add_option('--maxra', type=float, default=None, help='Maximum RA to run')

    parser.add_option('--fix', default=False, action='store_true')
    
    parser.add_option('--touching', default=False, action='store_true',
                      help='Select bricks touching min/max ra/dec box (vs container within)')

    parser.add_option('--near', action='store_true', help='Only run tiles near bricks')

    parser.add_option('--near-ccds', action='store_true', help='Only run tiles near CCDs')

    parser.add_option('--queue', action='store_true', default=False,
                      help='Print qdo commands')
    parser.add_option('--queue-args', help='Add args to --queue commands')

    parser.add_option('--all', action='store_true', help='Render all tiles')

    parser.add_option('--ignore', action='store_true', help='Ignore cached tile files',
                      default=False)

    parser.add_option('--top', action='store_true', help='Top levels of the pyramid')

    parser.add_option('--split', action='store_true', help='For split layers (DR6+DR7), only compute one y strip per zoom level')

    parser.add_option('--bricks-exist', action='store_true', help='Create table of bricks that exist')

    parser.add_option('--kind', default='image')
    parser.add_option('--scale', action='store_true', help='Scale images?')
    parser.add_option('--deps', action='store_true', default=False, help='With --scale, check if files need to be remade due to updated dependencies?')
    parser.add_option('--bricks', action='store_true', help='Compute scaled brick tables?')
    parser.add_option('--coadd', action='store_true', help='Create SDSS coadd images?')
    parser.add_option('--grass', action='store_true', help='progress plot')

    parser.add_option('--bands', default=None)
    parser.add_option('--bandlist', default=None, help='Comma-separated list of bands')

    parser.add_option('-v', '--verbose', dest='verbose', action='count',
                      default=0, help='Make more verbose')


    opt,args = parser.parse_args()

    if opt.bandlist is not None:
        opt.bands = opt.bandlist.split(',')
    if opt.verbose == 0:
        lvl = logging.INFO
    else:
        lvl = logging.DEBUG
    logging.basicConfig(level=lvl, format='%(message)s', stream=sys.stdout)


    mp = multiproc(opt.threads)

    if opt.kind in ['sdss', 'sdss2']:
        if opt.maxdec is None:
            opt.maxdec = 90
        if opt.mindec is None:
            opt.mindec = -25

    # All-sky
    elif (opt.kind in ['halpha', 'unwise-neo1', 'unwise-neo2', 'unwise-neo3',
                       'unwise-neo4', 'unwise-neo6', 'unwise-neo7', 'unwise-cat-model',
                       'unwise-w3w4',
                       'galex', 'wssa', 'vlass', 'vlass1.2', 'hsc2', 'hsc-dr3', 'ztf']
              or 'dr8i' in opt.kind
              or 'dr9-test' in opt.kind
              or 'dr9f' in opt.kind
              or 'dr9g' in opt.kind
              or 'dr9h' in opt.kind
              or 'dr9i' in opt.kind
              or 'dr9j' in opt.kind
              or 'dr9-sga' in opt.kind
              or 'dr9-sga2' in opt.kind
              or 'dr9-grid' in opt.kind
              or 'dr9-segsize2' in opt.kind
              or 'dr9k' in opt.kind
              or 'dr9m' in opt.kind
              or 'ls-dr9.1.1' in opt.kind):
        if opt.maxdec is None:
            opt.maxdec = 90.
        if opt.mindec is None:
            opt.mindec = -90.
        if opt.maxra is None:
            opt.maxra = 360.
        if opt.minra is None:
            opt.minra = 0.

        if opt.kind == 'galex' and opt.bands is None:
            opt.bands = 'nf'
        if opt.kind == 'unwise-w3w4' and opt.bands is None:
            opt.bands = '34'
        if 'unwise' in opt.kind and opt.bands is None:
            opt.bands = '12'
        if 'ztf' in opt.kind and opt.bands is None:
            opt.bands = 'gri'
        if 'vlass' in opt.kind:
            opt.bands = [1]

    elif opt.kind == 'm33':
        if opt.mindec is None:
            opt.mindec = 30.40
        if opt.maxdec is None:
            opt.maxdec = 30.90
        if opt.minra is None:
            opt.minra = 23.29
        if opt.maxra is None:
            opt.maxra = 23.73

    elif opt.kind == 'm33':
        if opt.mindec is None:
            opt.mindec = 30.40
        if opt.maxdec is None:
            opt.maxdec = 30.90
        if opt.minra is None:
            opt.minra = 23.29
        if opt.maxra is None:
            opt.maxra = 23.73

    elif opt.kind in ['des-dr1']:
        if opt.maxdec is None:
            opt.maxdec = 6
        if opt.mindec is None:
            opt.mindec = -68
        if opt.maxra is None:
            opt.maxra = 360
        if opt.minra is None:
            opt.minra = 0

    elif opt.kind in ['mzls+bass-dr6', 'mzls+bass-dr6-model', 'mzls+bass-dr6-resid']:
        if opt.maxdec is None:
            opt.maxdec = 90
        if opt.mindec is None:
            opt.mindec = -20
        if opt.maxra is None:
            opt.maxra = 360
        if opt.minra is None:
            opt.minra = 0

    # elif opt.kind in ['dr8', 'dr8-model', 'dr8-resid']:
    #     if opt.maxdec is None:
    #         opt.maxdec = 90
    #     if opt.mindec is None:
    #         opt.mindec = -5
    #     if opt.maxra is None:
    #         opt.maxra = 360
    #     if opt.minra is None:
    #         opt.minra = 0
    
    elif opt.kind in ['dr8-north', 'dr8-north-model', 'dr8-north-resid',
                      'dr9sv-north', 'dr9sv-north-model', 'dr9sv-north-resid',
                      'ls-dr9-north', 'ls-dr9-north-model',
                      ]:
        if opt.maxdec is None:
            opt.maxdec = 90
        if opt.mindec is None:
            opt.mindec = -5
        if opt.maxra is None:
            opt.maxra = 360
        if opt.minra is None:
            opt.minra = 0

    elif opt.kind in ['dr8-south', 'dr8-south-model', 'dr8-south-resid',
                      'dr9sv-south', 'dr9sv-south-model', 'dr9sv-south-resid',
                      'fornax', 'fornax-model', 'fornax-resid']:
        if opt.maxdec is None:
            opt.maxdec = 40
        if opt.mindec is None:
            opt.mindec = -70
        if opt.maxra is None:
            opt.maxra = 360
        if opt.minra is None:
            opt.minra = 0

    elif opt.kind in ['decaps2', 'decaps2-model', 'decaps2-resid']:
        # After we have generated the bricks-exist files, don't really need RA,Dec limits...
        if opt.maxdec is None:
            #opt.maxdec = -15
            opt.maxdec = 90
        if opt.mindec is None:
            #opt.mindec = -75
            opt.mindec = -90
        if opt.maxra is None:
            #opt.maxra = 280
            opt.maxra = 360
        if opt.minra is None:
            #opt.minra = 90
            opt.minra = 0

    elif opt.kind in ['ls-dr9-south-B', 'ls-dr9-south-B-model']:
        if opt.maxdec is None:
            opt.maxdec = 40
        if opt.mindec is None:
            opt.mindec = -70
        if opt.maxra is None:
            opt.maxra = 360
        if opt.minra is None:
            opt.minra = 0
    elif 'ls-dr10' in opt.kind:
        #in ['ls-dr10-early', 'ls-dr10a', 'ls-dr10a-mode`l',
        #              'ls-dr10', 'ls-dr10-model', 'ls-dr10-resid']:
        if opt.bands is None:
            if opt.kind.endswith('-grz'):
                opt.bands = 'grz'
            else:
                opt.bands = 'griz'
        if opt.maxdec is None:
            opt.maxdec = 40
        if opt.mindec is None:
            opt.mindec = -90
        if opt.maxra is None:
            opt.maxra = 360
        if opt.minra is None:
            opt.minra = 0

    elif opt.kind in ['pandas']:
        if opt.bands is None:
            opt.bands = 'gi'
        if opt.maxdec is None:
            opt.maxdec = 51
        if opt.mindec is None:
            opt.mindec = 37
        if opt.maxra is None:
            opt.maxra = 360
        if opt.minra is None:
            opt.minra = 0

    else:
        if opt.maxdec is None:
            opt.maxdec = 40
        if opt.mindec is None:
            opt.mindec = -25
        if opt.maxra is None:
            opt.maxra = 360
        if opt.minra is None:
            opt.minra = 0

    if opt.bands is None:
        opt.bands = 'grz'

    if opt.top:
        top_levels(mp, opt)
        sys.exit(0)

    if opt.bricks:
        from map.views import get_layer
        layer = get_layer(opt.kind)
        for scale in range(1,8):
            B = layer.get_bricks_for_scale(scale)
        sys.exit(0)

    if opt.scale:

        if opt.kind == 'ps1':
            from map.views import get_layer

            fns = glob('data/ps1/skycells/*/ps1-*.fits')
            fns.sort()
            #ps1-1561-021-r.fits
            if len(opt.zoom) == 0:
                opt.zoom = [1,2,3,4,5,6,7]
            print(len(fns), 'PS1 image files')
            layer = get_layer(opt.kind)
            B = layer.get_bricks()
            print(len(B), 'skycells total')
            B.cut((B.ra  >= opt.minra ) * (B.ra  <= opt.maxra ) *
                  (B.dec >= opt.mindec) * (B.dec <= opt.maxdec))
            print(len(B), 'skycells in RA,Dec box')
            for i,brick in enumerate(B):
                for band in opt.bands:
                    fn0 = layer.get_filename(brick, band, 0)
                    print('PS1 image:', fn0)
                    if not os.path.exists(fn0):
                        continue
                    for scale in opt.zoom:
                        fn = layer.get_filename(brick, band, scale)
                        layer.create_scaled_image(brick, band, scale, fn)
            sys.exit(0)


        # Rebricked
        if (opt.kind in ['decals-dr5', 'decals-dr5-model', 'decals-dr7', 'decals-dr7-model',
                        'eboss',
                        'mzls+bass-dr6', 'mzls+bass-dr6-model',
                         'unwise-neo3', 'unwise-neo4', 'unwise-neo6', 'unwise-neo7',
                         'unwise-w3w4',
                         'unwise-cat-model',
                         'galex', 'wssa', 'des-dr1', 'hsc2', 'hsc-dr3',
                        'dr8-north', 'dr8-north-model', 'dr8-north-resid',
                        'dr8-south', 'dr8-south-model', 'dr8-south-resid',
                        'dr9c', 'dr9c-model', 'dr9c-resid',
                        'dr9d-south', 'dr9d-south-model', 'dr9d-south-resid',
                        'dr9d-north', 'dr9d-north-model', 'dr9d-north-resid',
                        #
                        'dr9e-south', 'dr9e-south-model', 'dr9e-south-resid',
                        'dr9e-north', 'dr9e-north-model', 'dr9e-north-resid',
                        #
                        'dr9sv-south', 'dr9sv-south-model', 'dr9sv-south-resid',
                        'dr9sv-north', 'dr9sv-north-model', 'dr9sv-north-resid',
                        'dr9sv', 'dr9sv-model', 'dr9sv-resid',
                        'fornax', 'fornax-model', 'fornax-resid',
                         'vlass1.2', 'ztf',
                         'ls-dr9-south', 'ls-dr9-south-model',
                         'ls-dr9-north', 'ls-dr9-north-model',
                         'ls-dr9.1.1', 'ls-dr9.1.1-model',

                         'ls-dr9-south-B', 'ls-dr9-south-B-model',
                         'asteroids-i',
                         'ls-dr10-early', 'ls-dr10a', 'ls-dr10a-model',
                         'ls-dr10', 'ls-dr10-model',
                         'ls-dr10-grz', 'ls-dr10-model-grz',
                         'pandas', 'wiro-C', 'wiro-D',
                         'suprime-L427', 'suprime-L427-model',
                         'suprime-L464', 'suprime-L464-model',
                         'suprime-L484', 'suprime-L484-model',
                         'suprime-L505', 'suprime-L505-model',
                         'suprime-L527', 'suprime-L527-model',
                         'suprime-ia-v1', 'suprime-ia-v1-model',
                         'cfht-cosmos-cahk',
                         'decaps2', 'decaps2-model',
                         'dr10-deep', 'dr10-deep-model', 'ibis-color', 'ibis',
        ]
            or opt.kind.startswith('dr8-test')
            or opt.kind.startswith('dr9-test')
            or opt.kind.startswith('dr9f')
            or opt.kind.startswith('dr9g')
            or opt.kind.startswith('dr9h')
            or opt.kind.startswith('dr9i')
            or opt.kind.startswith('dr9j')
            or opt.kind.startswith('dr9-sga')
            or opt.kind.startswith('dr9-sga2')
            or opt.kind.startswith('dr9-grid')
            or opt.kind.startswith('dr9-segsize2')
            or opt.kind.startswith('dr9k')
            or opt.kind.startswith('dr9m')
            ):
            from map.views import get_layer

            layer = get_layer(opt.kind)
            print('Layer:', layer)
            if opt.queue:
                if len(opt.zoom) == 0:
                    opt.zoom = [1,2,3,4,5,6,7]
                #step = 0.1
                step = 1.
                ras = np.arange(opt.minra, opt.maxra+step, step)
                #ras = np.arange(opt.minra, opt.maxra+step, step)
                #decs = np.arange(opt.mindec, opt.maxdec+step, step)
                decs = [opt.mindec, opt.maxdec]
                for zoom in opt.zoom:
                    for declo,dechi in zip(decs, np.clip(decs[1:], opt.mindec, opt.maxdec)):
                        #rstep = step / np.maximum(0.05, np.cos(np.deg2rad((declo+dechi)/2.)))
                        #ras = np.arange(opt.minra, opt.maxra+rstep, rstep)
                        for ralo,rahi in zip(ras, np.clip(ras[1:], opt.minra, opt.maxra)):
                            cmd = ('python3 render-tiles.py --kind %s --bands %s --scale --minra %f --maxra %f --mindec %f --maxdec %f -z %i' %
                                   (opt.kind, opt.bands, ralo, rahi, declo, dechi, zoom))
                            if opt.queue_args:
                                cmd = cmd + ' ' + opt.queue_args
                            print(cmd)
                sys.exit(0)

            if len(opt.zoom) == 0:
                opt.zoom = [1]

            for scale in opt.zoom:
                B = layer.get_bricks_for_scale(scale)
                print(len(B), 'bricks for scale', scale)
                if opt.touching:
                    B.cut((B.dec2 >= opt.mindec) * (B.dec1 <= opt.maxdec))
                    print(len(B), 'touching Dec range')
                    B.cut((B.ra2 >= opt.minra) * (B.ra1 <= opt.maxra))
                    print(len(B), 'touching RA range')
                else:
                    B.cut((B.dec >= opt.mindec) * (B.dec <= opt.maxdec))
                    print(len(B), 'in Dec range')
                    B.cut((B.ra  >= opt.minra)  * (B.ra  <= opt.maxra))
                    print(len(B), 'in RA range')

                bands = opt.bands

                has = {}
                for band in bands:
                    if 'has_%s' % band in B.get_columns():
                        has[band] = B.get('has_%s' % band)
                    else:
                        # assume yes
                        has[band] = np.ones(len(B), bool)

                # Run one scale at a time
                args = []
                for ibrick,brick in enumerate(B):
                    for band in bands:
                        if has[band][ibrick]:
                            args.append((layer, brick, band, scale, opt.ignore, opt.deps))
                print(len(args), 'bricks for scale', scale)
                mp.map(_layer_get_filename, args)

            sys.exit(0)
                
        
        if (opt.kind in ['eboss', 'ps1']
            or 'dr8b' in opt.kind
            or 'dr8c' in opt.kind
            or 'dr8i' in opt.kind):

            from map.views import get_survey, get_layer
            surveyname = opt.kind
            for suffix in ['-model', '-resid']:
                if surveyname.endswith(suffix):
                    surveyname = surveyname[:-len(suffix)]

            survey = get_survey(surveyname)

            print('Survey:', survey)
            print('  cache_dir:', survey.cache_dir)

            B = survey.get_bricks()
            print(len(B), 'bricks')
            B.cut((B.dec >= opt.mindec) * (B.dec < opt.maxdec))
            print(len(B), 'in Dec range')
            B.cut((B.ra  >= opt.minra)  * (B.ra  < opt.maxra))
            print(len(B), 'in RA range')

            print('Resulting range: RA', B.ra.min(), 'to', B.ra.max(),
                  'Dec', B.dec.min(), 'to', B.dec.max())
            
            # find all image files
            filetype = 'image'
            model = False
            if '-model' in opt.kind:
                model = True
                filetype = 'model'

            bands = opt.bands

            layer = get_layer(opt.kind)

            has = {}
            for band in bands:
                if 'has_%s' % band in B.get_columns():
                    has[band] = B.get('has_%s' % band)
                else:
                    # assume yes
                    has[band] = np.ones(len(B), bool)

            for scale in opt.zoom:
                args = []
                for ibrick,brick in enumerate(B):
                    for band in bands:
                        if not has[band][ibrick]:
                            print('Brick', brick.brickname, 'does not have', band)
                            continue
                        args.append((layer, brick, band, scale, opt.ignore, False))
                mp.map(_layer_get_filename, args)
                
            sys.exit(0)

        elif opt.kind == 'sdss2':
            layer = get_layer(opt.kind)
            bands = 'gri'
            scales = opt.zoom
            if len(scales) == 0:
                scales = list(range(1,8))
            for scale in scales:
                #maxscale = 7
                bricks = layer.get_bricks_for_scale(scale)
                print('Got', len(bricks), 'bricks for scale', scale)
                bricks.cut((bricks.dec > opt.mindec) * (bricks.dec <= opt.maxdec) *
                           (bricks.ra  > opt.minra ) * (bricks.ra  <= opt.maxra))
                print('Cut to', len(bricks), 'bricks within RA,Dec box')

                for ibrick,brick in enumerate(bricks):
                    for band in bands:
                        print('Scaling brick', ibrick, 'of', len(bricks), 'scale', scale, 'brick', brick.brickname, 'band', band)
                        fn = layer.get_filename(brick, band, scale)
            sys.exit(0)

        if opt.kind in ['unwise-w1w2', 'unwise-neo2']:
            # scaledir = opt.kind
            # basedir = settings.DATA_DIR
            # dirnm = os.path.join(basedir, 'scaled', scaledir)
            # B = fits_table(os.path.join(basedir, 'unwise-bricks.fits'))
            layer = get_layer(opt.kind)
            B = layer.get_bricks()
            print(len(B), 'unWISE tiles')
            for b in B:
                for band in ['1','2']:
                    for scale in [1,2,3,4,5,6,7]:
                        print('Get brick', b.brickname, 'band', band, 'scale', scale)
                        layer.get_filename(b, band, scale)

        else:
            assert(False)


    if opt.bricks_exist:
        from map.views import get_survey

        surveyname = opt.kind
        filetype = 'image'

        survey = get_survey(surveyname)
        print('Survey:', type(survey), survey)
        
        B = survey.get_bricks()
        print(len(B), 'bricks')
        B.cut((B.dec >= opt.mindec) * (B.dec < opt.maxdec))
        print(len(B), 'in Dec range')
        B.cut((B.ra  >= opt.minra)  * (B.ra  < opt.maxra))
        print(len(B), 'in RA range')

        # find all image files
        bands = opt.bands

        has_band = {}
        for b in bands:
            B.set('has_%s' % b, np.zeros(len(B), bool))
            has_band[b] = B.get('has_%s' % b)
        exists = np.zeros(len(B), bool)

        for i,brick in enumerate(B.brickname):
            found = False
            for band in bands:
                fn = survey.find_file(filetype, brick=brick, band=band)
                ex = os.path.exists(fn)
                print('Brick', brick, 'band', band, 'exists?', ex, 'file', fn)
                has_band[band][i] = ex
                if ex:
                    found = True
            exists[i] = found

        B.cut(exists)
        B.writeto('bricks-exist-%s.fits' % opt.kind)
        sys.exit(0)

    from map.views import get_survey
    surveyname = opt.kind
    if surveyname.endswith('-model'):
        surveyname = surveyname.replace('-model','')
    if surveyname.endswith('-resid'):
        surveyname = surveyname.replace('-resid','')
    survey = get_survey(surveyname)

    if len(opt.zoom) == 0:
        opt.zoom = [13]
    
    if opt.near:
        if opt.kind == 'sdss':
            B = fits_table(os.path.join(settings.DATA_DIR, 'bricks-sdssco.fits'))
        else:
            B = survey.get_bricks()
        print(len(B), 'bricks')

    #if opt.scale:
    #    opt.near_ccds = True
    ccdsize = None

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
            print(len(C), 'SDSS fields')

        else:
            C = survey.get_ccds()
            print(len(C), 'CCDs')
            ccdsize = 0.2

    if opt.x is not None:
        opt.x0 = opt.x
        opt.x1 = opt.x + 1
    if opt.y is not None:
        opt.y0 = opt.y
        opt.y1 = opt.y + 1

    if opt.coadd and opt.kind == 'galex':
        layer = GalexLayer('galex')
        
        # base-level (coadd) bricks
        B = layer.get_bricks()
        print(len(B), 'bricks')
        B.cut((B.dec >= opt.mindec) * (B.dec < opt.maxdec))
        print(len(B), 'in Dec range')
        B.cut((B.ra  >= opt.minra)  * (B.ra  < opt.maxra))
        print(len(B), 'in RA range')

        pat = layer.get_scaled_pattern()
        tempfiles = []
        for b in B:
            for band in ['n','f']:
                fn = pat % dict(scale=0, band=band, brickname=b.brickname)
                layer.create_coadd_image(b, band, 0, fn, tempfiles=tempfiles)
            for fn in tempfiles:
                os.unlink(fn)
        sys.exit(0)

    if opt.coadd and opt.kind == 'sdss':
        from legacypipe.survey import wcs_for_brick
        from map.views import trymakedirs

        #B = survey.get_bricks()
        B = fits_table(os.path.join(settings.DATA_DIR, 'sdss2', 'bricks-sdssco.fits'))
        print(len(B), 'bricks')
        B.cut((B.dec >= opt.mindec) * (B.dec < opt.maxdec))
        print(len(B), 'in Dec range')
        B.cut((B.ra  >= opt.minra)  * (B.ra  < opt.maxra))
        print(len(B), 'in RA range')

        if opt.queue:
            # ~ square-degree tiles
            # RA slices
            rr = np.arange(opt.minra , opt.maxra +1)
            dd = np.arange(opt.mindec, opt.maxdec+1)
            for rlo,rhi in zip(rr, rr[1:]):
                for dlo,dhi in zip(dd, dd[1:]):
                    print('time python3 render-tiles.py --kind sdss --coadd --minra %f --maxra %f --mindec %f --maxdec %f' % (rlo, rhi, dlo, dhi))
            sys.exit(0)

        if opt.grass:
            basedir = settings.DATA_DIR
            codir = os.path.join(basedir, 'coadd', 'sdssco')
            rr,dd = [],[]
            exist = []
            for i,b in enumerate(B):
                print('Brick', b.brickname,)
                fn = os.path.join(codir, b.brickname[:3], 'sdssco-%s-%s.fits' % (b.brickname, 'r'))
                print('-->', fn,)
                if not os.path.exists(fn):
                    print()
                    continue
                print('found')
                rr.append(b.ra)
                dd.append(b.dec)
                exist.append(i)

            exist = np.array(exist)
            B.cut(exist)
            B.writeto('bricks-sdssco-exist.fits')

            import pylab as plt
            plt.clf()
            plt.plot(rr, dd, 'k.')
            plt.title('SDSS coadd tiles')
            plt.savefig('sdss.png')
            sys.exit(0)

        basedir = settings.DATA_DIR
        codir = os.path.join(basedir, 'coadd', 'sdssco')
        for b in B:
            print('Brick', b.brickname)
            wcs = wcs_for_brick(b, W=2400, H=2400, pixscale=0.396)
            #bands = 'gri'
            bands = 'z'

            dirnm = os.path.join(codir, b.brickname[:3])
            fns = [os.path.join(dirnm, 'sdssco-%s-%s.fits' % (b.brickname, band))
                   for band in bands]

            hdr = fitsio.FITSHDR()
            hdr['SURVEY'] = 'SDSS'
            wcs.add_to_header(hdr)

            if all([os.path.exists(fn) for fn in fns]):
                print('Already exist')
                continue

            from map.oldviews import map_sdss

            ims = map_sdss(req, 1, 0, 0, 0, get_images=True, wcs=wcs, ignoreCached=True,
                           forcescale=0, bands=bands)
            if ims is None:
                print('No overlap')
                continue
            trymakedirs(os.path.join(dirnm, 'xxx'))
            for fn,band,im in zip(fns,bands, ims):
                fitsio.write(fn, im, header=hdr, clobber=True)
                print('Wrote', fn)

            # Also write scaled versions
            # dirnm = os.path.join(basedir, 'scaled', 'sdssco')
            # scalepat = os.path.join(dirnm, '%(scale)i%(band)s', '%(brickname).3s', 'sdssco-%(brickname)s-%(band)s.fits')
            # for im,band in zip(ims,bands):
            #     scalekwargs = dict(band=band, brick=b.brickid, brickname=b.brickname)
            #     imwcs = wcs
            #     for scale in range(1, 7):
            #         print('Writing scale level', scale)
            #         im,imwcs,sfn = get_scaled(scalepat, scalekwargs, scale, None,
            #                                   wcs=imwcs, img=im, return_data=True)
        sys.exit(0)


    for zoom in opt.zoom:
        N = 2**zoom
        if opt.y1 is None:
            y1 = N
        else:
            y1 = opt.y1

        if opt.x0 is None:
            opt.x0 = 0
        x1 = opt.x1
        if x1 is None:
            x1 = N

        if opt.split:
            decsplit = 32.
            y = 2.**zoom/(2.*np.pi) * (np.pi - np.log(np.tan(np.pi/4. + np.deg2rad(decsplit)/2.)))
            y = int(y)
            opt.y0 = y
            y1 = y+1

        # Find grid of Ra,Dec tile centers and select the ones near DECaLS bricks.
        rr,dd = [],[]
        yy = np.arange(opt.y0, y1)
        xx = np.arange(opt.x0, x1)

        if opt.grass:
            import pylab as plt
            tileexists = np.zeros((len(yy),len(xx)), bool)

            

            basedir = settings.DATA_DIR
            ver = tileversions[opt.kind][-1]
            tiledir = os.path.join(basedir, 'tiles', opt.kind, '%i'%ver, '%i'%zoom)
            for dirpath,dirnames,filenames in os.walk(tiledir):
                # change walk order
                dirnames.sort()
                if len(filenames) == 0:
                    continue
                print('Dirpath', dirpath)
                #print 'Dirnames', dirnames
                #print 'Filenames', filenames

                # check for symlinks
                if False:
                    fns = []
                    for fn in filenames:
                        fullfn = os.path.join(tiledir, dirpath, fn)
                        if os.path.isfile(fullfn) and not os.path.islink(fullfn):
                            fns.append(fn)
                    print(len(fns), 'of', len(filenames), 'are files (not symlinks)')
                    filenames = fns

                x = os.path.basename(dirpath)
                x = int(x)
                #print 'x', x

                yy = [int(fn.replace('.jpg','')) for fn in filenames]
                #print 'yy', yy
                print(len(yy), 'tiles')
                for y in yy:
                    tileexists[y - opt.y0, x - opt.x0] = True
            plt.clf()
            plt.imshow(tileexists, interpolation='nearest', origin='upper',
                       vmin=0, vmax=1, cmap='gray')
            fn = 'exist-%s-z%02i' % (opt.kind, zoom)
            plt.savefig(fn+'.png')
            fitsio.write(fn+'.fits', tileexists, clobber=True)
            print('Wrote', fn+'.png and', fn+'.fits')

            continue

        if not opt.all:
            print('Finding overlapping tiles;', len(yy), 'y', len(xx), 'x')
            for y in yy:
                wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, 0, y)
                r,d = wcs.get_center()
                dd.append(d)
            # Mercator: delta-RA between tiles is the same at all y/Dec values.
            wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, opt.x0, 0)
            ra_a,d = wcs.get_center()
            if len(xx) < 2:
                dra = 0.
            else:
                wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, opt.x0+1, 0)
                ra_b,d = wcs.get_center()
                dra = ra_b - ra_a
            rr = ra_a + dra * np.arange(len(xx))
            # rr2 = []
            # for x in xx:
            #     wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, x, 0)
            #     r,d = wcs.get_center()
            #     rr2.append(r)
            # rr2 = np.array(rr2)
            # print('rr2', rr2)
            # print('rr', rr)

            dd = np.array(dd)
            if len(dd) > 1:
                tilesize = max(np.abs(np.diff(dd)))
                print('Tile size:', tilesize)
            else:
                if opt.near_ccds or opt.near:
                    try:
                        wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, 0, opt.y0+1)
                        r2,d2 = wcs.get_center()
                    except:
                        wcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, 0, opt.y0-1)
                        r2,d2 = wcs.get_center()
                    tilesize = np.abs(dd[0] - d2)
                    print('Tile size:', tilesize)
                else:
                    tilesize = 180.
            I = np.flatnonzero((dd >= opt.mindec) * (dd <= opt.maxdec))
            print('Keeping', len(I), 'Dec points between', opt.mindec, 'and', opt.maxdec)
            if len(I) == 0:
                continue
            dd = dd[I]
            yy = yy[I]

            if opt.near_ccds:
                margin = tilesize + ccdsize
                I = np.flatnonzero((dd > C.dec.min()-margin) * (dd < C.dec.max()+margin))
                if len(I) == 0:
                    print('No Dec points within range of CCDs')
                    continue
                dd = dd[I]
                yy = yy[I]
                print('Keeping', len(I), 'Dec points within range of CCDs: Dec',
                      dd.min(), dd.max())

            I = np.flatnonzero((rr >= opt.minra) * (rr <= opt.maxra))
            print('Keeping', len(I), 'RA points between', opt.minra, 'and', opt.maxra)
            if len(I) == 0:
                continue
            rr = rr[I]
            xx = xx[I]
            
            print(len(rr), 'RA points x', len(dd), 'Dec points')
            print('x tile range:', xx.min(), xx.max(), 'y tile range:', yy.min(), yy.max())


        from astrometry.libkd.spherematch import trees_match, tree_build_radec
        Bkd = None
        if opt.near:
            Bkd = tree_build_radec(ra=B.ra, dec=B.dec)
        Ckd = None
        if opt.near_ccds:
            Ckd = tree_build_radec(ra=C.ra, dec=C.dec)

        if len(yy) < len(xx):
            for dec,y in zip(dd, yy):
                print()
                print('Y row', y, 'Dec', dec)
                run_xy_set(zoom, xx, y+np.zeros_like(xx), rr, dec+np.zeros_like(rr), opt, Bkd, Ckd,
                           ccdsize, tilesize, mp)
        else:
            for ra,x in zip(rr, xx):
                print()
                print('X col', x, 'RA', ra)
                run_xy_set(zoom, x+np.zeros_like(yy), yy, ra+np.zeros_like(dd), dd, opt, Bkd, Ckd,
                           ccdsize, tilesize, mp)

        # if opt.grass:
        #     plt.clf()
        #     plt.plot(tileexists, interpolation='nearest', origin='lower',
        #              vmin=0, vmax=1, cmap='gray')
        #     plt.savefig('%s-z%02i-exists.png' % (opt.kind, zoom))


def run_xy_set(zoom, xx, yy, rr, dd, opt, Bkd, Ckd, ccdsize, tilesize, mp):
    if opt.queue:
        if 'decaps2' in opt.kind:
            layer = get_layer(opt.kind)
            if zoom >= layer.nativescale:
                oldscale = 0
            else:
                oldscale = (layer.nativescale - zoom)
                oldscale = np.clip(oldscale, layer.minscale, layer.maxscale)
            x = 0
            wcs, W, H, zoomscale, z,xi,yi = get_tile_wcs(zoom, x, y)
            newscale = layer.get_scale(zoom, 0, y, wcs)
            if oldscale == newscale:
                print('Oldscale = newscale = ', oldscale)
                return
        cmd = 'python3 -u render-tiles.py --zoom %i --y0 %i --y1 %i --kind %s --mindec %f --maxdec %f' % (zoom, y, y+1, opt.kind, opt.mindec, opt.maxdec)
        cmd += ' --threads 32'
        if opt.near_ccds:
            cmd += ' --near-ccds'
        if opt.all:
            cmd += ' --all'
        if opt.ignore:
            cmd += ' --ignore'
        print(cmd)
        return

    if opt.near:
        kd = tree_build_radec(ra=rr, dec=dd)
        radius = np.deg2rad(0.25 + tilesize)
        I,J,dist = trees_match(kd, Bkd, radius, nearest=True)
        if len(I) == 0:
            print('No matches to bricks')
            return
        keep = np.zeros(len(rr), bool)
        keep[I] = True

        if opt.fix:
            # UGH, in a previous version I had rr,dd swapped in this function call!
            # Cut the set "I" computed above down to only those that *weren't* previously
            # computed.
            kd_old = tree_build_radec(ra=dd, dec=rr)
            I_old,_,_ = trees_match(kd_old, Bkd, radius, nearest=True)
            print('Full set:', len(I), 'tiles in row/col')
            print('Old set:', len(I_old))
            keep[I_old] = False

        print('Keeping', sum(keep), 'tiles in row/col')
        xx = xx[keep]
        yy = yy[keep]

    elif opt.near_ccds:
        #d = dd[iy]
        #print('RA range of tiles:', rr.min(), rr.max())
        #print('Dec of tile row:', d)
        #I,J,dist = match_radec(rr, d+np.zeros_like(rr), C.ra, C.dec, ccdsize + tilesize, nearest=True)
        kd = tree_build_radec(ra=rr, dec=dd)
        radius = np.deg2rad(ccdsize + tilesize)
        I,J,dist = trees_match(kd, Ckd, radius, nearest=True)
        if len(I) == 0:
            print('No matches to CCDs')
            return
        keep = np.zeros(len(rr), bool)
        keep[I] = True
        print('Keeping', sum(keep), 'tiles in row/col')
        xx = xx[keep]
        yy = yy[keep]

    args = []
    for xi,yi in zip(xx,yy):
        args.append((opt.kind, zoom, xi, yi, opt.ignore, False))
    print('Rendering', len(args), 'tiles in row/col')
    mp.map(_bounce_one_tile, args, chunksize=min(100, max(1, int(len(args)/opt.threads))))
    #mp.map(_one_tile, args, chunksize=min(100, max(1, int(len(args)/opt.threads))))
    print('Rendered', len(args), 'tiles')

        
if __name__ == '__main__':
    main()
