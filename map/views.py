import os
from django.http import HttpResponse, StreamingHttpResponse

from decals import settings

import matplotlib
matplotlib.use('Agg')

# We add a version number to each layer, to allow long cache times
# for the tile JPEGs.  Increment this version to invalidate
# client-side caches.

tileversions = {
    'sfd': [1,],
    'decals-dr1j-edr': [1],
    'decals-model-dr1j-edr': [1],
    'decals-resid-dr1j-edr': [1],

    'decals-dr1j': [1],
    'decals-model-dr1j': [1],
    'decals-resid-dr1j': [1],

    'unwise-w1w2': [1],
    'unwise-w3w4': [1],
    'unwise-w1234': [1],
    }

catversions = {
    'decals-dr1j': [1,],
    }

oneyear = (3600 * 24 * 365)

class MercWCSWrapper(object):
    def __init__(self, wcs, wrap):
        self.wcs = wcs
        self.wrap = float(wrap)
    def radec2pixelxy(self, ra, dec):
        #print 'radec2pixelxy:', ra, dec
        X = self.wcs.radec2pixelxy(ra, dec)
        #print '->', X
        (ok,x,y) = X
        x += (x < -self.wrap/2) * self.wrap
        x -= (x >  self.wrap/2) * self.wrap
        # if abs(x + self.wrap) < abs(x):
        #     print ' wrap up ->', ok, x+self.wrap, y
        #     return ok, x + self.wrap, y
        # if abs(x - self.wrap) < abs(x):
        #     print ' wrap down ->', ok, x-self.wrap, y
        #     return ok, x - self.wrap, y
        return (ok,x,y)

    # def pixelxy2radec(self, x, y):
    #     print 'pixelxy2radec', x, y
    #     X = self.wcs.pixelxy2radec(x, y)
    #     print '->', X
    #     return X

    def __getattr__(self, name):
        #if name in ['imagew', 'imageh', 'pixelxy2radec', 'get_center', 'pixel_scale',
        #            ]:
        return getattr(self.wcs, name)
        #raise RuntimeError('no such attr: %s' % name)
    def __setattr__(self, name, val):
        #if name in ['imagew', 'imageh']:
        #    return setattr(self.wcs, name, val)
        if name in ['wcs', 'wrap']:
            self.__dict__[name] = val
            return
        return setattr(self.wcs, name, val)
        #raise RuntimeError('no such attr in setattr: %s' % name)



def trymakedirs(fn):
    dirnm = os.path.dirname(fn)
    if not os.path.exists(dirnm):
        try:
            os.makedirs(dirnm)
        except:
            pass


def _read_tan_wcs(sourcefn, ext, hdr=None, W=None, H=None):
    from astrometry.util.util import Tan
    wcs = None
    if not sourcefn.endswith('.gz'):
        try:
            wcs = Tan(sourcefn, ext)
        except:
            pass
    if wcs is None:
        import fitsio
        # maybe gzipped; try fitsio header.
        if hdr is None:
            hdr = fitsio.read_header(sourcefn, ext)
        if W is None or H is None:
            F = fitsio.FITS(sourcefn)
            info = F[ext].get_info()
            H,W = info['dims']
        wcs = Tan(*[float(x) for x in [
                    hdr['CRVAL1'], hdr['CRVAL2'], hdr['CRPIX1'], hdr['CRPIX2'],
                    hdr['CD1_1'], hdr['CD1_2'], hdr['CD2_1'], hdr['CD2_2'],
                    W, H]])
    return wcs

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

    res = StreamingHttpResponse(f, content_type=content_type)
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
    layer = req.GET.get('layer', 'decals-dr1j-edr')
    # Nice spiral galaxy
    #ra, dec, zoom = 244.7, 7.4, 13
    # EDR2 region
    ra, dec, zoom = 243.7, 8.2, 13
    # Top of DR1
    #ra,dec,zoom = 113.49, 29.86, 13

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

    url = req.build_absolute_uri(settings.ROOT_URL) + '/{id}/{ver}/{z}/{x}/{y}.jpg'
    #caturl = settings.ROOT_URL + '/{id}/{ver}/{z}/{x}/{y}.cat.json'
    caturl = settings.CAT_URL

    tileurl = settings.TILE_URL

    # Deployment: http://{s}.DOMAIN/{id}/{ver}/{z}/{x}/{y}.jpg
    #tileurl = url.replace('www.legacysurvey', 'legacysurvey').replace('://', '://{s}.')
    #tileurl = 'http://{s}.legacysurvey.org/viewer/

    # Testing:
    #tileurl = settings.ROOT_URL + '/{id}/{ver}/{z}/{x}/{y}.jpg'

    #subdomains = "['a','b','c','d'];"

    # test.
    subdomains = settings.SUBDOMAINS
    # convert to javascript
    subdomains = '[' + ','.join(["'%s'" % s for s in subdomains]) + '];'

    static_tile_url = settings.STATIC_TILE_URL

    bricksurl = settings.ROOT_URL + '/bricks/?north={north}&east={east}&south={south}&west={west}'
    ccdsurl = settings.ROOT_URL + '/ccds/?north={north}&east={east}&south={south}&west={west}'

    # HACK
    # tileurl = 'http://broiler.cosmo.fas.nyu.edu:8896/{id}/{ver}/{z}/{x}/{y}.jpg'
    # caturl = 'http://broiler.cosmo.fas.nyu.edu:8896/{id}/{ver}/{z}/{x}/{y}.cat.json'
    #bricksurl = 'http://broiler.cosmo.fas.nyu.edu:8896/bricks/?north={north}&east={east}&south={south}&west={west}'
    #ccdsurl = 'http://broiler.cosmo.fas.nyu.edu:8896/ccds/?north={north}&east={east}&south={south}&west={west}'

    baseurl = req.path + '?layer=%s&' % layer

    from django.shortcuts import render

    return render(req, 'index.html',
                  dict(ra=ra, dec=dec, lat=lat, long=lng, zoom=zoom,
                       layer=layer, tileurl=tileurl,
                       baseurl=baseurl, caturl=caturl, bricksurl=bricksurl,
                       ccdsurl=ccdsurl,
                       static_tile_url=static_tile_url,
                       subdomains=subdomains,
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

    wcs = MercWCSWrapper(wcs, 2**zoom * W)

    return wcs, W, H, zoomscale, zoom,x,y

def get_scaled(scalepat, scalekwargs, scale, basefn):
    from scipy.ndimage.filters import gaussian_filter
    import fitsio
    from astrometry.util.util import Tan
    import tempfile

    if scale <= 0:
        return basefn
    fn = scalepat % dict(scale=scale, **scalekwargs)
    if not os.path.exists(fn):

        # print 'Does not exist:', fn
        sourcefn = get_scaled(scalepat, scalekwargs, scale-1, basefn)
        # print 'Source:', sourcefn
        if sourcefn is None or not os.path.exists(sourcefn):
            # print 'Image source file', sourcefn, 'not found'
            return None
        try:
            I,hdr = fitsio.read(sourcefn, header=True)
        except:
            print 'Failed to read:', sourcefn
            return None
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
        wcs = _read_tan_wcs(sourcefn, 0, hdr=hdr, W=W, H=H)
        # include the even size clip; this may be a no-op
        H,W = im.shape
        wcs = wcs.get_subimage(0, 0, W, H)
        subwcs = wcs.scale(0.5)
        hdr = fitsio.FITSHDR()
        subwcs.add_to_header(hdr)
        trymakedirs(fn)
        dirnm = os.path.dirname(fn)
        f,tmpfn = tempfile.mkstemp(suffix='.fits.tmp', dir=dirnm)
        os.close(f)
        # To avoid overwriting the (empty) temp file (and fitsio
        # printing "Removing existing file")
        os.unlink(tmpfn)
        fitsio.write(tmpfn, I2, header=hdr, clobber=True)
        os.rename(tmpfn, fn)
        print 'Wrote', fn
    return fn

# "PR"
#rgbkwargs=dict(mnmx=(-0.3,100.), arcsinh=1.))

rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)

B_dr1j_edr = None

def map_decals_dr1j_edr(req, ver, zoom, x, y, savecache=False,
                    model=False, resid=False,
                    **kwargs):
    global B_dr1j_edr
    if B_dr1j_edr is None:
        from decals import settings
        from astrometry.util.fits import fits_table
        B_dr1j_edr = fits_table(os.path.join(settings.WEB_DIR, 'decals-bricks-in-edr.fits'))
        #B_dr1j_edr.cut(B_dr1d.exists)

    imagetag = 'image'
    tag = 'decals-dr1j-edr'
    imagedir = 'decals-dr1j'
    if model:
        imagetag = 'model'
        tag = 'decals-model-dr1j-edr'
        imagedir = 'decals-dr1j-model'
        scaledir = 'decals-dr1j'
        kwargs.update(model_gz=False, scaledir=scaledir)
    if resid:
        imagetag = 'resid'
        kwargs.update(modeldir = 'decals-dr1j-model')
        tag = 'decals-resid-dr1j-edr'

    return map_coadd_bands(req, ver, zoom, x, y, 'grz', tag, imagedir,
                           imagetag=imagetag,
                           rgbkwargs=rgbkwargs,
                           bricks=B_dr1j_edr,
                           savecache=savecache, **kwargs)

def map_decals_model_dr1j_edr(*args, **kwargs):
    return map_decals_dr1j_edr(*args, model=True, model_gz=False, **kwargs)

def map_decals_resid_dr1j_edr(*args, **kwargs):
    return map_decals_dr1j_edr(*args, resid=True, model_gz=False, **kwargs)


B_dr1j = None

def map_decals_dr1j(req, ver, zoom, x, y, savecache=False,
                    model=False, resid=False,
                    **kwargs):
    global B_dr1j
    if B_dr1j is None:
        from decals import settings
        from astrometry.util.fits import fits_table
        import numpy as np

        B_dr1j = fits_table(os.path.join(settings.WEB_DIR, 'decals-dr1',
                                         'decals-bricks-exist.fits'))
        B_dr1j.cut(reduce(np.logical_or, [B_dr1j.has_image_g,
                                          B_dr1j.has_image_r,
                                          B_dr1j.has_image_z]))
        B_dr1j.has_g = B_dr1j.has_image_g
        B_dr1j.has_r = B_dr1j.has_image_r
        B_dr1j.has_z = B_dr1j.has_image_z
        print len(B_dr1j), 'bricks with images'

    imagetag = 'image'
    tag = 'decals-dr1j'
    imagedir = 'decals-dr1j'
    if model:
        imagetag = 'model'
        tag = 'decals-model-dr1j'
        imagedir = 'decals-dr1j-model'
        scaledir = 'decals-dr1j'
        kwargs.update(model_gz=False, scaledir=scaledir)
    if resid:
        imagetag = 'resid'
        kwargs.update(modeldir = 'decals-dr1j-model')
        tag = 'decals-resid-dr1j'

    return map_coadd_bands(req, ver, zoom, x, y, 'grz', tag, imagedir,
                           imagetag=imagetag,
                           rgbkwargs=rgbkwargs,
                           bricks=B_dr1j,
                           savecache=savecache, **kwargs)

def map_decals_model_dr1j(*args, **kwargs):
    return map_decals_dr1j(*args, model=True, model_gz=False, **kwargs)

def map_decals_resid_dr1j(*args, **kwargs):
    return map_decals_dr1j(*args, resid=True, model_gz=False, **kwargs)


def _unwise_to_rgb(imgs, bands=[1,2], S=None, Q=None):
    import numpy as np
    img = imgs[0]
    H,W = img.shape


    if S is not None or Q is not None:
        # 
        if S is None:
            S = [1000.]*len(imgs)
        if Q is None:
            Q = 25.
        alpha = 1.5

        if len(imgs) == 2:
            w1,w2 = imgs
            S1,S2 = S
            b = w1 / S1
            r = w2 / S2
            g = (r + b) / 2.
        elif len(imgs) == 4:
            w1,w2,w3,w4 = imgs
            S1,S2,S3,S4 = S
            w1 /= S1
            w2 /= S2
            w3 /= S3
            w4 /= S4
            b = w1
            g = 0.8 * w2 + 0.2 * w3
            r = 0.4 * w2 + 0.8 * w3 + w4

        m = -2e-2
    
        r = np.maximum(0, r - m)
        g = np.maximum(0, g - m)
        b = np.maximum(0, b - m)
        I = (r+g+b)/3.
        fI = np.arcsinh(alpha * Q * I) / np.sqrt(Q)
        I += (I == 0.) * 1e-6
        R = fI * r / I
        G = fI * g / I
        B = fI * b / I
        RGB = (np.clip(np.dstack([R,G,B]), 0., 1.) * 255.).astype(np.uint8)
        return RGB

    ## FIXME
    w1,w2 = imgs
    
    rgb = np.zeros((H, W, 3), np.uint8)

    scale1 = 50.
    scale2 = 50.

    mn,mx = -1.,100.
    arcsinh = 1.
    #mn,mx = -3.,30.
    #arcsinh = None

    img1 = w1 / scale1
    img2 = w2 / scale2

    if arcsinh is not None:
        def nlmap(x):
            return np.arcsinh(x * arcsinh) / np.sqrt(arcsinh)
        #img1 = nlmap(img1)
        #img2 = nlmap(img2)
        mean = (img1 + img2) / 2.
        I = nlmap(mean)
        img1 = img1 / mean * I
        img2 = img2 / mean * I
        mn = nlmap(mn)
        mx = nlmap(mx)
    img1 = (img1 - mn) / (mx - mn)
    img2 = (img2 - mn) / (mx - mn)

    rgb[:,:,2] = (np.clip(img1, 0., 1.) * 255).astype(np.uint8)
    rgb[:,:,0] = (np.clip(img2, 0., 1.) * 255).astype(np.uint8)
    rgb[:,:,1] = rgb[:,:,0]/2 + rgb[:,:,2]/2

    return rgb

UNW = None
UNW_tree = None

def map_unwise_w1w2(*args, **kwargs):
    return map_unwise(*args, **kwargs)

def map_unwise_w3w4(*args, **kwargs):
    kwargs.update(S=[1e5, 1e6])
    return map_unwise(*args, bands=[3,4], tag='unwise-w3w4', **kwargs)

def map_unwise_w1234(*args, **kwargs):
    kwargs.update(S=[3e3, 3e3, 3e5, 1e6])
    return map_unwise(*args, bands=[1,2,3,4], tag='unwise-w1234', **kwargs)

def map_unwise(req, ver, zoom, x, y, savecache = False, ignoreCached=False,
               get_images=False,
               bands=[1,2], tag='unwise-w1w2', **kwargs):
    global UNW
    global UNW_tree

    zoom = int(zoom)
    zoomscale = 2.**zoom
    x = int(x)
    y = int(y)
    if zoom < 0 or x < 0 or y < 0 or x >= zoomscale or y >= zoomscale:
        raise RuntimeError('Invalid zoom,x,y %i,%i,%i' % (zoom,x,y))
    ver = int(ver)

    if not ver in tileversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    from decals import settings

    basedir = settings.DATA_DIR
    tilefn = os.path.join(basedir, 'tiles', tag,
                          '%i/%i/%i/%i.jpg' % (ver, zoom, x, y))
    if os.path.exists(tilefn) and not ignoreCached:
        return send_file(tilefn, 'image/jpeg', expires=oneyear,
                         modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'))

    if not savecache:
        import tempfile
        f,tilefn = tempfile.mkstemp(suffix='.jpg')
        os.close(f)

    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)

    from astrometry.util.fits import fits_table
    import numpy as np
    from astrometry.libkd.spherematch import tree_build_radec, tree_search_radec
    from astrometry.util.starutil_numpy import degrees_between, arcsec_between
    from astrometry.util.resample import resample_with_wcs, OverlapError
    from astrometry.util.util import Tan
    import fitsio

    if UNW is None:
        UNW = fits_table(os.path.join(settings.UNWISE_DIR, 'allsky-atlas.fits'))
        UNW_tree = tree_build_radec(UNW.ra, UNW.dec)

    # unWISE tile size
    radius = 1.01 * np.sqrt(2.)/2. * 2.75 * 2048 / 3600.

    # leaflet tile size
    ok,ra,dec = wcs.pixelxy2radec(W/2., H/2.)
    ok,r0,d0 = wcs.pixelxy2radec(1, 1)
    ok,r1,d1 = wcs.pixelxy2radec(W, H)
    radius = radius + max(degrees_between(ra,dec, r0,d0), degrees_between(ra,dec, r1,d1))

    J = tree_search_radec(UNW_tree, ra, dec, radius)
    #print len(J), 'unWISE tiles nearby'
    
    ww = [1, W*0.25, W*0.5, W*0.75, W]
    hh = [1, H*0.25, H*0.5, H*0.75, H]

    ok,r,d = wcs.pixelxy2radec(
        [1]*len(hh) + ww          + [W]*len(hh) +        list(reversed(ww)),
        hh          + [1]*len(ww) + list(reversed(hh)) + [H]*len(ww))
    scaled = 0
    scalepat = None
    scaledir = 'unwise'

    if zoom < 11:
        # Get *actual* pixel scales at the top & bottom
        ok,r1,d1 = wcs.pixelxy2radec(W/2., H)
        ok,r2,d2 = wcs.pixelxy2radec(W/2., H-1.)
        ok,r3,d3 = wcs.pixelxy2radec(W/2., 1.)
        ok,r4,d4 = wcs.pixelxy2radec(W/2., 2.)
        # Take the min = most zoomed-in
        scale = min(arcsec_between(r1,d1, r2,d2), arcsec_between(r3,d3, r4,d4))
        
        native_scale = 2.75
        scaled = int(np.floor(np.log2(scale / native_scale)))
        print 'Zoom:', zoom, 'x,y', x,y, 'Tile pixel scale:', scale, 'Scale step:', scaled
        scaled = np.clip(scaled, 1, 7)
        dirnm = os.path.join(basedir, 'scaled', scaledir)
        scalepat = os.path.join(dirnm, '%(scale)i%(band)s', '%(tilename).3s', 'unwise-%(tilename)s-%(band)s.fits')

    basepat = os.path.join(settings.UNWISE_DIR, '%(tilename).3s', '%(tilename)s', 'unwise-%(tilename)s-%(band)s-img-u.fits')

    rimgs = [np.zeros((H,W), np.float32) for band in bands]
    rn    = np.zeros((H,W), np.uint8)

    for j in J:
        tile = UNW.coadd_id[j]

        fns = []
        for band in bands:
            bandname = 'w%i' % band
            fnargs = dict(band=bandname, tilename=tile)
            basefn = basepat % fnargs
            fn = get_scaled(scalepat, fnargs, scaled, basefn)
            fns.append(fn)

        bwcs = Tan(fns[0], 0)
        ok,xx,yy = bwcs.radec2pixelxy(r, d)
        if not np.all(ok):
            print 'Skipping tile', tile
            continue
        assert(np.all(ok))
        xx = xx.astype(np.int)
        yy = yy.astype(np.int)
        imW,imH = int(bwcs.get_width()), int(bwcs.get_height())
        # Margin
        M = 20
        xlo = np.clip(xx.min() - M, 0, imW)
        xhi = np.clip(xx.max() + M, 0, imW)
        ylo = np.clip(yy.min() - M, 0, imH)
        yhi = np.clip(yy.max() + M, 0, imH)
        if xlo >= xhi or ylo >= yhi:
            continue
        subwcs = bwcs.get_subimage(xlo, ylo, xhi-xlo, yhi-ylo)
        slc = slice(ylo,yhi), slice(xlo,xhi)

        try:
            Yo,Xo,Yi,Xi,nil = resample_with_wcs(wcs, subwcs, [], 3)
        except OverlapError:
            # print 'Resampling exception'
            # import traceback
            # print traceback.print_exc()
            continue

        for fn, rimg in zip(fns, rimgs):
            f = fitsio.FITS(fn)[0]
            img = f[slc]
            rimg[Yo,Xo] += img[Yi,Xi]
            del img, f
        rn  [Yo,Xo] += 1

    for rimg in rimgs:
        rimg /= np.maximum(rn, 1)
    del rn

    if get_images:
        return rimgs

    rgb = _unwise_to_rgb(rimgs, **kwargs)

    import pylab as plt

    trymakedirs(tilefn)

    # no jpeg output support in matplotlib in some installations...
    if True:
        import tempfile
        f,tempfn = tempfile.mkstemp(suffix='.png')
        os.close(f)
        plt.imsave(tempfn, rgb)
        print 'Wrote to temp file', tempfn
        cmd = 'pngtopnm %s | pnmtojpeg -quality 90 > %s' % (tempfn, tilefn)
        print cmd
        os.system(cmd)
        os.unlink(tempfn)
        print 'Wrote', tilefn

    return send_file(tilefn, 'image/jpeg', unlink=(not savecache))


sfd = None

def map_sfd(req, ver, zoom, x, y, savecache = False):
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

    basedir = settings.DATA_DIR
    tilefn = os.path.join(basedir, 'tiles', tag,
                          '%i/%i/%i/%i.jpg' % (ver, zoom, x, y))

    if os.path.exists(tilefn):
        # print 'Cached:', tilefn
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

    trymakedirs(tilefn)

    if not savecache:
        import tempfile
        #f,tilefn = tempfile.mkstemp(suffix='.jpg')
        f,tilefn = tempfile.mkstemp(suffix='.png')
        os.close(f)

    import pylab as plt
    #plt.imsave(tilefn, ebv, vmin=0., vmax=0.5, cmap='hot', edgecolor='none', facecolor='none')
    #plt.imsave(tilefn, ebv, vmin=0., vmax=0.5, cmap='hot')
    #print 'Wrote',tilefn

    # no jpeg output support in matplotlib in some installations...
    if True:
        import tempfile
        f,tempfn = tempfile.mkstemp(suffix='.png')
        os.close(f)

        plt.imsave(tempfn, ebv, vmin=0., vmax=0.5, cmap='hot')

        cmd = 'pngtopnm %s | pnmtojpeg -quality 90 > %s' % (tempfn, tilefn)
        os.system(cmd)
        os.unlink(tempfn)
        print 'Wrote', tilefn

    return send_file(tilefn, 'image/jpeg', unlink=(not savecache))
    #return send_file(tilefn, 'image/png', unlink=(not savecache))



decals = None
def _get_decals():
    global decals
    if decals is None:
        from desi.common import Decals
        decals = Decals()
    return decals

def brick_list(req):
    import json

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
        return HttpResponse(json.dumps(dict(bricks=[])),
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

    return HttpResponse(json.dumps(dict(bricks=bricks)),
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
    import json
    from astrometry.util.util import Tan
    import numpy as np

    north = float(req.GET['north'])
    south = float(req.GET['south'])
    east  = float(req.GET['east'])
    west  = float(req.GET['west'])
    #print 'N,S,E,W:', north, south, east, west

    CCDS = _ccds_touching_box(north, south, east, west, Nmax=10000)

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

    return HttpResponse(json.dumps(dict(ccds=ccds)),
                        content_type='application/json')
    
def ccd_detail(req, ccd):
    import numpy as np
    #ccd = req.GET['ccd']
    words = ccd.split('-')
    assert(len(words) == 3)
    expnum = int(words[0], 10)
    assert(words[1][0] in 'NS')
    ns = words[1][0]
    chipnum = int(words[1][1:], 10)
    extname = '%s%i' % (ns,chipnum)

    D = _get_decals()
    CCDs = D.get_ccds()
    I = np.flatnonzero((CCDs.expnum == expnum) * 
                       np.array([n == extname for n in CCDs.extname]))
    assert(len(I) == 1)

    C = CCDs[I[0]]
    return HttpResponse('CCD %s, image %s, hdu %i' % (ccd, C.cpimage, C.cpimage_hdu))

    #return HttpResponse('CCD ' + ccd)

def nil(req):
    pass

def brick_detail(req, brickname):
    #brickname = req.GET['brick']
    return HttpResponse('Brick ' + brickname)

def cat_decals_dr1j(req, ver, zoom, x, y, tag='decals-dr1j'):
    return cat_decals(req, ver, zoom, x, y, tag=tag, docache=False)

def cat_decals(req, ver, zoom, x, y, tag='decals', docache=True):
    import json

    zoom = int(zoom)
    if zoom < 12:
        return HttpResponse(json.dumps(dict(rd=[], zoom=zoom,
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

    basedir = settings.DATA_DIR
    if docache:
        cachefn = os.path.join(basedir, 'cats-cache', tag,
                               '%i/%i/%i/%i.cat.json' % (ver, zoom, x, y))
        if os.path.exists(cachefn):
            # print 'Cached:', cachefn
            return send_file(cachefn, 'application/json',
                             modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'),
                             expires=oneyear)
    else:
        import tempfile
        f,cachefn = tempfile.mkstemp(suffix='.jpg')
        os.close(f)

    cat,hdr = _get_decals_cat(wcs, tag=tag)

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
        types = list([t[0] for t in cat.get('type')])
        fluxes = [dict(g=float(g), r=float(r), z=float(z))
                  for g,r,z in zip(cat.decam_flux[:,1], cat.decam_flux[:,2],
                                   cat.decam_flux[:,4])]
        bricknames = list(cat.brickname)
        objids = [int(x) for x in cat.objid]

    json = json.dumps(dict(rd=rd, sourcetype=types, fluxes=fluxes,
                                 bricknames=bricknames, objids=objids,
                                 zoom=int(zoom), tilex=int(x), tiley=int(y)))
    if docache:
        trymakedirs(cachefn)

    f = open(cachefn, 'w')
    f.write(json)
    f.close()
    return send_file(cachefn, 'application/json', expires=oneyear)

def _get_decals_cat(wcs, tag='decals'):
    from decals import settings
    from astrometry.util.fits import fits_table, merge_tables

    basedir = settings.DATA_DIR
    H,W = wcs.shape
    # print 'WCS shape:', H,W
    X = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                            [1,H/2,H,H,H,H/2,1,1])
    r,d = X[-2:]
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
        print 'Reading catalog', catfn
        T = fits_table(catfn)
        # FIXME -- all False
        # print 'brick_primary', np.unique(T.brick_primary)
        # T.cut(T.brick_primary)
        ok,xx,yy = wcs.radec2pixelxy(T.ra, T.dec)
        #print 'xx,yy', xx.min(), xx.max(), yy.min(), yy.max()
        T.cut((xx > 0) * (yy > 0) * (xx < W) * (yy < H))
        # print 'kept', len(T), 'from', catfn
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
                    bricks=None,
                    savecache = True, forcecache = False,
                    return_if_not_found=False, model_gz=False,
                    modeldir=None, scaledir=None, get_images=False,
                    ignoreCached=False,
                    ):
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

    basedir = settings.DATA_DIR
    tilefn = os.path.join(basedir, 'tiles', tag,
                          '%i/%i/%i/%i.jpg' % (ver, zoom, x, y))
    if os.path.exists(tilefn) and not ignoreCached:
        # print 'Cached:', tilefn
        return send_file(tilefn, 'image/jpeg', expires=oneyear,
                         modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'))
    else:
        print 'Tile image does not exist:', tilefn
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

    basepat = os.path.join(basedir, 'coadd', imagedir, '%(brickname).3s',
                           '%(brickname)s',
                           'decals-%(brickname)s-' + imagetag + '-%(band)s.fits')
    if modeldir is not None:
        modbasepat = os.path.join(basedir, 'coadd', modeldir, '%(brickname).3s',
                                  '%(brickname)s',
                                  'decals-%(brickname)s-' + imagetag + '-%(band)s.fits')
    else:
        modbasepat = basepat
    if model_gz and imagetag == 'model':
        modbasepat += '.gz'

    scaled = 0
    scalepat = None
    if scaledir is None:
        scaledir = imagedir
    if zoom < 14:
        scaled = (14 - zoom)
        scaled = np.clip(scaled, 1, 8)
        #print 'Scaled-down:', scaled
        dirnm = os.path.join(basedir, 'scaled', scaledir)
        scalepat = os.path.join(dirnm, '%(scale)i%(band)s', '%(brickname).3s', imagetag + '-%(brickname)s-%(band)s.fits')
        
    D = _get_decals()
    if bricks is None:
        B = D.get_bricks_readonly()
    else:
        B = bricks
    I = D.bricks_touching_radec_box(B, r.min(), r.max(), d.min(), d.max())
    print len(I), 'bricks touching zoom', zoom, 'x,y', x,y
    rimgs = []

    if len(I) == 0:
        if get_images:
            return None
        from django.http import HttpResponseRedirect
        if forcecache:
            # create symlink to blank.jpg!
            trymakedirs(tilefn)
            src = os.path.join(settings.STATIC_ROOT, 'blank.jpg')
            os.symlink(src, tilefn)
            print 'Symlinked', tilefn, '->', src
        return HttpResponseRedirect(settings.STATIC_URL + 'blank.jpg')

    foundany = False
    for band in bands:
        rimg = np.zeros((H,W), np.float32)
        rn   = np.zeros((H,W), np.uint8)
        for i,brickid,brickname in zip(I,B.brickid[I], B.brickname[I]):
            has = getattr(B, 'has_%s' % band, None)
            if has is not None and not has[i]:
                # No coverage for band in this brick.
                print 'Brick', brickname, 'has no', band, 'band'
                continue

            fnargs = dict(band=band, brick=brickid, brickname=brickname)

            if imagetag == 'resid':
                basefn = basepat % fnargs

                modbasefn = modbasepat % fnargs
                modbasefn = modbasefn.replace('resid', 'model')
                if model_gz:
                    modbasefn += '.gz'

                if scalepat is None:
                    imscalepat = None
                    modscalepat = None
                else:
                    imscalepat = scalepat.replace('resid', 'image')
                    modscalepat = scalepat.replace('resid', 'model')
                imbasefn = basefn.replace('resid', 'image')
                imfn = get_scaled(imscalepat, fnargs, scaled, imbasefn)
                # print 'imfn', imfn
                modfn = get_scaled(modscalepat, fnargs, scaled, modbasefn)
                # print 'modfn', modfn
                fn = imfn

            else:
                basefn = basepat % fnargs
                fn = get_scaled(scalepat, fnargs, scaled, basefn)
            if fn is None:
                # print 'Filename:', fn
                print 'not found: brick', brickname, 'band', band, 'with basefn', basefn
                savecache = False
                continue
            if not os.path.exists(fn):
                print 'Does not exist:', fn
                # dr = fn
                # for x in range(10):
                #     dr = os.path.dirname(dr)
                #     print 'dir', dr, 'exists?', os.path.exists(dr)
                savecache = False
                continue
            try:
                #bwcs = Tan(fn, 0)
                bwcs = _read_tan_wcs(fn, 0)
            except:
                print 'Failed to read WCS:', fn
                savecache = False
                import traceback
                import sys
                traceback.print_exc(None, sys.stdout)
                continue

            foundany = True
            print 'Reading', fn
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
                print 'Resampling exception'
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
        # print 'Band', band, ': total of', rn.sum(), 'pixels, range', rimg.min(), rimg.max()

    #if return_if_not_found and not foundany:
    if return_if_not_found and not savecache:
        return

    if get_images:
        return rimgs

    rgb = get_rgb(rimgs, bands, **rgbkwargs)

    trymakedirs(tilefn)

    if forcecache:
        savecache = True

    if not savecache:
        import tempfile
        f,tilefn = tempfile.mkstemp(suffix='.jpg')
        os.close(f)

    #import matplotlib
    #matplotlib.use('Agg')
    import pylab as plt
    #plt.imsave(tilefn, rgb)

    # no jpeg output support in matplotlib in some installations...
    if True:
        import tempfile
        f,tempfn = tempfile.mkstemp(suffix='.png')
        os.close(f)
        plt.imsave(tempfn, rgb)
        cmd = 'pngtopnm %s | pnmtojpeg -quality 90 > %s' % (tempfn, tilefn)
        os.system(cmd)
        os.unlink(tempfn)
        print 'Wrote', tilefn

    return send_file(tilefn, 'image/jpeg', unlink=(not savecache))



def cutouts(req):
    from astrometry.util.util import Tan
    from astrometry.util.starutil_numpy import degrees_between
    import numpy as np
    from desi.common import wcs_for_brick

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
        #c = dict([(k,c.get(k)) for k in c.columns()])
        #print 'CCD', c
        ccds.append((c, x, y))

    #print 'CCDS:', ccds

    D = _get_decals()
    B = D.get_bricks_readonly()

    I = np.flatnonzero((B.ra1  <= ra)  * (B.ra2  >= ra) *
                       (B.dec1 <= dec) * (B.dec2 >= dec))
    brick = B[I[0]]
    bwcs = wcs_for_brick(brick)
    ok,brickx,bricky = bwcs.radec2pixelxy(ra, dec)
    brick = brick.to_dict()
    
    from django.shortcuts import render
    from django.core.urlresolvers import reverse

    #url = req.build_absolute_uri('/') + reverse('cutout_panels',
    #                                            kwargs=dict(expnum='%i',
    #                                                      extname='%s'))

    from decals import settings

    url = req.build_absolute_uri('/') + settings.ROOT_URL + '/cutout_panels/%i/%s/'

    print 'URL', url

    # Deployment: http://{s}.DOMAIN/...
    url = url.replace('://www.', '://')
    url = url.replace('://', '://%s.')

    domains = ['a','b','c','d']

    print 'URL', url
    ccdsx = []
    for i,(ccd,x,y) in enumerate(ccds):
        fn = ccd.cpimage.replace(settings.DATA_DIR + '/', '')
        ccdsx.append(('CCD %s %i %s x,y %i,%i<br/><small>(%s [%i])</small>' % (ccd.filter, ccd.expnum, ccd.extname, x, y, fn, ccd.cpimage_hdu),
                      url % (domains[i%len(domains)], int(ccd.expnum), ccd.extname) + '?x=%i&y=%i' % (x,y)))

    return render(req, 'cutouts.html',
                  dict(ra=ra, dec=dec,
                       ccds=ccdsx,
                       brick=brick,
                       brickx=brickx,
                       bricky=bricky,
                       ))

def cat_plot(req):
    import pylab as plt
    import numpy as np
    from astrometry.util.util import Tan
    from desi.common import get_sdss_sources
    from decals import settings

    ra = float(req.GET['ra'])
    dec = float(req.GET['dec'])

    ver = float(req.GET.get('ver',2))

    # half-size in DECam pixels
    size = 50
    W,H = size*2, size*2
    
    pixscale = 0.262 / 3600.
    wcs = Tan(*[float(x) for x in [
        ra, dec, size+0.5, size+0.5, -pixscale, 0., 0., pixscale, W, H]])

    M = 10
    margwcs = wcs.get_subimage(-M, -M, W+2*M, H+2*M)

    cat,hdr = _get_decals_cat(margwcs, tag='decals-dr1j')

    # FIXME
    nil,sdss = get_sdss_sources('r', margwcs,
                                photoobjdir=os.path.join(settings.DATA_DIR, 'sdss'),
                                local=True)
    import tempfile
    f,tempfn = tempfile.mkstemp(suffix='.png')
    os.close(f)

    f = plt.figure(figsize=(2,2))
    f.subplots_adjust(left=0.01, bottom=0.01, top=0.99, right=0.99)
    f.clf()
    ax = f.add_subplot(111, xticks=[], yticks=[])
    if cat is not None:
        ok,x,y = wcs.radec2pixelxy(cat.ra, cat.dec)
        # matching the plot colors in index.html
        # cc = dict(S=(0x9a, 0xfe, 0x2e),
        #           D=(0xff, 0, 0),
        #           E=(0x58, 0xac, 0xfa),
        #           C=(0xda, 0x81, 0xf5))
        cc = dict(PSF =(0x9a, 0xfe, 0x2e),
                  DEV =(0xff, 0, 0),
                  EXP =(0x58, 0xac, 0xfa),
                  COMP=(0xda, 0x81, 0xf5))
        ax.scatter(x, y, s=50, c=[[float(x)/255. for x in cc[t.strip()]] for t in cat.type])
    if sdss is not None:
        ok,x,y = wcs.radec2pixelxy(sdss.ra, sdss.dec)
        ax.scatter(x, y, s=30, marker='x', c='k')
    ax.axis([0, W, 0, H])
    f.savefig(tempfn)

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
    basedir = settings.DATA_DIR
    fn = ccd.cpimage.strip()
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
    print 'Image slice:', slc
    img = img[slc]
    return img,slc,xstart,ystart

def cutout_panels(req, expnum=None, extname=None):
    import pylab as plt
    import numpy as np

    x = int(req.GET['x'], 10)
    y = int(req.GET['y'], 10)
    ccd = _get_ccd(expnum, extname)

    fn = _get_image_filename(ccd)
    if not os.path.exists(fn):
        #print 'NO IMAGE:', fn
        #print 'rsync -Rrv carver:tractor/decals/images/./' + fn.replace('/home/dstn/decals-web/data/images/', '') + ' data/images'
        return HttpResponse('no such image: ' + fn)

    wfn = fn.replace('ooi', 'oow')
    if not os.path.exists(wfn):
        #cmd = 'rsync -Rrv carver:tractor/decals/images/./' + wfn.replace('/home/dstn/decals-web/data/images/', '') + ' data/images'
        #print '\n' + cmd + '\n'
        #os.system(cmd)
        #if not os.path.exists(wfn):
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
    tim = im.get_tractor_image(decals, slc=slc, tiny=1, const2psf=True, pvwcs=True)

    if tim is None:
        img = np.zeros((0,0))

    mn,mx = -1, 100
    arcsinh = 1.
    cmap = 'gray'
    pad = True

    scales = dict(g = (2, 0.0066),
                  r = (1, 0.01),
                  z = (0, 0.025),
                  )
    rows,cols = 1,5
    f = plt.figure(figsize=(cols,rows))
    f.clf()
    f.subplots_adjust(left=0.002, bottom=0.02, top=0.995, right=0.998,
                      wspace=0.02, hspace=0)

    imgs = []

    img = tim.getImage()
    imgs.append((img,None))
    
    M = 10
    margwcs = tim.subwcs.get_subimage(-M, -M, int(tim.subwcs.get_width())+2*M, int(tim.subwcs.get_height())+2*M)
    for dr in ['dr1j']:
        cat,hdr = _get_decals_cat(margwcs, tag='decals-%s' % dr)
        if cat is None:
            tcat = []
        else:
            cat.shapedev = np.vstack((cat.shapedev_r, cat.shapedev_e1, cat.shapedev_e2)).T
            cat.shapeexp = np.vstack((cat.shapeexp_r, cat.shapeexp_e1, cat.shapeexp_e2)).T
            tcat = read_fits_catalog(cat, hdr=hdr)
        tr = Tractor([tim], tcat)
        img = tr.getModelImage(0)
        imgs.append((img,None))

        img = tr.getChiImage(0)
        imgs.append((img, dict(mn=-5,mx=5, arcsinh = None, scale = 1.)))

    th,tw = tim.shape
    pp = tim.getPsf().getPointSourcePatch(tw/2., th/2.)
    img = np.zeros(tim.shape, np.float32)
    pp.addTo(img)
    imgs.append((img, dict(scale=0.0001, cmap='hot')))
    
    from tractor.psfex import PsfEx
    from tractor.patch import Patch
    # HACK hard-coded image sizes.
    thepsf = PsfEx(im.psffn, 2046, 4096)
    psfim = thepsf.instantiateAt(x, y)
    img = np.zeros(tim.shape, np.float32)
    h,w = tim.shape
    ph,pw = psfim.shape
    patch = Patch((w-pw)/2., (h-ph)/2., psfim)
    patch.addTo(img)
    imgs.append((img, dict(scale = 0.0001, cmap = 'hot')))

    for i,(img,d) in enumerate(imgs):

        mn,mx = -5, 100
        arcsinh = 1.
        cmap = 'gray'
        nil,scale = scales[ccd.filter]
        pad = True

        if d is not None:
            if 'mn' in d:
                mn = d['mn']
            if 'mx' in d:
                mx = d['mx']
            if 'arcsinh' in d:
                arcsinh = d['arcsinh']
            if 'cmap' in d:
                cmap = d['cmap']
            if 'scale' in d:
                scale = d['scale']

        img = img / scale
        if arcsinh is not None:
            def nlmap(x):
                return np.arcsinh(x * arcsinh) / np.sqrt(arcsinh)
            img = nlmap(img)
            mn = nlmap(mn)
            mx = nlmap(mx)

        img = (img - mn) / (mx - mn)
        if pad:
            ih,iw = img.shape
            padimg = np.zeros((2*size,2*size), img.dtype) + 0.5
            print 'Image shape:', img.shape, 'pad shape:', padimg.shape
            padimg[ystart:ystart+ih, xstart:xstart+iw] = img
            img = padimg

        ax = f.add_subplot(rows, cols, i+1, xticks=[], yticks=[])
        # the chips are turned sideways :)
        #plt.imshow(np.rot90(np.clip(img, 0, 1), k=3), cmap=cmap,
        #           interpolation='nearest', origin='lower')
        ax.imshow(np.rot90(np.clip(img, 0, 1).T, k=2), cmap=cmap,
                   interpolation='nearest', origin='lower')
        #ax.xticks([]); ax.yticks([])

    import tempfile
    ff,tilefn = tempfile.mkstemp(suffix='.jpg')
    os.close(ff)

    f.savefig(tilefn)
    f.clf()
    del f
    
    return send_file(tilefn, 'image/jpeg', unlink=True,
                     expires=3600)




if __name__ == '__main__':
    class duck(object):
        pass

    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'
    
    ver = 1
    zoom,x,y = 2, 1, 1
    req = duck()
    req.META = dict()
    map_unwise_w1w2(req, ver, zoom, x, y, savecache=True, ignoreCached=True)
