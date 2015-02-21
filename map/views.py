import os
from django.http import HttpResponse

# We add a version number to each layer, to allow long cache times
# for the tile JPEGs.  Increment this version to invalidate
# client-side caches.

tileversions = {
    'cosmos-grz': [1,],
    'decals': [1,],
    'decals-model': [1,],
    'decals-pr': [1,4],
    'decals-model-pr': [1,],
    'des-stripe82': [1,],
    'des-pr': [1,],
    'sfd': [1,],
    'decals-edr2': [1,],
    'decals-model-edr2': [1,],
    'decals-resid-edr2': [1,],
    }

catversions = {
    #'decals': [1,],
    #'decals-edr2': [1,],
    'decals': [2,],
    'decals-edr2': [2,],
    }

oneyear = (3600 * 24 * 365)

def ra2long(ra):
    lng = 180. - ra
    lng += 360 * (lng < 0.)
    lng -= 360 * (lng > 360.)
    return lng

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
            from django.http import HttpResponseNotModified
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
    # Nice spiral galaxy
    #ra, dec, zoom = 244.7, 7.4, 13
    # EDR2 region
    ra, dec, zoom = 243.7, 8.2, 13

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

    lat,lng = dec, ra2long(ra)

    url = req.build_absolute_uri('/') + '{id}/{ver}/{z}/{x}/{y}.jpg'
    caturl = '/{id}/{ver}/{z}/{x}/{y}.cat.json'

    # Deployment: http://{s}.DOMAIN/{id}/{ver}/{z}/{x}/{y}.jpg
    tileurl = url.replace('://', '://{s}.')

    # Testing:
    #tileurl = '/{id}/{ver}/{z}/{x}/{y}.jpg'

    bricksurl = '/bricks/?north={north}&east={east}&south={south}&west={west}'
    ccdsurl = '/ccds/?north={north}&east={east}&south={south}&west={west}'

    baseurl = req.path + '?layer=%s&' % layer

    from django.shortcuts import render

    return render(req, 'index.html',
                  dict(ra=ra, dec=dec, lat=lat, long=lng, zoom=zoom,
                       layer=layer, tileurl=tileurl,
                       baseurl=baseurl, caturl=caturl, bricksurl=bricksurl,
                       ccdsurl=ccdsurl,
                       showSources='sources' in req.GET,
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
            print 'Image source file', sourcefn, 'not found'
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

# "PR"
#rgbkwargs=dict(mnmx=(-0.3,100.), arcsinh=1.))

rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)

def map_cosmos_grz(req, ver, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz', 'cosmos-grz', 'cosmos',
                           rgbkwargs=rgbkwargs)

# def map_cosmos_urz(req, zoom, x, y):
#     return map_coadd_bands(req, zoom, x, y, 'urz', 'cosmos-urz', 'cosmos')

def map_decals(req, ver, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz', 'decals', 'decals')

def map_decals_model(req, ver, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz',
                           'decals-model', 'decals-model', imagetag='model')

def map_decals_pr(req, ver, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz', 'decals-pr', 'decals',
                           rgbkwargs=rgbkwargs)

def map_decals_model_pr(req, ver, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz',
                           'decals-model-pr', 'decals-model', imagetag='model',
                           rgbkwargs=rgbkwargs)

def map_decals_edr2(req, ver, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz', 'decals-edr2', 'decals-edr2',
                           imagetag='image',
                           rgbkwargs=rgbkwargs,
                           layout=2)

def map_decals_model_edr2(req, ver, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz',
                           'decals-model-edr2', 'decals-edr2',
                           imagetag='model',
                           rgbkwargs=rgbkwargs,
                           layout=2)

def map_decals_resid_edr2(req, ver, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz',
                           'decals-resid-edr2', 'decals-edr2',
                           imagetag='resid',
                           rgbkwargs=dict(mnmx=(-5,5)),
                           layout=2)

def map_des_stripe82(req, ver, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz', 'des-stripe82', 'des-stripe82')

def map_des_pr(req, ver, zoom, x, y):
    return map_coadd_bands(req, ver, zoom, x, y, 'grz', 'des-stripe82-pr', 'des-stripe82',
                           rgbkwargs=rgbkwargs)

sfd = None

def map_sfd(req, ver, zoom, x, y):
    global sfd
    
    zoom = int(zoom)
    zoomscale = 2.**zoom
    x = int(x)
    y = int(y)
    if zoom < 0 or x < 0 or y < 0 or x >= zoomscale or y >= zoomscale:
        raise RuntimeError('Invalid zoom,x,y %i,%i,%i' % (zoom,x,y))
    ver = int(ver)

    tag = 'sfd'

    if not ver in tileversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    from decals import settings

    basedir = os.path.join(settings.WEB_DIR, 'data')
    tilefn = os.path.join(basedir, 'tiles', tag,
                          '%i/%i/%i/%i.jpg' % (ver, zoom, x, y))
    if os.path.exists(tilefn):
        print 'Cached:', tilefn
        return send_file(tilefn, 'image/jpeg', expires=oneyear,
                         modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'))

    from desi.common import SFDMap
    import numpy as np
    
    if sfd is None:
        sfd = SFDMap(dustdir=settings.DUST_DIR)

    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)

    xx,yy = np.meshgrid(np.arange(wcs.get_width()), np.arange(wcs.get_height()))
    ok,rr,dd = wcs.pixelxy2radec(xx.ravel(), yy.ravel())
    ebv = sfd.ebv(rr, dd)
    ebv = ebv.reshape(xx.shape)
    #print 'EBV range:', ebv.min(), ebv.max()
    savecache = True

    try:
        os.makedirs(os.path.dirname(tilefn))
    except:
        pass

    if not savecache:
        import tempfile
        f,tilefn = tempfile.mkstemp(suffix='.jpg')
        os.close(f)

    import matplotlib
    matplotlib.use('Agg')
    import pylab as plt
    plt.imsave(tilefn, ebv, vmin=0., vmax=0.5, cmap='hot')

    return send_file(tilefn, 'image/jpeg', unlink=(not savecache))



decals = None
def _get_decals():
    global decals
    if decals is None:
        from desi.common import Decals
        decals = Decals()
    return decals

def brick_list(req):
    import simplejson

    north = float(req.GET['north'])
    south = float(req.GET['south'])
    east  = float(req.GET['east'])
    west  = float(req.GET['west'])
    #print 'N,S,E,W:', north, south, east, west

    if east < 0:
        east += 360.
        west += 360.

    D = _get_decals()
    B = D.get_bricks_readonly()
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
                           poly=[[b.dec1-mdec, ra2long(b.ra1-mra)],
                                 [b.dec2+mdec, ra2long(b.ra1-mra)],
                                 [b.dec2+mdec, ra2long(b.ra2+mra)],
                                 [b.dec1-mdec, ra2long(b.ra2+mra)],
                                 ]))

    return HttpResponse(simplejson.dumps(dict(bricks=bricks)),
                        content_type='application/json')

ccdtree = None
CCDs = None

def _ccds_touching_box(north, south, east, west, Nmax=None):
    from astrometry.libkd.spherematch import tree_build_radec, tree_search_radec
    from astrometry.util.starutil_numpy import degrees_between
    import numpy as np
    global ccdtree
    global CCDs
    if ccdtree is None:
        D = _get_decals()
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

    if Nmax is not None:
        # limit result size
        J = J[:Nmax]

    return CCDs[J]

def ccd_list(req):
    import simplejson
    from astrometry.util.util import Tan
    import numpy as np

    north = float(req.GET['north'])
    south = float(req.GET['south'])
    east  = float(req.GET['east'])
    west  = float(req.GET['west'])
    #print 'N,S,E,W:', north, south, east, west

    CCDS = _ccds_touching_box(north, south, east, west, Nmax=1000)

    ccds = []
    for c in CCDS:
        wcs = Tan(*[float(x) for x in [
            c.ra_bore, c.dec_bore, c.crpix1, c.crpix2, c.cd1_1, c.cd1_2,
            c.cd2_1, c.cd2_2, c.width, c.height]])
        x = np.array([1, 1, c.width, c.width])
        y = np.array([1, c.height, c.height, 1])
        r,d = wcs.pixelxy2radec(x, y)
        ccds.append(dict(name='%i-%s-%s' % (c.expnum, c.extname, c.filter),
                         poly=zip(d, ra2long(r))))

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

def cat_decals_edr2(req, ver, zoom, x, y, tag='decals-edr2'):
    return cat_decals(req, ver, zoom, x, y, tag=tag, layout=2)

def cat_decals(req, ver, zoom, x, y, tag='decals', layout=1):
    import simplejson

    zoom = int(zoom)
    if zoom < 12:
        return HttpResponse(simplejson.dumps(dict(rd=[], zoom=zoom,
                                                  tilex=x, tiley=y)),
                            content_type='application/json')

    from astrometry.util.fits import fits_table, merge_tables
    import numpy as np
    from decals import settings

    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)
    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    basedir = os.path.join(settings.WEB_DIR, 'data')
    cachefn = os.path.join(basedir, 'cats-cache', tag,
                           '%i/%i/%i/%i.cat.json' % (ver, zoom, x, y))
    if os.path.exists(cachefn):
        print 'Cached:', cachefn
        return send_file(cachefn, 'application/json',
                         modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'),
                         expires=oneyear)

    cat,hdr = _get_decals_cat(wcs, layout=layout, tag=tag)

    if cat is None:
        rd = []
        types = []
        fluxes = []
        bricknames = []
        objids = []
    else:
        #print 'All catalogs:'
        #cat.about()
        rd = zip(cat.ra, cat.dec)
        types = list(cat.get('type'))
        fluxes = [dict(g=float(g), r=float(r), z=float(z))
                  for g,r,z in zip(cat.decam_flux[:,1], cat.decam_flux[:,2],
                                   cat.decam_flux[:,4])]
        bricknames = list(cat.brickname)
        objids = list(cat.objid.astype(int))

    json = simplejson.dumps(dict(rd=rd, sourcetype=types, fluxes=fluxes,
                                 bricknames=bricknames, objids=objids,
                                 zoom=zoom, tilex=x, tiley=y))
    dirnm = os.path.dirname(cachefn)
    if not os.path.exists(dirnm):
        try:
            os.makedirs(dirnm)
        except:
            pass

    f = open(cachefn, 'w')
    f.write(json)
    f.close()
    return send_file(cachefn, 'application/json', expires=oneyear)

def _get_decals_cat(wcs, layout=1, tag='decals'):
    from decals import settings
    from astrometry.util.fits import fits_table, merge_tables

    basedir = os.path.join(settings.WEB_DIR, 'data')
    H,W = wcs.shape
    print 'WCS shape:', H,W
    X = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                            [1,H/2,H,H,H,H/2,1,1])
    r,d = X[-2:]
    if layout == 1:
        catpat = os.path.join(basedir, 'cats', tag,
                              'tractor-%(brick)06i.fits')
    elif layout == 2:
        catpat = os.path.join(basedir, 'cats', tag, '%(brickname).3s',
                              'tractor-%(brickname)s.fits')
    D = _get_decals()
    B = D.get_bricks_readonly()
    I = D.bricks_touching_radec_box(B, r.min(), r.max(), d.min(), d.max())

    cat = []
    hdr = None
    for brickid,brickname in zip(B.brickid[I], B.brickname[I]):
        fnargs = dict(brick=brickid, brickname=brickname)
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
        print 'kept', len(T), 'from', catfn
        cat.append(T)
        if hdr is None:
            hdr = T.get_header()
    if len(cat) == 0:
        cat = None
    else:
        cat = merge_tables(cat)

    return cat,hdr
    
def map_coadd_bands(req, ver, zoom, x, y, bands, tag, imagedir,
                    imagetag='image2', rgbkwargs={},
                    layout=1):
    from decals import settings

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

    from astrometry.util.resample import resample_with_wcs, OverlapError
    from astrometry.util.util import Tan
    from desi.common import get_rgb
    import numpy as np
    import fitsio

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

    if layout == 1:
        basepat = os.path.join(basedir, 'coadd', imagedir,
                               imagetag + '-%(brick)06i-%(band)s.fits')
    elif layout == 2:
        basepat = os.path.join(basedir, 'coadd', imagedir, '%(brickname).3s',
                               '%(brickname)s',
                               'decals-%(brickname)s-' + imagetag + '-%(band)s.fits')
        
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
        
    D = _get_decals()
    B = D.get_bricks_readonly()
    I = D.bricks_touching_radec_box(B, r.min(), r.max(), d.min(), d.max())
    #print len(I), 'bricks touching:', B.brickid[I]
    rimgs = []

    # If any problems are encountered during tile rendering, don't save
    # the results... at least it'll get fixed upon reload.
    savecache = True

    for band in bands:
        rimg = np.zeros((H,W), np.float32)
        rn   = np.zeros((H,W), np.uint8)
        for brickid,brickname in zip(B.brickid[I], B.brickname[I]):
            fnargs = dict(band=band, brick=brickid, brickname=brickname)

            if imagetag == 'resid':
                basefn = basepat % fnargs

                if scalepat is None:
                    imscalepat = None
                    modscalepat = None
                else:
                    imscalepat = scalepat.replace('resid', 'image')
                    modscalepat = scalepat.replace('resid', 'model')
                imbasefn = basefn.replace('resid', 'image')
                imfn = get_scaled(imscalepat, fnargs, scaled, imbasefn)
                print 'imfn', imfn
                modbasefn = basefn.replace('resid', 'model')
                modfn = get_scaled(modscalepat, fnargs, scaled, modbasefn)
                print 'modfn', modfn
                fn = imfn

            else:
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
                del f

                if imagetag == 'resid':
                    f = fitsio.FITS(modfn)[0]
                    mod = f[slc]
                    del f
                    img = img - mod
                
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

    import matplotlib
    matplotlib.use('Agg')
    import pylab as plt
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


def cutouts(req):
    from astrometry.util.util import Tan
    import numpy as np

    ra = float(req.GET['ra'])
    dec = float(req.GET['dec'])

    # half-size in DECam pixels
    size = 50
    W,H = size*2, size*2
    
    pixscale = 0.262 / 3600.
    wcs = Tan(*[float(x) for x in [
        ra, dec, size+0.5, size+0.5, -pixscale, 0., 0., pixscale, W, H]])

    nil,north = wcs.pixelxy2radec(size+0.5, H)
    nil,south = wcs.pixelxy2radec(size+0.5, 1)
    west,nil  = wcs.pixelxy2radec(1, size+0.5)
    east,nil  = wcs.pixelxy2radec(W, size+0.5)
    
    CCDs = _ccds_touching_box(north, south, east, west)

    print len(CCDs), 'CCDs'

    CCDs = CCDs[np.lexsort((CCDs.extname, CCDs.expnum, CCDs.filter))]

    ccds = []
    #for c in CCDs:
    for i in range(len(CCDs)):
        c = CCDs[i]

        try:
            from desi.common import DecamImage
            c.cpimage = _get_image_filename(c)
            dim = DecamImage(c)
            wcs = dim.read_wcs()
        except:
            import traceback
            traceback.print_exc()
            
            wcs = Tan(*[float(x) for x in [
                c.ra_bore, c.dec_bore, c.crpix1, c.crpix2, c.cd1_1, c.cd1_2,
                c.cd2_1, c.cd2_2, c.width, c.height]])
        ok,x,y = wcs.radec2pixelxy(ra, dec)
        x = int(np.round(x-1))
        y = int(np.round(y-1))
        if x < -size or x >= c.width+size or y < -size or y >= c.height+size:
            continue

        #print 'CCD', c
        c = dict([(k,c.get(k)) for k in c.columns()])
        #print 'CCD', c
        ccds.append((c, x, y))

    #print 'CCDS:', ccds

    from django.shortcuts import render

    return render(req, 'cutouts.html',
                  dict(ra=ra, dec=dec,
                       ccds=ccds,
                       ))

def cat_plot(req):
    import matplotlib
    matplotlib.use('Agg')
    import pylab as plt
    import numpy as np
    from astrometry.util.util import Tan
    from desi.common import get_sdss_sources
    from decals import settings

    ra = float(req.GET['ra'])
    dec = float(req.GET['dec'])

    # half-size in DECam pixels
    size = 50
    W,H = size*2, size*2
    
    pixscale = 0.262 / 3600.
    wcs = Tan(*[float(x) for x in [
        ra, dec, size+0.5, size+0.5, -pixscale, 0., 0., pixscale, W, H]])

    M = 10
    margwcs = wcs.get_subimage(-M, -M, W+2*M, H+2*M)
    cat,hdr = _get_decals_cat(margwcs, layout=2, tag='decals-edr2')

    # FIXME
    nil,sdss = get_sdss_sources('r', margwcs,
                                photoobjdir=os.path.join(settings.WEB_DIR, 'data',
                                                         'sdss'),
                                local=False)

    import tempfile
    f,tempfn = tempfile.mkstemp(suffix='.png')
    os.close(f)

    plt.figure(figsize=(2,2))
    #plt.subplots_adjust(left=0.1, bottom=0.1, top=0.99, right=0.99)
    plt.subplots_adjust(left=0.01, bottom=0.01, top=0.99, right=0.99)
    plt.clf()
    ok,x,y = wcs.radec2pixelxy(cat.ra, cat.dec)
    # matching the plot colors in index.html
    cc = dict(S=(0x9a, 0xfe, 0x2e),
              D=(0xff, 0, 0),
              E=(0x58, 0xac, 0xfa),
              C=(0xda, 0x81, 0xf5))
    plt.scatter(x, y, s=50, c=[[float(x)/255. for x in cc[t]] for t in cat.type])

    ok,x,y = wcs.radec2pixelxy(sdss.ra, sdss.dec)
    plt.scatter(x, y, s=30, marker='x', c='k')

    plt.axis([0, W, 0, H])
    plt.xticks([]); plt.yticks([])
    plt.savefig(tempfn)

    return send_file(tempfn, 'image/png', unlink=True,
                     expires=0)


def _get_ccd(expnum, extname):
    import numpy as np
    # Not ideal... look up local CP image name from expnum.
    global CCDs
    if CCDs is None:
        D = _get_decals()
        CCDs = D.get_ccds()
    expnum = int(expnum, 10)
    extname = str(extname)
    I = np.flatnonzero((CCDs.expnum == expnum) * (CCDs.extname == extname))
    assert(len(I) == 1)
    ccd = CCDs[I[0]]
    return ccd

def _get_image_filename(ccd):
    from decals import settings
    basedir = os.path.join(settings.WEB_DIR, 'data')
    fn = ccd.cpimage
    # drop 'decals/' off the front...
    fn = fn.replace('decals/','')
    fn = os.path.join(basedir, fn)
    return fn

def _get_image_slice(fn, hdu, x, y, size=50):
    import fitsio
    img = fitsio.FITS(fn)[hdu]
    H,W = img.get_info()['dims']
    if x < size:
        xstart = size - x
    else:
        xstart = 0
    if y < size:
        ystart = size - y
    else:
        ystart = 0
    slc = slice(max(y-size, 0), min(y+size, H)), slice(max(x-size, 0), min(x+size, W))
    img = img[slc]
    return img,slc,xstart,ystart


def ccd_cutout(req, expnum=None, extname=None):
    return _cutout(req, expnum, extname, image=True)

#     import matplotlib
#     matplotlib.use('Agg')
#     import pylab as plt
# 
#     import numpy as np
#     
#     x = int(req.GET['x'], 10)
#     y = int(req.GET['y'], 10)
#     #print 'CCD cutout:', expnum, extname, x, y
# 
#     ccd = _get_ccd(expnum, extname)
#     #print 'CCD:', ccd
#     #print 'cpname:', ccd.cpimage
# 
#     fn = _get_image_filename(ccd)
#     if not os.path.exists(fn):
#         #print 'NO IMAGE:', fn
#         print 'rsync -Rrv carver:tractor/decals/images/./' + fn.replace('/home/dstn/decals-web/data/images/', '') + ' data/images'
#         return HttpResponse('no such image: ' + fn)
# 
#     import fitsio
# 
#     # half-size in DECam pixels -- must match cutouts():size
#     size = 50
# 
#     img,slc,xstart,ystart = _get_image_slice(fn, ccd.cpimage_hdu, x, y, size=size)
# 
#     mn,mx = [np.percentile(img, p) for p in [25,99]]
# 
#     ih,iw = img.shape
#     padimg = np.zeros((2*size,2*size), img.dtype) + (mn+mx)/2.
#     padimg[ystart:ystart+ih, xstart:xstart+iw] = img
#     img = padimg
# 
#     import tempfile
#     f,tilefn = tempfile.mkstemp(suffix='.jpg')
#     os.close(f)
# 
#     plt.imsave(tilefn, np.clip((img - mn) / (mx - mn), 0., 1.), cmap='gray')
#         
#     return send_file(tilefn, 'image/jpeg', unlink=True)

def model_cutout(req, expnum=None, extname=None):
    return _cutout(req, expnum, extname, model=True)

def resid_cutout(req, expnum=None, extname=None):
    return _cutout(req, expnum, extname, resid=True)

def _cutout(req, expnum, extname, model=False, image=False, resid=False):
    import matplotlib
    matplotlib.use('Agg')
    import pylab as plt
    import numpy as np

    x = int(req.GET['x'], 10)
    y = int(req.GET['y'], 10)

    ccd = _get_ccd(expnum, extname)
    
    fn = _get_image_filename(ccd)
    if not os.path.exists(fn):
        #print 'NO IMAGE:', fn
        print 'rsync -Rrv carver:tractor/decals/images/./' + fn.replace('/home/dstn/decals-web/data/images/', '') + ' data/images'
        return HttpResponse('no such image: ' + fn)

    wfn = fn.replace('ooi', 'oow')
    if not os.path.exists(wfn):
        cmd = 'rsync -Rrv carver:tractor/decals/images/./' + wfn.replace('/home/dstn/decals-web/data/images/', '') + ' data/images'
        print '\n' + cmd + '\n'
        os.system(cmd)
        if not os.path.exists(wfn):
            return HttpResponse('no such image: ' + wfn)

    # half-size in DECam pixels -- must match cutouts():size
    size = 50
    img,slc,xstart,ystart = _get_image_slice(fn, ccd.cpimage_hdu, x, y, size=size)

    from desi.common import DecamImage
    from desi.desi_common import read_fits_catalog
    from tractor import Tractor

    ccd.cpimage = fn
    im = DecamImage(ccd)
    D = _get_decals()
    tim = im.get_tractor_image(decals, slc=slc)
                               #nanomaggies=False, subsky=False)
    # nanomaggies
    #mn,mx = -0.1, 0.25
    #mn,mx = -3, 10
    #rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)
    mn,mx = -1, 100
    arcsinh = 1.

    scales = dict(g = (2, 0.0066),
                  r = (1, 0.01),
                  z = (0, 0.025),
                  )
    nil,scale = scales[ccd.filter]
    
    if image:
        img = tim.getImage()
        
    if model or resid:
        # UGH, this is just nasty.
        from tractor.psfex import CachingPsfEx
        tim.psfex.radius = 20
        tim.psfex.fitSavedData(*tim.psfex.splinedata)
        tim.psf = CachingPsfEx.fromPsfEx(tim.psfex)

        M = 10
        margwcs = tim.subwcs.get_subimage(-M, -M, int(tim.subwcs.get_width())+2*M, int(tim.subwcs.get_height())+2*M)
        cat,hdr = _get_decals_cat(margwcs, layout=2, tag='decals-edr2')
        # print len(cat), 'catalog objects'
        if cat is None:
            tcat = []
        else:
            tcat = read_fits_catalog(cat, hdr=hdr)
        # print len(tcat), 'Tractor sources'

        tr = Tractor([tim], tcat)
        if model:
            img = tr.getModelImage(0)
            #mn,mx = [np.percentile(img, p) for p in [25,99]]
        else:
            img = tr.getChiImage(0)
            mn,mx = -5, 5
            arcsinh = None
            scale = 1.

    img = img / scale

    if arcsinh is not None:
        def nlmap(x):
            return np.arcsinh(x * arcsinh) / np.sqrt(arcsinh)
        img = nlmap(img)
        mn = nlmap(mn)
        mx = nlmap(mx)

    ih,iw = img.shape
    padimg = np.zeros((2*size,2*size), img.dtype) + 0.5
    padimg[ystart:ystart+ih, xstart:xstart+iw] = (img - mn) / (mx - mn)
    img = padimg

    import tempfile
    f,tilefn = tempfile.mkstemp(suffix='.jpg')
    os.close(f)

    # the chips are turned sideways :)

    plt.imsave(tilefn, np.rot90(np.clip(img, 0., 1.), k=3), cmap='gray')
        
    return send_file(tilefn, 'image/jpeg', unlink=True,
                     expires=0)


