import os
import tempfile

import simplejson

from django.shortcuts import render
from django.http import HttpResponse

from astrometry.util.util import *

from astrometry.util.resample import *
from astrometry.util.fits import *

from scipy.ndimage.filters import gaussian_filter

from decals import settings

def index(req):
    layer = req.GET.get('layer', 'decals')
    ra, dec, zoom = 244.7, 7.4, 13

    try:
        zoom = int(req.GET.get('zoom', zoom))
    except:
        pass
    try:
        ra = float(req.GET.get('ra',ra))
    except:
        pass
    try:
        dec = float(req.GET.get('dec', dec))
    except:
        pass

    lat,long = dec, 180-ra

    # Deployment:
    # tileurl = 'http://{s}.decals.thetractor.org/{id}/{z}/{x}/{y}.jpg'
    # caturl = 'http://decals.thetractor.org/{id}/{z}/{x}/{y}.cat.json'

    tileurl = '/{id}/{z}/{x}/{y}.jpg'
    caturl = '/{id}/{z}/{x}/{y}.cat.json'

    #caturl = 'http://{s}.decals.thetractor.org/{id}/{z}/{x}/{y}.cat.json'
    #tileurl = '{id}/{z}/{x}/{y}.jpg'

    polygons = ''
    if False and layer == 'decals':
        T = fits_table(os.path.join(settings.WEB_DIR, 'edr-bricks.fits'))
        print len(T), 'bricks'
        for t in T:
            rd = [(t.ra1, t.dec1), (t.ra1,t.dec2), (t.ra2,t.dec2), (t.ra2,t.dec1)]
            p = ('L.polygon([' +
                 ','.join(['[%.4f,%.4f]' % (d, 180.-r) for r,d in rd])
                 + '], {fill:false}).addTo(map);')
            polygons += p + '\n'

    baseurl = req.path + '?layer=%s&' % layer
    
    return render(req, 'index.html',
                  dict(ra=ra, dec=dec, lat=lat, long=long, zoom=zoom,
                       layer=layer, tileurl=tileurl, polygons=polygons,
                       baseurl=baseurl, caturl=caturl))

def get_tile_wcs(zoom, x, y):
    zoom = int(zoom)
    zoomscale = 2.**zoom
    x = int(x)
    y = int(y)
    if zoom < 0 or x < 0 or y < 0 or x >= zoomscale or y >= zoomscale:
        raise RuntimeError('Invalid zoom,x,y %i,%i,%i' % (zoom,x,y))

    # tile size
    zoomscale = 2.**zoom
    W,H = 256,256
    if zoom == 0:
        rx = ry = 0.5
    else:
        rx = zoomscale/2 - x
        ry = zoomscale/2 - y
    rx = rx * W
    ry = ry * H
    wcs = anwcs_create_mercator_2(180., 0., rx, ry,
                                  zoomscale, W, H, 1)
    return wcs, W, H, zoomscale, zoom,x,y

def get_scaled(scalepat, scalekwargs, scale, basefn):
    if scale <= 0:
        return basefn
    fn = scalepat % dict(scale=scale, **scalekwargs)
    if not os.path.exists(fn):
        #print 'Does not exist:', fn
        sourcefn = get_scaled(scalepat, scalekwargs, scale-1, basefn)
        #print 'Source:', sourcefn
        if sourcefn is None or not os.path.exists(sourcefn):
            print 'No source'
            return None
        I = fitsio.read(sourcefn)
        #print 'source image:', I.shape
        H,W = I.shape
        # make even size; smooth down
        if H % 2 == 1:
            I = I[:-1,:]
        if W % 2 == 1:
            I = I[:,:-1]
        im = gaussian_filter(I, 1.)
        #print 'im', im.shape
        # bin
        I2 = (im[::2,::2] + im[1::2,::2] + im[1::2,1::2] + im[::2,1::2])/4.
        #print 'I2:', I2.shape
        # shrink WCS too
        wcs = Tan(sourcefn, 0)
        # include the even size clip; this may be a no-op
        H,W = im.shape
        wcs = wcs.get_subimage(0, 0, W, H)
        subwcs = wcs.scale(0.5)
        hdr = fitsio.FITSHDR()
        subwcs.add_to_header(hdr)
        fitsio.write(fn, I2, header=hdr, clobber=True)
        #print 'Wrote', fn
    return fn


def map_cosmos_grz(req, zoom, x, y):
    return map_coadd_bands(req, zoom, x, y, 'grz', 'cosmos-grz', 'cosmos')

def map_cosmos_urz(req, zoom, x, y):
    return map_coadd_bands(req, zoom, x, y, 'urz', 'cosmos-urz', 'cosmos')

def map_decals(req, zoom, x, y):
    return map_coadd_bands(req, zoom, x, y, 'grz', 'decals', 'decals')

def map_decals_model(req, zoom, x, y):
    return map_coadd_bands(req, zoom, x, y, 'grz', 'decals-model', 'decals-model', imagetag='model')

def map_decals_pr(req, zoom, x, y):
    return map_coadd_bands(req, zoom, x, y, 'grz', 'decals-pr', 'decals',
                           rgbkwargs=dict(mnmx=(-0.3,100.), arcsinh=1.))

def map_des_stripe82(req, zoom, x, y):
    return map_coadd_bands(req, zoom, x, y, 'grz', 'des-stripe82', 'des-stripe82')

def map_des_pr(req, zoom, x, y):
    return map_coadd_bands(req, zoom, x, y, 'grz', 'des-stripe82-pr', 'des-stripe82',
                           rgbkwargs=dict(mnmx=(-0.3,100.), arcsinh=1.))

def cat_decals(req, zoom, x, y, tag='decals'):
    from desi.common import *
    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)
    basedir = os.path.join(settings.WEB_DIR, 'data')
    cachefn = os.path.join(basedir, 'cats-cache', tag, '%i/%i/%i.cat.json' % (zoom, x, y))
    if os.path.exists(cachefn):
        print 'Cached:', cachefn
        f = open(cachefn)
        return HttpResponse(f, content_type='application/json')

    ok,r,d = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                               [1,H/2,H,H,H,H/2,1,1])
    catpat = os.path.join(basedir, 'cats', tag,
                          'tractor-%(brick)06i.fits')
    D = Decals()
    B = D.get_bricks()
    I = D.bricks_touching_radec_box(B, r.min(), r.max(), d.min(), d.max())

    cat = []
    for brickid in B.brickid[I]:
        fnargs = dict(brick=brickid)
        catfn = catpat % fnargs
        if not os.path.exists(catfn):
            print 'Does not exist:', catfn
            continue
        T = fits_table(catfn)
        T.cut(T.brick_primary)
        ok,x,y = wcs.radec2pixelxy(T.ra, T.dec)
        T.cut((x > 0) * (y > 0) * (x < W) * (y < H))
        cat.append(T)
    if len(cat) == 0:
        rd = []
    else:
        cat = merge_tables(cat)
        print 'All catalogs:'
        cat.about()
        rd = zip(cat.ra, cat.dec)

    json = simplejson.dumps(dict(rd=rd))
    try:
        os.makedirs(os.path.dirname(cachefn))
    except:
        pass

    f = open(cachefn, 'w')
    f.write(json)
    f.close()
    
    f = open(cachefn)

    return HttpResponse(f, content_type='application/json')
    


def map_coadd_bands(req, zoom, x, y, bands, tag, imagedir,
                    imagetag='image2', rgbkwargs={}):
    from desi.common import *
    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)

    basedir = os.path.join(settings.WEB_DIR, 'data')

    tilefn = os.path.join(basedir, 'tiles', tag, '%i/%i/%i.jpg' % (zoom, x, y))
    if os.path.exists(tilefn):
        print 'Cached:', tilefn
        f = open(tilefn)
        return HttpResponse(f, content_type="image/jpeg")

    ok,r,d = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                               [1,H/2,H,H,H,H/2,1,1])
    # print 'RA,Dec corners', r,d
    # print 'RA range', r.min(), r.max()
    # print 'Dec range', d.min(), d.max()
    # print 'Zoom', zoom, 'pixel scale', wcs.pixel_scale()

    basepat = os.path.join(basedir, 'coadd', imagedir, imagetag + '-%(brick)06i-%(band)s.fits')
    scaled = 0
    scalepat = None
    if zoom < 14:
        scaled = (14 - zoom)
        scaled = np.clip(scaled, 1, 8)
        #print 'Scaled-down:', scaled
        dirnm = os.path.join(basedir, 'scaled', imagedir)
        scalepat = os.path.join(dirnm, imagetag + '-%(brick)06i-%(band)s-%(scale)i.fits')
        if not os.path.exists(dirnm):
            try:
                os.makedirs(dirnm)
            except:
                pass
        
    D = Decals()
    B = D.get_bricks()
    I = D.bricks_touching_radec_box(B, r.min(), r.max(), d.min(), d.max())
    #print len(I), 'bricks touching:', B.brickid[I]
    rimgs = []

    # If any problems are encountered during tile rendering, don't save
    # the results... at least it'll get fixed upon reload.
    savecache = True

    for band in bands:
        rimg = np.zeros((H,W), np.float32)
        rn   = np.zeros((H,W), np.uint8)
        for brickid in B.brickid[I]:
            fnargs = dict(brick=brickid, band=band)
            basefn = basepat % fnargs
            fn = get_scaled(scalepat, fnargs, scaled, basefn)
            #print 'Filename:', fn
            if fn is None:
                savecache = False
                continue
            if not os.path.exists(fn):
                savecache = False
                continue
            try:
                bwcs = Tan(fn, 0)
            except:
                print 'Failed to read WCS:', fn
                savecache = False
                continue

            ok,xx,yy = bwcs.radec2pixelxy(r, d)
            xx = xx.astype(np.int)
            yy = yy.astype(np.int)
            #print 'x,y', x,y
            imW,imH = int(bwcs.get_width()), int(bwcs.get_height())
            M = 10
            #print 'brick coordinates of tile: x', xx.min(), xx.max(), 'y', yy.min(), yy.max()
            xlo = np.clip(xx.min() - M, 0, imW)
            xhi = np.clip(xx.max() + M, 0, imW)
            ylo = np.clip(yy.min() - M, 0, imH)
            yhi = np.clip(yy.max() + M, 0, imH)
            #print 'brick size', imW, 'x', imH
            #print 'clipped brick coordinates: x', xlo, xhi, 'y', ylo,yhi
            if xlo >= xhi or ylo >= yhi:
                #print 'skipping'
                continue

            subwcs = bwcs.get_subimage(xlo, ylo, xhi-xlo, yhi-ylo)
            slc = slice(ylo,yhi), slice(xlo,xhi)
            try:
                f = fitsio.FITS(fn)[0]
                img = f[slc]
            except:
                print 'Failed to read image and WCS:', fn
                savecache = False
                continue
            #print 'Subimage shape', img.shape
            #print 'Sub-WCS shape', subwcs.get_height(), subwcs.get_width()
            try:
                Yo,Xo,Yi,Xi,nil = resample_with_wcs(wcs, subwcs, [], 3)
            except OverlapError:
                #print 'Resampling exception'
                #import traceback
                #traceback.print_exc()
                continue

            # print 'Resampling', len(Yo), 'pixels'
            # print 'out range x', Xo.min(), Xo.max(), 'y', Yo.min(), Yo.max()
            # print 'in  range x', Xi.min(), Xi.max(), 'y', Yi.min(), Yi.max()
            
            rimg[Yo,Xo] += img[Yi,Xi]
            rn  [Yo,Xo] += 1
        rimg /= np.maximum(rn, 1)
        rimgs.append(rimg)
        #print 'Band', band, ': total of', rn.sum(), 'pixels'
    rgb = get_rgb(rimgs, bands, **rgbkwargs)

    try:
        os.makedirs(os.path.dirname(tilefn))
    except:
        pass

    # plt.figure(figsize=(2.56, 2.56))
    # plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
    # plt.imshow(rgb, interpolation='nearest')
    # plt.axis('off')
    # plt.text(128, 128, 'z%i,(%i,%i)' % (zoom, x, y), color='red', ha='center', va='center')
    # plt.savefig(tilefn)

    if not savecache:
        f,tilefn = tempfile.mkstemp(suffix='.jpg')
        os.close(f)
        #print 'Not caching file... saving to', tilefn

    plt.imsave(tilefn, rgb)
    f = open(tilefn)
    if not savecache:
        os.unlink(tilefn)

    return HttpResponse(f, content_type="image/jpeg")
    
            
    
def map_image(req, zoom, x, y):
    from astrometry.blind.plotstuff import Plotstuff

    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)

    plot = Plotstuff(size=(256,256), outformat='jpg')
    plot.wcs = wcs
    plot.color = 'gray'

    grid = 30
    if zoom >= 2:
        grid = 10
    if zoom >= 4:
        grid = 5
    if zoom >= 6:
        grid = 1
    if zoom >= 8:
        grid = 0.5
    if zoom >= 10:
        grid = 0.1
    plot.plot_grid(grid*2, grid, ralabelstep=grid*2, declabelstep=grid)

    plot.color = 'white'
    plot.apply_settings()
    ok,r,d = wcs.pixelxy2radec(W/2+0.5, H/2+0.5)
    plot.text_xy(W/2, H/2, 'zoom%i (%i,%i)' % (zoom,x,y))
    plot.stroke()
    plot.color = 'green'
    plot.lw = 2.
    plot.alpha = 0.3
    plot.apply_settings()
    M = 5
    plot.polygon([(M,M),(W-M,M),(W-M,H-M),(M,H-M)])
    plot.close_path()
    plot.stroke()
    
    f,fn = tempfile.mkstemp()
    os.close(f)
    plot.write(fn)
    f = open(fn)
    os.unlink(fn)
    return HttpResponse(f, content_type="image/jpeg")
