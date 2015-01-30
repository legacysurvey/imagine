import os

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseNotModified

from decals import settings


# We add a version number to each layer, to allow long cache times
# for the tile JPEGs.  Increment this version to invalidate
# client-side caches.

tileversions = {
    'decals': [1,],
    'decals-model': [1,],
    'decals-pr': [1,],
    'des-stripe82': [1,],
    'des-pr': [1,],
    }

oneyear = (3600 * 24 * 365)

def send_file(fn, content_type, unlink=False, modsince=None, expires=3600):
    import datetime
    '''
    modsince: If-Modified-Since header string from the client.
    '''
    st = os.stat(fn)
    f = open(fn)
    if unlink:
        os.unlink(fn)
    # file was last modified...
    lastmod = datetime.datetime.fromtimestamp(st.st_mtime)

    if modsince:
        #print 'If-modified-since:', modsince #Sat, 22 Nov 2014 01:12:39 GMT
        ifmod = datetime.datetime.strptime(modsince, '%a, %d %b %Y %H:%M:%S %Z')
        #print 'Parsed:', ifmod
        #print 'Last mod:', lastmod
        dt = (lastmod - ifmod).total_seconds()
        if dt < 1:
            return HttpResponseNotModified()

    res = HttpResponse(f, content_type=content_type)
    # res['Cache-Control'] = 'public, max-age=31536000'
    res['Content-Length'] = st.st_size
    # expires in an hour?
    now = datetime.datetime.utcnow()
    then = now + datetime.timedelta(0, expires, 0)
    timefmt = '%a, %d %b %Y %H:%M:%S GMT'
    res['Expires'] = then.strftime(timefmt)
    res['Last-Modified'] = lastmod.strftime(timefmt)
    return res

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

    lat,lng = dec, 180-ra

    # Deployment: http://{s}.DOMAIN/{id}/{ver}/{z}/{x}/{y}.jpg

    url = req.build_absolute_uri('/') + '{id}/{ver}/{z}/{x}/{y}.jpg'
    tileurl = url.replace('://', '://{s}.')
    caturl = '/{id}/{ver}/{z}/{x}/{y}.cat.json'

    #caturl = tileurl.replace('.jpg', '.cat.json')
    #tileurl = '/{id}/{z}/{x}/{y}.jpg'
    #caturl = '/{id}/{z}/{x}/{y}.cat.json'

    bricksurl = '/bricks/?north={north}&east={east}&south={south}&west={west}'
    ccdsurl = '/ccds/?north={north}&east={east}&south={south}&west={west}'

    baseurl = req.path + '?layer=%s&' % layer
    
    return render(req, 'index.html',
                  dict(ra=ra, dec=dec, lat=lat, long=lng, zoom=zoom,
                       layer=layer, tileurl=tileurl,
                       baseurl=baseurl, caturl=caturl, bricksurl=bricksurl,
                       ccdsurl=ccdsurl,
                       showBricks='bricks' in req.GET,
                       showCcds='ccds' in req.GET,
                       ))

def get_tile_wcs(zoom, x, y):
    from astrometry.util.util import anwcs_create_mercator_2

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
    from scipy.ndimage.filters import gaussian_filter
    import fitsio
    from astrometry.util.util import Tan

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

        import tempfile
        f,tmpfn = tempfile.mkstemp(suffix='.fits.tmp', dir=os.path.dirname(fn))
        os.close(f)
        
        fitsio.write(tmpfn, I2, header=hdr, clobber=True)
        os.rename(tmpfn, fn)
        #print 'Wrote', fn
    return fn


# def map_cosmos_grz(req, zoom, x, y):
#     return map_coadd_bands(req, zoom, x, y, 'grz', 'cosmos-grz', 'cosmos')
# 
# def map_cosmos_urz(req, zoom, x, y):
#     return map_coadd_bands(req, zoom, x, y, 'urz', 'cosmos-urz', 'cosmos')

def map_decals(req, ver, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz', 'decals', 'decals')

def map_decals_model(req, ver, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz',
                           'decals-model', 'decals-model', imagetag='model')

def map_decals_pr(req, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz', 'decals-pr', 'decals',
                           rgbkwargs=dict(mnmx=(-0.3,100.), arcsinh=1.))

def map_des_stripe82(req, ver, zoom, x, y):
    return map_coadd_bands(req, zoom, x, y, 'grz', 'des-stripe82', 'des-stripe82')

def map_des_pr(req, ver, zoom, x, y):
    return map_coadd_bands(req, zoom, x, y, 'grz', 'des-stripe82-pr', 'des-stripe82',
                           rgbkwargs=dict(mnmx=(-0.3,100.), arcsinh=1.))

def brick_list(req):
    import simplejson
    from desi.common import Decals

    north = float(req.GET['north'])
    south = float(req.GET['south'])
    east  = float(req.GET['east'])
    west  = float(req.GET['west'])
    #print 'N,S,E,W:', north, south, east, west

    D = Decals()
    B = D.get_bricks()
    I = D.bricks_touching_radec_box(B, east, west, south, north)
    # HACK -- limit result size...
    if len(I) > 10000:
        return HttpResponse(simplejson.dumps(dict(bricks=[])),
                            content_type='application/json')
    #I = I[:1000]
    bricks = []
    for b in B[I]:
        # brick overlap margin:
        #mdec = (0.262 * 20 / 3600.)
        #mra = mdec / np.cos(np.deg2rad(b.dec))
        mra = mdec = 0.
        bricks.append(dict(name=b.brickname,
                           poly=[[b.dec1-mdec, 180.-(b.ra1-mra)],
                                 [b.dec2+mdec, 180.-(b.ra1-mra)],
                                 [b.dec2+mdec, 180.-(b.ra2+mra)],
                                 [b.dec1-mdec, 180.-(b.ra2+mra)],
                                 #[b.dec1-mdec, 180.-(b.ra1-mra)]
                                 ]))

    return HttpResponse(simplejson.dumps(dict(bricks=bricks)),
                        content_type='application/json')

ccdtree = None
CCDs = None

def ccd_list(req):
    import simplejson
    from desi.common import Decals
    from astrometry.libkd.spherematch import tree_build_radec, tree_search_radec
    from astrometry.util.starutil_numpy import degrees_between
    from astrometry.util.util import Tan
    import numpy as np
    global ccdtree
    global CCDs

    north = float(req.GET['north'])
    south = float(req.GET['south'])
    east  = float(req.GET['east'])
    west  = float(req.GET['west'])
    #print 'N,S,E,W:', north, south, east, west

    if ccdtree is None:
        D = Decals()
        CCDs = D.get_ccds()
        ccdtree = tree_build_radec(CCDs.ra, CCDs.dec)

    dec = (north + south) / 2.
    c = (np.cos(np.deg2rad(east)) + np.cos(np.deg2rad(west))) / 2.
    s = (np.sin(np.deg2rad(east)) + np.sin(np.deg2rad(west))) / 2.
    ra  = np.rad2deg(np.arctan2(s, c))

    # image size
    radius = np.hypot(2048, 4096) * 0.262/3600. / 2.
    # RA,Dec box size
    radius = radius + degrees_between(east, north, west, south) / 2.

    J = tree_search_radec(ccdtree, ra, dec, radius)

    # HACK -- limit result size...
    J = J[:1000]

    ccds = []
    for c in CCDs[J]:
        wcs = Tan(*[float(x) for x in [
            c.ra_bore, c.dec_bore, c.crpix1, c.crpix2, c.cd1_1, c.cd1_2,
            c.cd2_1, c.cd2_2, c.width, c.height]])
        #x = np.array([1, 1, c.width, c.width, 1])
        #y = np.array([1, c.height, c.height, 1, 1])
        x = np.array([1, 1, c.width, c.width])
        y = np.array([1, c.height, c.height, 1])
        r,d = wcs.pixelxy2radec(x, y)
        ccds.append(dict(name='%i-%s-%s' % (c.expnum, c.extname, c.filter),
                         poly=zip(d, 180.-r)))

    return HttpResponse(simplejson.dumps(dict(ccds=ccds)),
                        content_type='application/json')
    
def ccd_detail(req, ccd):
    #ccd = req.GET['ccd']
    return HttpResponse('CCD ' + ccd)

def nil(req):
    pass

def brick_detail(req, brickname):
    #brickname = req.GET['brick']
    return HttpResponse('Brick ' + brickname)

def cat_decals(req, zoom, x, y, tag='decals'):
    import simplejson
    from desi.common import Decals
    from astrometry.util.fits import fits_table, merge_tables
    import numpy as np

    zoom = int(zoom)
    if zoom < 12:
        return HttpResponse(simplejson.dumps(dict(rd=[], zoom=zoom,
                                                  tilex=x, tiley=y)),
                            content_type='application/json')

    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)
    basedir = os.path.join(settings.WEB_DIR, 'data')
    cachefn = os.path.join(basedir, 'cats-cache', tag,
                           '%i/%i/%i.cat.json' % (zoom, x, y))
    if os.path.exists(cachefn):
        print 'Cached:', cachefn
        return send_file(cachefn, 'application/json',
                         modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'))

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
        # FIXME -- all False
        # print 'brick_primary', np.unique(T.brick_primary)
        # T.cut(T.brick_primary)
        ok,xx,yy = wcs.radec2pixelxy(T.ra, T.dec)
        #print 'xx,yy', xx.min(), xx.max(), yy.min(), yy.max()
        T.cut((xx > 0) * (yy > 0) * (xx < W) * (yy < H))
        cat.append(T)
    if len(cat) == 0:
        rd = []
    else:
        cat = merge_tables(cat)
        print 'All catalogs:'
        cat.about()
        rd = zip(cat.ra, cat.dec)

    json = simplejson.dumps(dict(rd=rd, zoom=zoom, tilex=x, tiley=y))
    dirnm = os.path.dirname(cachefn)
    if not os.path.exists(dirnm):
        try:
            os.makedirs(dirnm)
        except:
            pass

    f = open(cachefn, 'w')
    f.write(json)
    f.close()
    
    f = open(cachefn)
    return HttpResponse(f, content_type='application/json')
    
def map_coadd_bands(req, ver, zoom, x, y, bands, tag, imagedir,
                    imagetag='image2', rgbkwargs={}):
    from astrometry.util.resample import resample_with_wcs, OverlapError
    from astrometry.util.util import Tan
    from desi.common import Decals, get_rgb
    import numpy as np
    import pylab as plt
    import fitsio

    zoom = int(zoom)
    zoomscale = 2.**zoom
    x = int(x)
    y = int(y)
    if zoom < 0 or x < 0 or y < 0 or x >= zoomscale or y >= zoomscale:
        raise RuntimeError('Invalid zoom,x,y %i,%i,%i' % (zoom,x,y))
    ver = int(ver)

    if not ver in tileversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    basedir = os.path.join(settings.WEB_DIR, 'data')
    tilefn = os.path.join(basedir, 'tiles', tag,
                          '%i/%i/%i/%i.jpg' % (ver, zoom, x, y))
    if os.path.exists(tilefn):
        print 'Cached:', tilefn
        return send_file(tilefn, 'image/jpeg', expires=oneyear,
                         modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'))

    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)

    ok,r,d = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                               [1,H/2,H,H,H,H/2,1,1])
    # print 'RA,Dec corners', r,d
    # print 'RA range', r.min(), r.max()
    # print 'Dec range', d.min(), d.max()
    # print 'Zoom', zoom, 'pixel scale', wcs.pixel_scale()

    basepat = os.path.join(basedir, 'coadd', imagedir,
                           imagetag + '-%(brick)06i-%(band)s.fits')
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
                import traceback
                import sys
                traceback.print_exc(None, sys.stdout)
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
                import traceback
                import sys
                traceback.print_exc(None, sys.stdout)
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

    if not savecache:
        import tempfile
        f,tilefn = tempfile.mkstemp(suffix='.jpg')
        os.close(f)

    plt.imsave(tilefn, rgb)
    return send_file(tilefn, 'image/jpeg', unlink=(not savecache))


    
# def map_image(req, zoom, x, y):
#     from astrometry.blind.plotstuff import Plotstuff
# 
#     try:
#         wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
#     except RuntimeError as e:
#         return HttpResponse(e.strerror)
# 
#     plot = Plotstuff(size=(256,256), outformat='jpg')
#     plot.wcs = wcs
#     plot.color = 'gray'
# 
#     grid = 30
#     if zoom >= 2:
#         grid = 10
#     if zoom >= 4:
#         grid = 5
#     if zoom >= 6:
#         grid = 1
#     if zoom >= 8:
#         grid = 0.5
#     if zoom >= 10:
#         grid = 0.1
#     plot.plot_grid(grid*2, grid, ralabelstep=grid*2, declabelstep=grid)
# 
#     plot.color = 'white'
#     plot.apply_settings()
#     ok,r,d = wcs.pixelxy2radec(W/2+0.5, H/2+0.5)
#     plot.text_xy(W/2, H/2, 'zoom%i (%i,%i)' % (zoom,x,y))
#     plot.stroke()
#     plot.color = 'green'
#     plot.lw = 2.
#     plot.alpha = 0.3
#     plot.apply_settings()
#     M = 5
#     plot.polygon([(M,M),(W-M,M),(W-M,H-M),(M,H-M)])
#     plot.close_path()
#     plot.stroke()
#     
#     f,fn = tempfile.mkstemp()
#     os.close(f)
#     plot.write(fn)
#     return send_file(fn, 'image/jpeg', unlink=True)
