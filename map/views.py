import os
import tempfile

from django.shortcuts import render
from django.http import HttpResponse

from astrometry.util.util import *
from astrometry.blind.plotstuff import *

from astrometry.util.resample import *
from astrometry.util.fits import *

def index(req):
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
    
    return render(req, 'index.html',
                  dict(ra=ra, dec=dec, lat=lat, long=long, zoom=zoom))

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

def map_coadd(req, zoom, x, y):
    from desi.common import *
    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)
    print 'WCS size', W,H
    
    ok,r,d = wcs.pixelxy2radec([1,1,W,W], [1,H,H,1])
    print 'RA,Dec corners', r,d
    print 'RA range', r.min(), r.max()
    print 'Dec range', d.min(), d.max()

    D = Decals()
    B = D.get_bricks()
    I = D.bricks_touching_radec_box(B, r.min(), r.max(), d.min(), d.max())
    print len(I), 'bricks touching'
    bands = 'grz'
    rimgs = []
    for band in bands:
        rimg = np.zeros((H,W), np.float32)
        rn   = np.zeros((H,W), np.uint8)
        for brickid in B.brickid[I]:
            fn = 'tunebrick/coadd/image-%06i-%s.fits' % (brickid, band)
            print 'Reading', fn
            img = fitsio.read(fn)
            bwcs = Tan(fn, 0)
            print 'Img', img.shape, img.dtype
            print 'WCS', bwcs

            try:
                Yo,Xo,Yi,Xi,nil = resample_with_wcs(wcs, bwcs, [], 3)
            except:
                continue

            rimg[Yo,Xo] = img[Yi,Xi]
            rn  [Yo,Xo] += 1
        rimg /= np.maximum(rn, 1)
        rimgs.append(rimg)
    rgb = get_rgb(rimgs, bands)

    f,fn = tempfile.mkstemp(suffix='.jpg')
    os.close(f)
    plt.imsave(fn, rgb, origin='lower')
    f = open(fn)
    os.unlink(fn)
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
