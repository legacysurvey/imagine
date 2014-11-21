import os
import tempfile

from django.shortcuts import render
from django.http import HttpResponse

from astrometry.util.util import *
from astrometry.blind.plotstuff import *

from astrometry.util.resample import *
from astrometry.util.fits import *

from scipy.ndimage.filters import gaussian_filter

from decals import settings

def index(req):
    layer = req.GET.get('layer', 'image')
    ra, dec, zoom = 242.0, 7.0, 11

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

    tileurl = 'http://{s}.decals.thetractor.org/{id}/{z}/{x}/{y}.jpg'
    #tileurl = '{id}/{z}/{x}/{y}.jpg'
    
    return render(req, 'index.html',
                  dict(ra=ra, dec=dec, lat=lat, long=long, zoom=zoom,
                       layer=layer, tileurl=tileurl))

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
        print 'Does not exist:', fn
        sourcefn = get_scaled(scalepat, scalekwargs, scale-1, basefn)
        print 'Source:', sourcefn
        if sourcefn is None or not os.path.exists(sourcefn):
            print 'No source'
            return None
        I = fitsio.read(sourcefn)
        print 'source image:', I.shape
        H,W = I.shape
        # make even size; smooth down
        if H % 2 == 1:
            I = I[:-1,:]
        if W % 2 == 1:
            I = I[:,:-1]
        im = gaussian_filter(I, 1.)
        print 'im', im.shape
        # bin
        I2 = (im[::2,::2] + im[1::2,::2] + im[1::2,1::2] + im[::2,1::2])/4.
        print 'I2:', I2.shape
        # shrink WCS too
        wcs = Tan(sourcefn, 0)
        # include the even size clip; this may be a no-op
        H,W = im.shape
        wcs = wcs.get_subimage(0, 0, W, H)
        subwcs = wcs.scale(0.5)
        hdr = fitsio.FITSHDR()
        subwcs.add_to_header(hdr)
        fitsio.write(fn, I2, header=hdr)
        print 'Wrote', fn
    return fn


def map_coadd(req, zoom, x, y):
    return map_coadd_bands(req, zoom, x, y, 'grz', 'coadd-grz')

def map_coadd_urz(req, zoom, x, y):
    return map_coadd_bands(req, zoom, x, y, 'urz', 'coadd-urz')


def map_coadd_bands(req, zoom, x, y, bands, tag):
    from desi.common import *
    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)

    basedir = os.path.join(settings.WEB_DIR, 'decals-web')

    tilefn = os.path.join(basedir, 'tiles-%s' % tag, '%i/%i/%i.jpg' % (zoom, x, y))
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

    basepat = os.path.join(settings.WEB_DIR, 'cosmos/coadd/image2-%(brick)06i-%(band)s.fits')
    scaled = 0
    scalepat = None
    if zoom < 14:
        scaled = (14 - zoom)
        scaled = np.clip(scaled, 1, 8)
        #print 'Scaled-down:', scaled
        dirnm = os.path.join(basedir, 'scaled-'+tag)
        scalepat = os.path.join(dirnm, 'image2-%(brick)06i-%(band)s-%(scale)i.fits')
        if not os.path.exists(dirnm):
            try:
                os.makedirs(dirnm)
            except:
                pass
        
    D = Decals()
    B = D.get_bricks()
    I = D.bricks_touching_radec_box(B, r.min(), r.max(), d.min(), d.max())
    print len(I), 'bricks touching:', B.brickid[I]
    rimgs = []
    for band in bands:
        rimg = np.zeros((H,W), np.float32)
        rn   = np.zeros((H,W), np.uint8)
        for brickid in B.brickid[I]:
            fnargs = dict(brick=brickid, band=band)
            basefn = basepat % fnargs
            fn = get_scaled(scalepat, fnargs, scaled, basefn)
            print 'Filename:', fn
            if fn is None:
                continue
            if not os.path.exists(fn):
                continue
            try:
                bwcs = Tan(fn, 0)
            except:
                print 'Failed to read WCS:', fn
                continue

            ok,xx,yy = bwcs.radec2pixelxy(r, d)
            xx = xx.astype(np.int)
            yy = yy.astype(np.int)
            #print 'x,y', x,y
            imW,imH = bwcs.get_width(), bwcs.get_height()
            M = 10
            xlo = np.clip(xx.min() - M, 0, imW)
            xhi = np.clip(xx.max() + M, 0, imW)
            ylo = np.clip(yy.min() - M, 0, imH)
            yhi = np.clip(yy.max() + M, 0, imH)
            if xlo >= xhi or ylo >= yhi:
                continue

            subwcs = bwcs.get_subimage(xlo, ylo, xhi-xlo, yhi-ylo)
            slc = slice(ylo,yhi), slice(xlo,xhi)
            try:
                f = fitsio.FITS(fn)[0]
                img = f[slc]
            except:
                print 'Failed to read image and WCS:', fn
                continue
            try:
                Yo,Xo,Yi,Xi,nil = resample_with_wcs(wcs, subwcs, [], 3)
            except:
                continue

            rimg[Yo,Xo] = img[Yi,Xi]
            rn  [Yo,Xo] += 1
        rimg /= np.maximum(rn, 1)
        rimgs.append(rimg)
    rgb = get_rgb(rimgs, bands)

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
    
    plt.imsave(tilefn, rgb)
    f = open(tilefn)
    return HttpResponse(f, content_type="image/jpeg")
    
            
    
def map_image(req, zoom, x, y):

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
