from __future__ import print_function
if __name__ == '__main__':
    import sys
    sys.path.insert(0, 'django-1.7')

import os
from django.http import HttpResponse, StreamingHttpResponse

from decals import settings
from map.utils import get_tile_wcs

import matplotlib
matplotlib.use('Agg')

# We add a version number to each layer, to allow long cache times
# for the tile JPEGs.  Increment this version to invalidate
# client-side caches.

debug = print
if not settings.DEBUG_LOGGING:
    def debug(*args, **kwargs):
        pass

tileversions = {
    'sfd': [1,],
    'halpha': [1,],
    'sdss': [1,],
    'sdssco': [1,],

    'mobo-dr3': [1],
    'mobo-dr3-model': [1],
    'mobo-dr3-resid': [1],
    
    'decals-dr3': [1],
    'decals-dr3-model': [1],
    'decals-dr3-resid': [1],

    'decals-dr2': [1, 2],
    'decals-dr2-model': [1],
    'decals-dr2-resid': [1],

    'decals-dr1k': [1],
    'decals-model-dr1k': [1],
    'decals-resid-dr1k': [1],

    'decals-dr1n': [1],
    'decals-model-dr1n': [1],
    'decals-resid-dr1n': [1],

    'decals-dr1j': [1],
    'decals-model-dr1j': [1],
    'decals-resid-dr1j': [1],
    'decals-nexp-dr1j': [1],

    'decals-wl': [4],

    'decam-depth-g': [1],
    'decam-depth-r': [1],
    'decam-depth-z': [1],

    'unwise-w1w2': [1],
    'unwise-neo1': [1],
    #'unwise-w3w4': [1],
    #'unwise-w1234': [1],

    'cutouts': [1],
    }

catversions = {
    'decals-dr1j': [1,],
    'decals-dr2': [2,],
    'decals-dr3': [1,],
    'ngc': [1,],
    'spec': [1,],
    'spec-deep2': [1,],
    'bright': [1,],
    'tycho2': [1,],
}

oneyear = (3600 * 24 * 365)

def trymakedirs(fn):
    dirnm = os.path.dirname(fn)
    if not os.path.exists(dirnm):
        try:
            os.makedirs(dirnm)
        except:
            pass

def save_jpeg(fn, rgb, **kwargs):
    import pylab as plt
    import tempfile
    f,tempfn = tempfile.mkstemp(suffix='.png')
    os.close(f)
    plt.imsave(tempfn, rgb, **kwargs)
    cmd = 'pngtopnm %s | pnmtojpeg -quality 90 > %s' % (tempfn, fn)
    os.system(cmd)
    os.unlink(tempfn)

def _read_tansip_wcs(sourcefn, ext, hdr=None, W=None, H=None, tansip=None):
    wcs = None
    if not sourcefn.endswith('.gz'):
        try:
            wcs = tansip(sourcefn, ext)
        except:
            pass
    return wcs

def _read_tan_wcs(sourcefn, ext, hdr=None, W=None, H=None, fitsfile=None):
    from astrometry.util.util import Tan
    wcs = _read_tansip_wcs(sourcefn, ext, hdr=hdr, W=W, H=H, tansip=Tan)
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

def _read_sip_wcs(sourcefn, ext, hdr=None, W=None, H=None, fitsfile=None):
    from astrometry.util.util import Sip
    return _read_tansip_wcs(sourcefn, ext, hdr=hdr, W=W, H=H, tansip=Sip)

def ra2long(ra):
    lng = 180. - ra
    lng += 360 * (lng < 0.)
    lng -= 360 * (lng > 360.)
    return lng

def ra2long_B(ra):
    lng = 180. - ra
    lng += 360 * (lng < -180.)
    lng -= 360 * (lng >  180.)
    return lng

def send_file(fn, content_type, unlink=False, modsince=None, expires=3600,
              filename=None):
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
        #print('If-modified-since:', modsince #Sat, 22 Nov 2014 01:12:39 GMT)
        ifmod = datetime.datetime.strptime(modsince, '%a, %d %b %Y %H:%M:%S %Z')
        #print('Parsed:', ifmod)
        #print('Last mod:', lastmod)
        dt = (lastmod - ifmod).total_seconds()
        if dt < 1:
            from django.http import HttpResponseNotModified
            return HttpResponseNotModified()

    res = StreamingHttpResponse(f, content_type=content_type)
    # res['Cache-Control'] = 'public, max-age=31536000'
    res['Content-Length'] = st.st_size
    if filename is not None:
        res['Content-Disposition'] = 'attachment; filename="%s"' % filename
    # expires in an hour?
    now = datetime.datetime.utcnow()
    then = now + datetime.timedelta(0, expires, 0)
    timefmt = '%a, %d %b %Y %H:%M:%S GMT'
    res['Expires'] = then.strftime(timefmt)
    res['Last-Modified'] = lastmod.strftime(timefmt)
    return res

galaxycat = None

def get_random_galaxy():
    import numpy as np

    global galaxycat
    galfn = os.path.join(settings.DATA_DIR, 'galaxy-cats-in-dr2.fits')

    if galaxycat is None and not os.path.exists(galfn):
        import astrometry.catalogs
        from astrometry.util.fits import fits_table, merge_tables
        import fitsio
        from astrometry.util.util import Tan

        fn = os.path.join(os.path.dirname(astrometry.catalogs.__file__), 'ngc2000.fits')
        NGC = fits_table(fn)
        print(len(NGC), 'NGC objects')
        NGC.name = np.array(['NGC %i' % n for n in NGC.ngcnum])
        NGC.delete_column('ngcnum')
        
        fn = os.path.join(os.path.dirname(astrometry.catalogs.__file__), 'ic2000.fits')
        IC = fits_table(fn)
        print(len(IC), 'IC objects')
        IC.name = np.array(['IC %i' % n for n in IC.icnum])
        IC.delete_column('icnum')

        fn = os.path.join(settings.DATA_DIR, 'ugc.fits')
        UGC = fits_table(fn)
        print(len(UGC), 'UGC objects')
        UGC.name = np.array(['UGC %i' % n for n in UGC.ugcnum])
        UGC.delete_column('ugcnum')

        T = merge_tables([NGC, IC, UGC])
        T.writeto(os.path.join(settings.DATA_DIR, 'galaxy-cats.fits'))
        
        keep = np.zeros(len(T), bool)

        bricks = _get_dr2_bricks()
        bricks.cut(bricks.has_g * bricks.has_r * bricks.has_z)
        print(len(bricks), 'bricks with grz')

        for brick in bricks:
            dirnm = os.path.join(settings.DATA_DIR, 'coadd', 'decals-dr2',
                                 '%.3s' % brick.brickname, brick.brickname)
            fn = os.path.join(dirnm,
                              'decals-%s-nexp-r.fits.gz' % brick.brickname)
            if not os.path.exists(fn):
                print('Does not exist:', fn)
                continue

            I = np.flatnonzero((T.ra  >= brick.ra1 ) * (T.ra  < brick.ra2 ) *
                               (T.dec >= brick.dec1) * (T.dec < brick.dec2))
            if len(I) == 0:
                continue
            print('Brick', brick.brickname, 'has', len(I), 'objs')

            nn = fitsio.read(fn)
            h,w = nn.shape
            imgfn = os.path.join(dirnm,
                                 'decals-%s-image-r.fits' % brick.brickname)
            wcs = Tan(imgfn)

            ok,x,y = wcs.radec2pixelxy(T.ra[I], T.dec[I])
            x = np.clip((x-1).astype(int), 0, w-1)
            y = np.clip((y-1).astype(int), 0, h-1)
            n = nn[y,x]
            keep[I[n > 0]] = True

        T.cut(keep)
        T.writeto(galfn)

    if galaxycat is None:
        from astrometry.util.fits import fits_table
        galaxycat = fits_table(galfn)

    i = np.random.randint(len(galaxycat))
    ra = galaxycat.ra[i]
    dec = galaxycat.dec[i]
    name = galaxycat.name[i].strip()
    return ra,dec,name

def index(req):
    layer = req.GET.get('layer', 'decals-dr2')
    # Nice spiral galaxy
    #ra, dec, zoom = 244.7, 7.4, 13

    ra = dec = None
    zoom = 13

    try:
        zoom = int(req.GET.get('zoom', zoom))
    except:
        pass
    try:
        ra = float(req.GET.get('ra'))
    except:
        pass
    try:
        dec = float(req.GET.get('dec'))
    except:
        pass

    galname = None
    if ra is None or dec is None:
        ra,dec,galname = get_random_galaxy()

    lat,lng = dec, ra2long(ra)

    url = req.build_absolute_uri(settings.ROOT_URL) + '/{id}/{ver}/{z}/{x}/{y}.jpg'
    caturl = settings.CAT_URL

    smallcaturl = settings.ROOT_URL + '/{id}/{ver}/cat.json?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}'

    tileurl = settings.TILE_URL

    subdomains = settings.SUBDOMAINS
    # convert to javascript
    subdomains = '[' + ','.join(["'%s'" % s for s in subdomains]) + '];'

    static_tile_url = settings.STATIC_TILE_URL

    ccdsurl = settings.ROOT_URL + '/ccds/?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&id={id}'
    bricksurl = settings.ROOT_URL + '/bricks/?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&id={id}'
    expsurl = settings.ROOT_URL + '/exps/?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&id={id}'
    platesurl = settings.ROOT_URL + '/sdss-plates/?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}'
    sqlurl = settings.ROOT_URL + '/sql-box/?north={north}&east={east}&south={south}&west={west}&q={q}'
    namequeryurl = settings.ROOT_URL + '/namequery/?obj={obj}'

    baseurl = req.path

    absurl = req.build_absolute_uri(settings.ROOT_URL)

    from django.shortcuts import render

    return render(req, 'index.html',
                  dict(ra=ra, dec=dec, zoom=zoom,
                       galname=galname,
                       layer=layer, tileurl=tileurl,
                       absurl=absurl,
                       sqlurl=sqlurl,
                       baseurl=baseurl, caturl=caturl, bricksurl=bricksurl,
                       smallcaturl=smallcaturl,
                       namequeryurl=namequeryurl,
                       ccdsurl=ccdsurl,
                       expsurl=expsurl,
                       platesurl=platesurl,
                       static_tile_url=static_tile_url,
                       subdomains=subdomains,
                       maxNativeZoom = settings.MAX_NATIVE_ZOOM,
                       enable_sql = settings.ENABLE_SQL,
                       enable_vcc = settings.ENABLE_VCC,
                       enable_wl = settings.ENABLE_WL,
                       enable_cutouts = settings.ENABLE_CUTOUTS,
                       ))

def get_scaled(scalepat, scalekwargs, scale, basefn, read_wcs=None, read_base_wcs=None,
               wcs=None, img=None, return_data=False):
    from scipy.ndimage.filters import gaussian_filter
    import fitsio
    from astrometry.util.util import Tan
    import tempfile
    import numpy as np

    if scale <= 0:
        return basefn
    fn = scalepat % dict(scale=scale, **scalekwargs)

    if read_wcs is None:
        read_wcs = _read_tan_wcs

    if os.path.exists(fn):
        if return_data:
            F = fitsio.FITS(sourcefn)
            img = F[0].read()
            hdr = F[0].read_header()
            wcs = read_wcs(fn, 0, hdr=hdr, W=W, H=H, fitsfile=F)
            return img,wcs,fn
        return fn

    if img is None:
        sourcefn = get_scaled(scalepat, scalekwargs, scale-1, basefn,
                              read_base_wcs=read_base_wcs, read_wcs=read_wcs)
        debug('Source:', sourcefn)
        if sourcefn is None or not os.path.exists(sourcefn):
            debug('Image source file', sourcefn, 'not found')
            return None
        try:
            debug('Reading:', sourcefn)
            F = fitsio.FITS(sourcefn)
            img = F[0].read()
            hdr = F[0].read_header()
        except:
            debug('Failed to read:', sourcefn)
            return None

    H,W = img.shape
    # make even size; smooth down
    if H % 2 == 1:
        img = img[:-1,:]
    if W % 2 == 1:
        img = img[:,:-1]
    img = gaussian_filter(img, 1.)
    # bin
    I2 = (img[::2,::2] + img[1::2,::2] + img[1::2,1::2] + img[::2,1::2])/4.
    I2 = I2.astype(np.float32)

    # shrink WCS too
    if wcs is None:
        if scale == 1:
            # Use the given function to read base WCS.
            if read_base_wcs is not None:
                read_wcs = read_base_wcs
        wcs = read_wcs(sourcefn, 0, hdr=hdr, W=W, H=H, fitsfile=F)
    # include the even size clip; this may be a no-op
    H,W = img.shape
    wcs = wcs.get_subimage(0, 0, W, H)
    wcs2 = wcs.scale(0.5)

    dirnm = os.path.dirname(fn)

    from decals import settings
    ro = settings.READ_ONLY_BASEDIR
    if ro:
        dirnm = None

    hdr = fitsio.FITSHDR()
    wcs2.add_to_header(hdr)
    trymakedirs(fn)
    f,tmpfn = tempfile.mkstemp(suffix='.fits.tmp', dir=dirnm)
    os.close(f)
    debug('Temp file', tmpfn)
    # To avoid overwriting the (empty) temp file (and fitsio
    # debuging "Removing existing file")
    os.unlink(tmpfn)
    fitsio.write(tmpfn, I2, header=hdr, clobber=True)
    if not ro:
        os.rename(tmpfn, fn)
        debug('Wrote', fn)
    if return_data:
        return I2,wcs2,fn
    return fn

def name_query(req):
    import json
    import urllib
    import urllib2

    obj = req.GET.get('obj')
    #print('Name query: "%s"' % obj)

    if len(obj) == 0:
        ra,dec,name = get_random_galaxy()
        return HttpResponse(json.dumps(dict(ra=ra, dec=dec, name=name)),
                            content_type='application/json')

    url = 'http://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame//NSV?'
    url += urllib.urlencode(dict(q=obj)).replace('q=','')

    print('URL', url)

    '''
    # IC 1200#Q2671982
    #=N=NED:    1     0ms (from cache)
    %C G     
    %J 241.1217083 +69.6657778 = 16:04:29.20 +69:39:56.8
    %J.E [1250.00 1250.00 0] 20032MASX.C.......:
    %V v 7449.84363 [38.07365] 2003AJ....126.2268W
    %T E                   
    %MAG 13.74
    %I.0 NGC 6079 =[G]
    #B 17

    # IC 12000#Q2672097
    #! *** Nothing found *** 
    #====Done (2016-Mar-04,17:43:13z)====

    '''
    try:
        f = urllib2.urlopen(url)
        code = f.getcode()
        print('Code', code)
        for line in f.readlines():
            words = line.split()
            if len(words) == 0:
                continue
            if words[0] == '%J':
                ra = float(words[1])
                dec = float(words[2])
                return HttpResponse(json.dumps(dict(ra=ra, dec=dec, name=obj)),
                                    content_type='application/json')
            if words[0] == '#!':
                return HttpResponse(json.dumps(dict(error=' '.join(words[1:]))),
                                    content_type='application/json')

    except Exception as e:
        return HttpResponse(json.dumps(dict(error=str(e))),
                            content_type='application/json')

def data_for_radec(req):
    import numpy as np
    ra  = float(req.GET['ra'])
    dec = float(req.GET['dec'])
    bricks = _get_dr2_bricks()
    I = np.flatnonzero((ra >= bricks.ra1) * (ra < bricks.ra2) *
                       (dec >= bricks.dec1) * (dec < bricks.dec2))
    if len(I) == 0:
        return HttpResponse('No DECaLS DR2 data overlaps RA,Dec = %.4f, %.4f' % (ra,dec))
    I = I[0]
    brickname = bricks.brickname[I]

    return brick_detail(req, brickname)





# "PR"
#rgbkwargs=dict(mnmx=(-0.3,100.), arcsinh=1.))

rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)

rgbkwargs_nexp = dict(mnmx=(0,25), arcsinh=1.,
                      scales=dict(g=(2,1),r=(1,1),z=(0,1)))

def jpeg_cutout_decals_dr1j(req):
    return cutout_decals(req, jpeg=True, default_tag='decals-dr1j')

def fits_cutout_decals_dr1j(req):
    return cutout_decals(req, fits=True, default_tag='decals-dr1j')

def jpeg_cutout_decals_dr2(req):
    return cutout_decals(req, jpeg=True, default_tag='decals-dr2', dr2=True)

def fits_cutout_decals_dr2(req):
    return cutout_decals(req, fits=True, default_tag='decals-dr2', dr2=True)

def cutout_decals(req, jpeg=False, fits=False, default_tag='decals-dr1j',
                  dr2=False):

    kwa = {}
    tag = req.GET.get('tag', None)
    debug('Requested tag:', tag)
    if not tag in ['decals-dr1n', 'decals-model', 'decals-resid']:
        # default
        tag = default_tag
    debug('Using tag:', tag)

    imagetag = 'image'
    if tag == 'decals-model':
        tag = default_tag
        imagetag = 'model'
        kwa.update(add_gz=True)
    elif tag == 'decals-resid':
        tag = default_tag
        imagetag = 'resid'
        kwa.update(model_gz=True)

    bricks = None
    if tag == 'decals-dr1n':
        bricks = get_dr1n_bricks()
    if dr2:
        bricks = _get_dr2_bricks()

    hdr = None
    if fits:
        import fitsio
        hdr = fitsio.FITSHDR()
        hdr['SURVEY'] = 'DECaLS'
        if dr2:
            hdr['VERSION'] = 'DR2'
        else:
            hdr['VERSION'] = 'DR1'

    rgbfunc = None
    if dr2:
        rgbfunc = dr2_rgb

    #print('Calling cutout_on_bricks: tag="%s"' % tag)
        
    return cutout_on_bricks(req, tag, bricks=bricks, imagetag=imagetag,
                            jpeg=jpeg, fits=fits,
                            drname=tag,
                            rgbfunc=rgbfunc, outtag=tag, hdr=hdr)


def jpeg_cutout_sdssco(req):
    return cutout_sdssco(req, jpeg=True)

def fits_cutout_sdssco(req):
    return cutout_sdssco(req, fits=True)

def cutout_sdssco(req, jpeg=False, fits=False):
    hdr = None
    if fits:
        import fitsio
        hdr = fitsio.FITSHDR()
        hdr['SURVEY'] = 'SDSS'

    # data/coadd/sdssco/000/sdssco-0001m002-g.fits
    from decals import settings
    basedir = settings.DATA_DIR
    basepat = os.path.join(basedir, 'coadd', 'sdssco', '%(brickname).3s',
                           'sdssco-%(brickname)s-%(band)s.fits')

    return cutout_on_bricks(req, 'sdssco', bricks=get_sdssco_bricks(), imagetag='sdssco',
                            jpeg=jpeg, fits=fits,
                            pixscale=0.396, bands='gri', native_zoom=13, maxscale=6,
                            rgbfunc=sdss_rgb, outtag='sdss', hdr=hdr, basepat=basepat)

def cutout_on_bricks(req, tag, imagetag='image', jpeg=False, fits=False,
                     pixscale=0.262, bands='grz', native_zoom=14, ver=1,
                     hdr=None, outtag=None, **kwargs):

    native_pixscale = pixscale

    ra  = float(req.GET['ra'])
    dec = float(req.GET['dec'])
    pixscale = float(req.GET.get('pixscale', pixscale))
    maxsize = 1024
    size   = min(int(req.GET.get('size',    256)), maxsize)
    width  = min(int(req.GET.get('width',  size)), maxsize)
    height = min(int(req.GET.get('height', size)), maxsize)

    if not 'pixscale' in req.GET and 'zoom' in req.GET:
        zoom = int(req.GET.get('zoom'))
        pixscale = pixscale * 2**(native_zoom - zoom)

    bands = req.GET.get('bands', bands)
    #bands = [b for b in 'grz' if b in bands]

    from astrometry.util.util import Tan
    import numpy as np
    import fitsio
    import tempfile

    ps = pixscale / 3600.
    raps = -ps
    decps = ps
    if jpeg:
        decps *= -1.
    wcs = Tan(*[float(x) for x in [ra, dec, (width+1)/2., (height+1)/2.,
                                   raps, 0., 0., decps, width, height]])

    zoom = native_zoom - int(np.round(np.log2(pixscale / native_pixscale)))
    zoom = max(0, min(zoom, 16))

    #print('Calling map_coadd_bands: tag="%s"' % tag)
    
    rtn = map_coadd_bands(req, ver, zoom, 0, 0, bands, 'cutouts',
                          tag, wcs=wcs, imagetag=imagetag,
                          savecache=False, get_images=fits, **kwargs)

    if jpeg:
        return rtn
    ims = rtn

    if hdr is not None:
        hdr['BANDS'] = ''.join(bands)
        for i,b in enumerate(bands):
            hdr['BAND%i' % i] = b
        wcs.add_to_header(hdr)

    f,tmpfn = tempfile.mkstemp(suffix='.fits')
    os.close(f)
    os.unlink(tmpfn)

    if len(bands) > 1:
        cube = np.empty((len(bands), height, width), np.float32)
        for i,im in enumerate(ims):
            cube[i,:,:] = im
    else:
        cube = ims[0]
    del ims
    fitsio.write(tmpfn, cube, clobber=True, header=hdr)
    if outtag is None:
        fn = 'cutout_%.4f_%.4f.fits' % (ra,dec)
    else:
        fn = 'cutout_%s_%.4f_%.4f.fits' % (outtag, ra,dec)
    return send_file(tmpfn, 'image/fits', unlink=True, filename=fn)

def jpeg_cutout(req):
    layer = req.GET.get('layer', 'decals-dr2')
    if layer == 'decals-dr1j':
        return jpeg_cutout_decals_dr1j(req)
    if layer in ['sdss', 'sdssco']:
        return jpeg_cutout_sdssco(req)
    return jpeg_cutout_decals_dr2(req)

B_sdssco = None

def get_sdssco_bricks():
    global B_sdssco
    if B_sdssco is None:
        from decals import settings
        from astrometry.util.fits import fits_table
        basedir = settings.DATA_DIR
        B_sdssco = fits_table(os.path.join(basedir, 'bricks-sdssco.fits'),
                              columns=['brickname', 'ra1', 'ra2', 'dec1', 'dec2'])
    return B_sdssco


def map_sdssco(req, ver, zoom, x, y, savecache=None, tag='sdssco',
               get_images=False,
               wcs=None,
               **kwargs):
    from decals import settings

    if savecache is None:
        savecache = settings.SAVE_CACHE

    B_sdssco = get_sdssco_bricks()

    bands = 'gri'
    basedir = settings.DATA_DIR
    basepat = os.path.join(basedir, 'coadd', tag, '%(brickname).3s',
                           'sdssco-%(brickname)s-%(band)s.fits')
    return map_coadd_bands(req, ver, zoom, x, y, bands, tag, tag,
                           imagetag=tag,
                           get_images=get_images,
                           savecache=savecache,
                           rgbfunc=sdss_rgb, basepat=basepat, bricks=B_sdssco,
                           nativescale=13, maxscale=6, **kwargs)

def sdss_rgb(rimgs, bands, scales=None,
             m = 0.02):
    import numpy as np
    rgbscales = {'u': 1.5, #1.0,
                 'g': 2.5,
                 'r': 1.5,
                 'i': 1.0,
                 'z': 0.4, #0.3
                 }
    if scales is not None:
        rgbscales.update(scales)
        
    b,g,r = [rimg * rgbscales[b] for rimg,b in zip(rimgs, bands)]
    r = np.maximum(0, r + m)
    g = np.maximum(0, g + m)
    b = np.maximum(0, b + m)
    I = (r+g+b)/3.
    Q = 20
    #alpha = 1.0
    #m2 = 0.
    #fI = np.arcsinh(alpha * Q * (I - m2)) / np.sqrt(Q)
    fI = np.arcsinh(Q * I) / np.sqrt(Q)
    I += (I == 0.) * 1e-6
    R = fI * r / I
    G = fI * g / I
    B = fI * b / I
    # maxrgb = reduce(np.maximum, [R,G,B])
    # J = (maxrgb > 1.)
    # R[J] = R[J]/maxrgb[J]
    # G[J] = G[J]/maxrgb[J]
    # B[J] = B[J]/maxrgb[J]
    rgb = np.dstack((R,G,B))
    rgb = np.clip(rgb, 0, 1)
    return rgb

def layer_name_map(name):
    return {'decals-dr2-model': 'decals-dr2',
            'decals-dr2-resid': 'decals-dr2',
            'decals-dr2-ccds': 'decals-dr2',
            'decals-dr2-exps': 'decals-dr2',
            'decals-bricks': 'decals-dr2',

            'decals-dr3-ccds': 'decals-dr3',
            'decals-dr3-exps': 'decals-dr3',

            'mobo-dr3-ccds': 'mobo-dr3',

    }.get(name, name)

B_dr2 = None
def _get_dr2_bricks():
    global B_dr2
    if B_dr2 is not None:
        return B_dr2

    fn = os.path.join(settings.DATA_DIR, 'decals-dr2', 'decals-bricks-in-dr2.fits')
    if os.path.exists(fn):
        from astrometry.util.fits import fits_table
        debug('Reading', fn)
        B_dr2 = fits_table(fn, columns=['brickname', 'ra1', 'ra2', 'dec1', 'dec2',
                                        'has_g', 'has_r', 'has_z'])
        return B_dr2

    from astrometry.libkd.spherematch import match_radec
    import numpy as np

    decals = _get_survey('decals-dr2')
    B = decals.get_bricks()
    C = decals.get_ccds_readonly()
    # CCD radius
    radius = np.hypot(2048, 4096) / 2. * 0.262 / 3600.
    # Brick radius
    radius += np.hypot(0.25, 0.25)/2.
    I,J,d = match_radec(B.ra, B.dec, C.ra, C.dec, radius * 1.05)
    for band in 'grz':
        has = np.zeros(len(B), bool)
        K = (C.filter[J] == band)
        has[I[K]] = True
        B.set('has_%s' % band, has)
        debug(sum(has), 'bricks have coverage in', band)

    keep = np.zeros(len(B), bool)
    keep[I] = True
    B.cut(keep)
    B_dr2 = B
    B_dr2.writeto(fn)
    debug('Wrote', fn)
    return B_dr2



B_mobo_dr3 = None
def _get_mobo_dr3_bricks():
    global B_mobo_dr3
    if B_mobo_dr3 is not None:
        return B_mobo_dr3

    fn = os.path.join(settings.DATA_DIR, 'mobo-dr3', 'mobo-bricks-in-dr3.fits')
    if os.path.exists(fn):
        from astrometry.util.fits import fits_table
        debug('Reading', fn)
        B_mobo_dr3 = fits_table(fn, columns=['brickname', 'ra1', 'ra2', 'dec1', 'dec2',
                                        'has_g', 'has_r', 'has_z'])
        return B_mobo_dr3

    from astrometry.libkd.spherematch import match_radec
    import numpy as np

    decals = _get_survey('mobo-dr3')
    B = decals.get_bricks()
    C = decals.get_ccds_readonly()
    # CCD radius
    radius = np.hypot(2048, 4096) / 2. * 0.262 / 3600.
    # Brick radius
    radius += np.hypot(0.25, 0.25)/2.
    I,J,d = match_radec(B.ra, B.dec, C.ra, C.dec, radius * 1.05)
    for band in 'grz':
        has = np.zeros(len(B), bool)
        K = (C.filter[J] == band)
        has[I[K]] = True
        B.set('has_%s' % band, has)
        debug(sum(has), 'bricks have coverage in', band)

    keep = np.zeros(len(B), bool)
    keep[I] = True
    B.cut(keep)
    B_mobo_dr3 = B
    B_mobo_dr3.writeto('/tmp/mobo-bricks-in-dr3.fits')
    #B_dr3.writeto(fn)
    #debug('Wrote', fn)
    return B_mobo_dr3

def map_mobo_dr3_model(req, ver, zoom, x, y, **kwargs):
    kwargs.update(model=True, model_gz=True, add_gz=True)
    return map_mobo_dr3(req, ver, zoom, x, y, **kwargs)

def map_mobo_dr3_resid(req, ver, zoom, x, y, **kwargs):
    kwargs.update(resid=True, model_gz=True)
    return map_mobo_dr3(req, ver, zoom, x, y, **kwargs)

def map_mobo_dr3(req, ver, zoom, x, y, savecache=None,
                    model=False, resid=False, nexp=False,
                    **kwargs):
    if savecache is None:
        savecache = settings.SAVE_CACHE

    B_dr3 = _get_mobo_dr3_bricks()
    survey = _get_survey('mobo-dr3')
    
    imagetag = 'image'
    tag = 'mobo-dr3'
    imagedir = 'mobo-dr3'

    if model:
        imagetag = 'model'
        tag = 'mobo-dr3-model'
    if resid:
        imagetag = 'resid'
        kwargs.update(modeldir = 'mobo-dr3-model')
        tag = 'mobo-dr3-resid'

    rgb = rgbkwargs
    return map_coadd_bands(req, ver, zoom, x, y, 'grz', tag, imagedir,
                           imagetag=imagetag,
                           rgbkwargs=rgb,
                           bricks=B_dr3,
                           decals=survey,
                           savecache=savecache, rgbfunc=dr2_rgb, **kwargs)


B_dr3 = None
def _get_dr3_bricks():
    global B_dr3
    if B_dr3 is not None:
        return B_dr3

    fn = os.path.join(settings.DATA_DIR, 'decals-dr3', 'decals-bricks-in-dr3.fits')
    if os.path.exists(fn):
        from astrometry.util.fits import fits_table
        debug('Reading', fn)
        B_dr3 = fits_table(fn, columns=['brickname', 'ra1', 'ra2', 'dec1', 'dec2',
                                        'has_g', 'has_r', 'has_z'])
        return B_dr3

    from astrometry.libkd.spherematch import match_radec
    import numpy as np

    decals = _get_survey('decals-dr3')
    B = decals.get_bricks()
    C = decals.get_ccds_readonly()
    # CCD radius
    radius = np.hypot(2048, 4096) / 2. * 0.262 / 3600.
    # Brick radius
    radius += np.hypot(0.25, 0.25)/2.
    I,J,d = match_radec(B.ra, B.dec, C.ra, C.dec, radius * 1.05)
    for band in 'grz':
        has = np.zeros(len(B), bool)
        K = (C.filter[J] == band)
        has[I[K]] = True
        B.set('has_%s' % band, has)
        debug(sum(has), 'bricks have coverage in', band)

    keep = np.zeros(len(B), bool)
    keep[I] = True
    B.cut(keep)
    B_dr3 = B
    B_dr3.writeto('/tmp/decals-bricks-in-dr3.fits')
    #B_dr3.writeto(fn)
    #debug('Wrote', fn)
    return B_dr3

def map_decals_dr3_model(req, ver, zoom, x, y, **kwargs):
    kwargs.update(model=True, model_gz=True, add_gz=True)
    return map_decals_dr3(req, ver, zoom, x, y, **kwargs)

def map_decals_dr3_resid(req, ver, zoom, x, y, **kwargs):
    kwargs.update(resid=True, model_gz=True)
    return map_decals_dr3(req, ver, zoom, x, y, **kwargs)

def map_decals_dr3(req, ver, zoom, x, y, savecache=None,
                    model=False, resid=False, nexp=False,
                    **kwargs):
    if savecache is None:
        savecache = settings.SAVE_CACHE

    B_dr3 = _get_dr3_bricks()
    decals = _get_survey('decals-dr3')
    
    imagetag = 'image'
    tag = 'decals-dr3'
    imagedir = 'decals-dr3'

    if model:
        imagetag = 'model'
        tag = 'decals-dr3-model'
    if resid:
        imagetag = 'resid'
        kwargs.update(modeldir = 'decals-dr3-model')
        tag = 'decals-dr3-resid'

    rgb = rgbkwargs
    return map_coadd_bands(req, ver, zoom, x, y, 'grz', tag, imagedir,
                           imagetag=imagetag,
                           rgbkwargs=rgb,
                           bricks=B_dr3,
                           decals=decals,
                           savecache=savecache, rgbfunc=dr2_rgb, **kwargs)


def dr2_rgb(rimgs, bands, **ignored):
    return sdss_rgb(rimgs, bands, scales=dict(g=6.0, r=3.4, z=2.2), m=0.03)

def map_decals_dr2_model(req, ver, zoom, x, y, **kwargs):
    kwargs.update(model=True, model_gz=True, add_gz=True)
    return map_decals_dr2(req, ver, zoom, x, y, **kwargs)

def map_decals_dr2_resid(req, ver, zoom, x, y, **kwargs):
    kwargs.update(resid=True, model_gz=True)
    return map_decals_dr2(req, ver, zoom, x, y, **kwargs)

def map_decals_dr2(req, ver, zoom, x, y, savecache=None,
                    model=False, resid=False, nexp=False,
                    **kwargs):
    if savecache is None:
        savecache = settings.SAVE_CACHE

    B_dr2 = _get_dr2_bricks()
    decals = _get_survey('decals-dr2')

    imagetag = 'image'
    tag = 'decals-dr2'
    imagedir = 'decals-dr2'

    if model:
        imagetag = 'model'
        tag = 'decals-dr2-model'
    if resid:
        imagetag = 'resid'
        kwargs.update(modeldir = 'decals-dr2-model')
        tag = 'decals-dr2-resid'

    rgb = rgbkwargs
    return map_coadd_bands(req, ver, zoom, x, y, 'grz', tag, imagedir,
                           decals=decals,
                           imagetag=imagetag,
                           rgbkwargs=rgb,
                           bricks=B_dr2,
                           savecache=savecache, rgbfunc=dr2_rgb, **kwargs)


B_dr1j = None

def map_decals_dr1j(req, ver, zoom, x, y, savecache=None,
                    model=False, resid=False, nexp=False,
                    **kwargs):
    if savecache is None:
        savecache = settings.SAVE_CACHE
    global B_dr1j
    if B_dr1j is None:
        from astrometry.util.fits import fits_table
        import numpy as np

        B_dr1j = fits_table(os.path.join(settings.DATA_DIR, 'decals-dr1',
                                         'decals-bricks-exist.fits'),
                            columns=['has_image_g', 'has_image_r', 'has_image_z',
                                     'brickname', 'ra1','ra2','dec1','dec2'])
        B_dr1j.cut(reduce(np.logical_or, [B_dr1j.has_image_g,
                                          B_dr1j.has_image_r,
                                          B_dr1j.has_image_z]))
        B_dr1j.rename('has_image_g', 'has_g')
        B_dr1j.rename('has_image_g', 'has_g')
        B_dr1j.rename('has_image_g', 'has_g')
        debug(len(B_dr1j), 'DR1 bricks with images')

    imagetag = 'image'
    tag = 'decals-dr1j'
    imagedir = 'decals-dr1j'
    rgb = rgbkwargs
    if model:
        imagetag = 'model'
        tag = 'decals-model-dr1j'
        scaledir = 'decals-dr1j'
        kwargs.update(model_gz=False, add_gz=True, scaledir=scaledir)
    if resid:
        imagetag = 'resid'
        kwargs.update(modeldir = 'decals-dr1j-model',
                      model_gz=True)
        tag = 'decals-resid-dr1j'
    if nexp:
        imagetag = 'nexp'
        tag = 'decals-nexp-dr1j'
        rgb = rgbkwargs_nexp

    return map_coadd_bands(req, ver, zoom, x, y, 'grz', tag, imagedir,
                           imagetag=imagetag,
                           rgbkwargs=rgb,
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

def map_unwise_w1w2_neo1(*args, **kwargs):
    kwargs.update(tag='unwise-neo1', unwise_dir=settings.UNWISE_NEO1_DIR)
    return map_unwise(*args, **kwargs)

def map_unwise(req, ver, zoom, x, y, savecache = False, ignoreCached=False,
               get_images=False,
               bands=[1,2], tag='unwise-w1w2',
               unwise_dir=settings.UNWISE_DIR,
               **kwargs):
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
    debug('Tilefn:', tilefn)
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
        UNW = fits_table(os.path.join(settings.UNWISE_DIR, 'allsky-atlas.fits'),
                         columns=['ra','dec','coadd_id'])
        UNW_tree = tree_build_radec(UNW.ra, UNW.dec)

    # unWISE tile size
    radius = 1.01 * np.sqrt(2.)/2. * 2.75 * 2048 / 3600.

    # leaflet tile size
    ok,ra,dec = wcs.pixelxy2radec(W/2., H/2.)
    ok,r0,d0 = wcs.pixelxy2radec(1, 1)
    ok,r1,d1 = wcs.pixelxy2radec(W, H)
    radius = radius + max(degrees_between(ra,dec, r0,d0), degrees_between(ra,dec, r1,d1))

    J = tree_search_radec(UNW_tree, ra, dec, radius)
    debug(len(J), 'unWISE tiles nearby')
    
    ww = [1, W*0.25, W*0.5, W*0.75, W]
    hh = [1, H*0.25, H*0.5, H*0.75, H]

    ok,r,d = wcs.pixelxy2radec(
        [1]*len(hh) + ww          + [W]*len(hh) +        list(reversed(ww)),
        hh          + [1]*len(ww) + list(reversed(hh)) + [H]*len(ww))
    scaled = 0
    scalepat = None
    scaledir = tag

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
        debug('Zoom:', zoom, 'x,y', x,y, 'Tile pixel scale:', scale, 'Scale step:', scaled)
        scaled = np.clip(scaled, 1, 7)
        
        scalepat = os.path.join(basedir, 'scaled', scaledir,
                                '%(scale)i%(band)s', '%(tilename).3s', 'unwise-%(tilename)s-%(band)s.fits')

    basepat = os.path.join(unwise_dir, '%(tilename).3s', '%(tilename)s', 'unwise-%(tilename)s-%(band)s-img-u.fits')

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

        debug('Tile', tile, 'fns', fns)
        bwcs = Tan(fns[0], 0)
        ok,xx,yy = bwcs.radec2pixelxy(r, d)
        #print('ok:', np.unique(ok))
        if not np.all(ok):
            debug('Skipping tile', tile)
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

    trymakedirs(tilefn)
    save_jpeg(tilefn, rgb)
    debug('Wrote', tilefn)

    return send_file(tilefn, 'image/jpeg', unlink=(not savecache))

sfd = None
halpha = None

def map_halpha(req, ver, zoom, x, y, savecache=False):
    global halpha

    from tractor.sfd import SFDMap
    if halpha is None:
        halpha = SFDMap(ngp_filename=os.path.join(settings.HALPHA_DIR,'Halpha_4096_ngp.fits'), sgp_filename=os.path.join(settings.HALPHA_DIR,'Halpha_4096_sgp.fits'))

    # Doug says: np.log10(halpha + 5) stretched to 0.5 to 2.5

    def stretch(x):
        import numpy as np
        return np.log10(x + 5)

    return map_zea(req, ver, zoom, x, y, ZEAmap=halpha, tag='halpha', savecache=savecache, vmin=0.5, vmax=2.5, stretch=stretch)


def map_sfd(req, ver, zoom, x, y, savecache=False):
    global sfd

    from tractor.sfd import SFDMap
    if sfd is None:
        sfd = SFDMap(dustdir=settings.DUST_DIR)

    return map_zea(req, ver, zoom, x, y, ZEAmap=sfd, tag='sfd', savecache=savecache)


def map_zea(req, ver, zoom, x, y, ZEAmap=None, tag=None, savecache=False, vmin=0, vmax=0.5, stretch=None):

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

    if os.path.exists(tilefn):
        # debug('Cached:', tilefn)
        return send_file(tilefn, 'image/jpeg', expires=oneyear,
                         modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'))

    import numpy as np
    
    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)

    xx,yy = np.meshgrid(np.arange(wcs.get_width()), np.arange(wcs.get_height()))
    ok,rr,dd = wcs.pixelxy2radec(xx.ravel(), yy.ravel())

    # Calling ebv function for historical reasons, works for any ZEA map.
    val = ZEAmap.ebv(rr, dd) 
    val = val.reshape(xx.shape)

    trymakedirs(tilefn)

    if not savecache:
        import tempfile
        f,tilefn = tempfile.mkstemp(suffix='.jpg')
        os.close(f)

    import pylab as plt

    # no jpeg output support in matplotlib in some installations...
    if True:
        if stretch is not None:
            val = stretch(val)
        save_jpeg(tilefn, val, vmin=vmin, vmax=vmax, cmap='hot')
        debug('Wrote', tilefn)

    return send_file(tilefn, 'image/jpeg', unlink=(not savecache))

surveys = {}
def _get_survey(name=None):
    global surveys
    if name in surveys:
        return surveys[name]

    debug('Creating LegacySurveyData() object for "%s"' % name)
    debug('cwd:', os.getcwd())
    
    from decals import settings
    basedir = settings.DATA_DIR
    from legacypipe.common import LegacySurveyData

    if name in ['decals-dr3', 'mobo-dr3']:
        dirnm = os.path.join(basedir, name)
        d = LegacySurveyData(survey_dir=dirnm)
        # HACK -- drop unnecessary columns.
        B = d.get_bricks_readonly()
        for k in ['brickid', 'brickq', 'brickrow', 'brickcol']:
            B.delete_column(k)
        # HACK -- plug in a cut version of the CCDs table, if it exists
        cutfn = os.path.join(dirnm, 'ccds-cut.fits')
        if os.path.exists(cutfn):
            from astrometry.util.fits import fits_table
            C = fits_table(cutfn)
            d.ccds = C
        else:
            C = d.get_ccds_readonly()
            # HACK -- cut to photometric & not-blacklisted CCDs.
            C.cut(d.photometric_ccds(C))
            debug('HACK -- cut to', len(C), 'photometric CCDs')
            C.cut(d.apply_blacklist(C))
            debug('HACK -- cut to', len(C), 'not-blacklisted CCDs')
            for k in ['date_obs', 'ut', 'airmass',
                      'zpt', 'avsky', 'arawgain', 'ccdnum', 'ccdzpta',
                      'ccdzptb', 'ccdphoff', 'ccdphrms', 'ccdskyrms',
                      'ccdtransp', 'ccdnstar', 'ccdnmatch', 'ccdnmatcha',
                      'ccdnmatchb', 'ccdmdncol', 'expid']:
                if k in C.columns():
                    C.delete_column(k)
            C.writeto('/tmp/cut-ccds-%s.fits' % name)

        surveys[name] = d
        return d
    
    if name == 'decals-dr2':
        dirnm = os.path.join(basedir, 'decals-dr2')
        d = LegacySurveyData(survey_dir=dirnm, version='dr2')

        # HACK -- drop unnecessary columns.
        B = d.get_bricks_readonly()
        for k in ['brickid', 'brickq', 'brickrow', 'brickcol']:
            B.delete_column(k)

        # HACK -- plug in a cut version of the CCDs table, if it exists
        cutfn = os.path.join(dirnm, 'decals-ccds-cut.fits')
        if os.path.exists(cutfn):
            from astrometry.util.fits import fits_table
            C = fits_table(cutfn)
            d.ccds = C
        else:
            C = d.get_ccds_readonly()
            # HACK -- cut to photometric & not-blacklisted CCDs.
            C.cut(d.photometric_ccds(C))
            debug('HACK -- cut to', len(C), 'photometric CCDs')
            C.cut(d.apply_blacklist(C))
            debug('HACK -- cut to', len(C), 'not-blacklisted CCDs')
            for k in ['date_obs', 'ut', 'airmass',
                      'zpt', 'avsky', 'arawgain', 'ccdnum', 'ccdzpta',
                      'ccdzptb', 'ccdphoff', 'ccdphrms', 'ccdskyrms',
                      'ccdtransp', 'ccdnstar', 'ccdnmatch', 'ccdnmatcha',
                      'ccdnmatchb', 'ccdmdncol', 'expid']:
                C.delete_column(k)
            # C.writeto(cutfn)

        surveys[name] = d
        return d

    if name is None:
        name = 'decals-dr1'
    if name in surveys:
        return surveys[name]

    assert(name == 'decals-dr1')

    dirnm = os.path.join(basedir, 'decals-dr1')
    d = LegacySurveyData(survey_dir=dirnm, version='dr1')
    surveys[name] = d

    return d

def brick_list(req):
    import json

    north = float(req.GET['dechi'])
    south = float(req.GET['declo'])
    east  = float(req.GET['ralo'])
    west  = float(req.GET['rahi'])

    if east < 0:
        east += 360.
        west += 360.

    B = None

    name = req.GET.get('id', None)
    name = layer_name_map(name)
    if name == 'decals-dr1k':
        from astrometry.util.fits import fits_table
        B = fits_table(os.path.join(settings.DATA_DIR, 'decals-dr1k',
                                    'decals-bricks.fits'))
    elif name == 'decals-dr1n':
        from astrometry.util.fits import fits_table
        B = fits_table(os.path.join(settings.DATA_DIR,
                                    'decals-bricks.fits'))

    D = _get_survey(name=name)
    if B is None:
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
                           poly=[[b.dec1-mdec, ra2long_B(b.ra1-mra)],
                                 [b.dec2+mdec, ra2long_B(b.ra1-mra)],
                                 [b.dec2+mdec, ra2long_B(b.ra2+mra)],
                                 [b.dec1-mdec, ra2long_B(b.ra2+mra)],
                                 ]))

    return HttpResponse(json.dumps(dict(polys=bricks)),
                        content_type='application/json')

def _objects_touching_box(kdtree, north, south, east, west,
                          Nmax=None, radius=0.):
    import numpy as np
    from astrometry.libkd.spherematch import tree_search_radec
    from astrometry.util.starutil_numpy import degrees_between

    dec = (north + south) / 2.
    c = (np.cos(np.deg2rad(east)) + np.cos(np.deg2rad(west))) / 2.
    s = (np.sin(np.deg2rad(east)) + np.sin(np.deg2rad(west))) / 2.
    ra  = np.rad2deg(np.arctan2(s, c))

    # RA,Dec box size
    radius = radius + degrees_between(east, north, west, south) / 2.

    J = tree_search_radec(kdtree, ra, dec, radius)
    if Nmax is not None:
        # limit result size
        J = J[:Nmax]
    return J

ccd_cache = {}

def _ccds_touching_box(north, south, east, west, Nmax=None, name=None):
    from astrometry.libkd.spherematch import tree_build_radec
    import numpy as np
    global ccd_cache

    if not name in ccd_cache:
        debug('Finding CCDs for name=', name)

        decals = _get_survey(name=name)
        CCDs = decals.get_ccds_readonly()

        # fn = None
        # CCDs = None
        # if name == 'decals-dr1j':
        #     fn = os.path.join(settings.DATA_DIR, 'decals-dr1', 'decals-ccds.fits')
        # elif name == 'decals-dr1k':
        #     fn = os.path.join(settings.DATA_DIR, 'decals-dr1k',
        #                       'decals-ccds.fits')
        # elif name == 'decals-dr1n':
        #     fn = os.path.join(settings.DATA_DIR, 'decals-ccds-dr1n.fits')
        # elif name == 'decals-dr2':
        #     fn = os.path.join(settings.DATA_DIR, 'decals-dr2',
        #                       'decals-ccds.fits')
        # else:
        #     D = _get_survey(name=name)
        #     if hasattr(D, 'get_ccds_readonly'):
        #         CCDs = D.get_ccds_readonly()
        #     else:
        #         CCDs = D.get_ccds()
        # 
        # if CCDs is None:
        #     from astrometry.util.fits import fits_table
        #     CCDs = fits_table(fn)

        if name == 'decals-dr2':
            CCDs.extname = CCDs.ccdname
            CCDs.cpimage = CCDs.image_filename
            CCDs.cpimage_hdu = CCDs.image_hdu

        tree = tree_build_radec(CCDs.ra, CCDs.dec)
        ccd_cache[name] = (CCDs, tree)
    else:
        CCDs,tree = ccd_cache[name]

    # image size
    radius = np.hypot(2048, 4096) * 0.262/3600. / 2.

    J = _objects_touching_box(tree, north, south, east, west, Nmax=Nmax,
                              radius=radius)
    return CCDs[J]

def ccd_list(req):
    import json
    from astrometry.util.util import Tan
    import numpy as np

    north = float(req.GET['dechi'])
    south = float(req.GET['declo'])
    east  = float(req.GET['ralo'])
    west  = float(req.GET['rahi'])

    name = req.GET.get('id', None)
    print('Name:', name)
    name = layer_name_map(name)
    print('Mapped name:', name)
    
    CCDS = _ccds_touching_box(north, south, east, west, Nmax=10000, name=name)

    ccdname = lambda c: '%s %i-%s-%s' % (c.camera, c.expnum, c.extname.strip(), c.filter)

    if name in ['decals-dr2', 'decals-dr3', 'mobo-dr3']:
        ccdname = lambda c: '%s %i-%s-%s' % (c.camera, c.expnum, c.ccdname.strip(), c.filter)
        #decals = _get_survey(name)
        #CCDS.cut(decals.photometric_ccds(CCDS))

    CCDS.cut(np.lexsort((CCDS.expnum, CCDS.filter)))

    ccds = []
    for c in CCDS:
        wcs = Tan(*[float(x) for x in [
            c.crval1, c.crval2, c.crpix1, c.crpix2, c.cd1_1, c.cd1_2,
            c.cd2_1, c.cd2_2, c.width, c.height]])
        x = np.array([1, 1, c.width, c.width])
        y = np.array([1, c.height, c.height, 1])
        r,d = wcs.pixelxy2radec(x, y)
        ccmap = dict(g='#00ff00', r='#ff0000', z='#cc00cc')
        ccds.append(dict(name=ccdname(c),
                         poly=zip(d, ra2long(r)),
                         color=ccmap[c.filter]))

    return HttpResponse(json.dumps(dict(polys=ccds)),
                        content_type='application/json')

def get_exposure_table(name):
    from astrometry.util.fits import fits_table
    if name == 'decals-dr2':
        T = fits_table(os.path.join(settings.DATA_DIR, 'decals-dr2',
                                    'decals-exposures.fits'))
    elif name == 'decals-dr3':
        '''
        T1=fits_table('survey-ccds-extra.fits.gz')
        T2=fits_table('survey-ccds-decals.fits.gz')
        T3=fits_table('survey-ccds-nondecals.fits.gz')
        T = merge_tables([T1,T2,T3])
        e,I = np.unique(T.expnum, return_index=True)
        E = T[I]
        E.ra = E.ra_bore
        E.dec = E.dec_bore
        E.writeto('dr3-exposures.fits', columns=['ra', 'dec', 'expnum', 'seeing', 'propid',
        'fwhm', 'zpt', 'airmass', 'exptime', 'date_obs', 'ut', 'filter', 'mjd_obs', 'image_filename'])
        '''
        T = fits_table(os.path.join(settings.DATA_DIR, 'decals-dr3',
                                    'decals-exposures.fits'))
    else:
        T = fits_table(os.path.join(settings.DATA_DIR, 'decals-exposures-dr1.fits'))
    return T

exposure_cache = {}

def exposure_list(req):
    import json
    from astrometry.util.fits import fits_table
    from decals import settings
    import numpy as np

    global exposure_cache

    north = float(req.GET['dechi'])
    south = float(req.GET['declo'])
    east  = float(req.GET['ralo'])
    west  = float(req.GET['rahi'])
    name = req.GET.get('id', None)
    print('Name:', name)
    name = layer_name_map(name)
    print('Mapped name:', name)

    if not name in exposure_cache:
        from astrometry.libkd.spherematch import tree_build_radec
        T = get_exposure_table(name)
        tree = tree_build_radec(T.ra, T.dec)
        exposure_cache[name] = (T,tree)
    else:
        T,tree = exposure_cache[name]

    radius = 1.0

    I = _objects_touching_box(tree, north, south, east, west,radius=radius)
    T = T[I]
    T.cut(np.lexsort((T.expnum, T.filter)))

    exps = []
    for t in T:
        cmap = dict(g='#00ff00', r='#ff0000', z='#cc00cc')
        exps.append(dict(name='%i %s' % (t.expnum, t.filter),
                         ra=t.ra, dec=t.dec, radius=radius,
                         color=cmap[t.filter]))

    return HttpResponse(json.dumps(dict(objs=exps)),
                        content_type='application/json')

plate_cache = {}

def sdss_plate_list(req):
    import json
    from astrometry.util.fits import fits_table
    from decals import settings
    import numpy as np

    global plate_cache

    north = float(req.GET['dechi'])
    south = float(req.GET['declo'])
    east  = float(req.GET['ralo'])
    west  = float(req.GET['rahi'])
    name = 'sdss'

    if not name in plate_cache:
        from astrometry.libkd.spherematch import tree_build_radec
        T = fits_table(os.path.join(settings.DATA_DIR, 'sdss',
                                    'plates-dr12.fits'))
        T.rename('racen', 'ra')
        T.rename('deccen', 'dec')
        # Cut to the first entry for each PLATE
        nil,I = np.unique(T.plate, return_index=True)
        T.cut(I)
        tree = tree_build_radec(T.ra, T.dec)
        plate_cache[name] = (T,tree)
    else:
        T,tree = plate_cache[name]

    radius = 1.5

    I = _objects_touching_box(tree, north, south, east, west,radius=radius)
    T = T[I]

    plates = []
    for t in T:
        plates.append(dict(name='plate%i' % t.plate,
                           ra=t.ra, dec=t.dec, radius=radius,
                           color='#ffffff'))

    return HttpResponse(json.dumps(dict(objs=plates)),
                        content_type='application/json')

    
def ccd_detail(req, name, ccd):
    import numpy as np
    #ccd = req.GET['ccd']
    words = ccd.split('-')
    assert(len(words) == 3)
    expnum = int(words[0], 10)
    assert(words[1][0] in 'NS')
    ns = words[1][0]
    chipnum = int(words[1][1:], 10)
    extname = '%s%i' % (ns,chipnum)

    decals = _get_survey(name=name)
    C = decals.find_ccds(expnum=expnum, ccdname=extname)
    assert(len(C) == 1)
    c = C[0]

    if name == 'decals-dr2':
        about = lambda ccd, c: 'CCD %s, image %s, hdu %i; exptime %.1f sec, seeing %.1f arcsec, fwhm %.1f pix' % (ccd, c.image_filename, c.image_hdu, c.exptime, c.seeing, c.fwhm)
    else:
        about = lambda ccd, c: 'CCD %s, image %s, hdu %i; exptime %.1f sec, seeing %.1f arcsec' % (ccd, c.cpimage, c.cpimage_hdu, c.exptime, c.fwhm*0.262)

    return HttpResponse(about(ccd, c))


def exposure_detail(req, name, exp):
    import numpy as np
    expnum = exp.split('-')[0]
    expnum = int(expnum)
    T = get_exposure_table(name)
    T.cut(T.expnum == expnum)
    t = T[0]
    pixscale = 0.262
    return HttpResponse('Exposure %i, %s band, %.1f sec exposure time, seeing %.2f arcsec, file %s' %
                        (t.expnum, t.filter, t.exptime, t.fwhm * pixscale,
                         t.image_filename))

def nil(req):
    pass

def brick_detail(req, brickname):
    #return HttpResponse('Brick ' + brickname)
    import numpy as np
    bricks = _get_dr2_bricks()
    I = np.flatnonzero(brickname == bricks.brickname)
    assert(len(I) == 1)
    brick = bricks[I[0]]

    return HttpResponse('\n'.join([
                '<html><head><title>DECaLS DR2 data for brick %s</title></head>' % (brickname),
                '<body>',
                '<h1>DECaLS DR2 data for brick %s:</h1>' % (brickname),
                '<p>Brick bounds: RA [%.4f to %.4f], Dec [%.4f to %.4f]</p>' % (brick.ra1, brick.ra2, brick.dec1, brick.dec2),
                '<ul>',
                '<li><a href="http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr2/coadd/%s/%s/decals-%s-image.jpg">JPEG image</a></li>' % (brickname[:3], brickname, brickname),
                '<li><a href="http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr2/coadd/%s/%s/">Coadded images</a></li>' % (brickname[:3], brickname),
                '<li><a href="http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr2/tractor/%s/tractor-%s.fits">Catalog (FITS table)</a></li>' % (brickname[:3], brickname),
                '</ul>',
                '</body></html>']))

def cat_spec(req, ver):
    import json
    tag = 'spec'
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])

    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    from astrometry.util.fits import fits_table, merge_tables
    import numpy as np
    from decals import settings

    TT = []
    T = fits_table(os.path.join(settings.DATA_DIR, 'specObj-dr12-trim-2.fits'))
    debug(len(T), 'spectra')
    if ralo > rahi:
        # RA wrap
        T.cut(np.logical_or(T.ra > ralo, T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    else:
        T.cut((T.ra > ralo) * (T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    debug(len(T), 'in cut')

    rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
    names = [t.strip() for t in T.label]
    mjd   = [int(x) for x in T.mjd]
    fiber = [int(x) for x in T.fiberid]
    plate = [int(x) for x in T.plate]

    return HttpResponse(json.dumps(dict(rd=rd, name=names, mjd=mjd, fiber=fiber, plate=plate)),
                        content_type='application/json')


def cat_spec_deep2(req, ver):
    import json
    tag = 'spec-deep2'
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])
    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    from astrometry.util.fits import fits_table, merge_tables
    import numpy as np
    from decals import settings

    TT = []
    T = fits_table(os.path.join(settings.DATA_DIR, 'deep2-zcat-dr4-uniq.fits'))
    debug(len(T), 'spectra')
    if ralo > rahi:
        # RA wrap
        T.cut(np.logical_or(T.ra > ralo, T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    else:
        T.cut((T.ra > ralo) * (T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    debug(len(T), 'in cut')

    rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
    names = []

    classes = T.get('class')
    subclasses = T.subclass
    zbests = T.zbest
    zq = T.zquality
    for i in range(len(T)):
        clazz = classes[i]
        clazz = clazz[0] + clazz[1:].lower()

        #if zq[i] >= 3:
        nm = clazz
        sc = subclasses[i].strip()
        if sc != 'NONE':
            nm += ' ' + sc
        if not (zq[i] == -1 and clazz.strip() == 'Star'):
            nm += ' z=%.2f, q=%i' % (zbests[i], zq[i])
        names.append(nm)

    return HttpResponse(json.dumps(dict(rd=rd, name=names)),
                        content_type='application/json')

def cat_bright(req, ver):
    return cat(req, ver, 'bright',
               os.path.join(settings.DATA_DIR, 'bright.fits'))

def cat_tycho2(req, ver):
    return cat(req, ver, 'tycho2',
               os.path.join(settings.DATA_DIR, 'tycho2.fits'))

def cat_gals(req, ver):
    return cat(req, ver, 'ngc',
               os.path.join(settings.DATA_DIR,'galaxy-cats.fits'))

def cat(req, ver, tag, fn):
    import json
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])

    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    from astrometry.util.fits import fits_table
    import numpy as np
    from decals import settings

    TT = []
    T = fits_table(fn)
    debug(len(T), 'catalog objects')
    if ralo > rahi:
        # RA wrap
        T.cut(np.logical_or(T.ra > ralo, T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    else:
        T.cut((T.ra > ralo) * (T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    debug(len(T), 'in cut')

    rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
    names = [t.strip() for t in T.name]
    rtn = dict(rd=rd, name=names)
    # bright stars
    if 'alt_name' in T.columns():
        rtn.update(altname = [t.strip() for t in T.alt_name])
    if 'radius' in T.columns():
        rtn.update(radiusArcsec=list(float(f) for f in T.radius * 3600.))
        
    return HttpResponse(json.dumps(rtn), content_type='application/json')

def cat_decals_dr1j(req, ver, zoom, x, y, tag='decals-dr1j'):
    return cat_decals(req, ver, zoom, x, y, tag=tag, docache=False)

def cat_decals_dr2(req, ver, zoom, x, y, tag='decals-dr2'):
    return cat_decals(req, ver, zoom, x, y, tag=tag, docache=False)

def cat_decals_dr3(req, ver, zoom, x, y, tag='decals-dr3'):
    return cat_decals(req, ver, zoom, x, y, tag=tag, docache=False)

def cat_decals(req, ver, zoom, x, y, tag='decals', docache=True):
    import json
    zoom = int(zoom)
    if zoom < 12:
        return HttpResponse(json.dumps(dict(rd=[])),
                            content_type='application/json')

    from astrometry.util.fits import fits_table, merge_tables
    import numpy as np

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
            return send_file(cachefn, 'application/json',
                             modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'),
                             expires=oneyear)
    else:
        import tempfile
        f,cachefn = tempfile.mkstemp(suffix='.json')
        os.close(f)

    cat,hdr = _get_decals_cat(wcs, tag=tag)

    if cat is None:
        rd = []
        types = []
        fluxes = []
        bricknames = []
        objids = []
        nobs = []
    else:
        rd = zip(cat.ra, cat.dec)
        types = list([t[0] for t in cat.get('type')])
        fluxes = [dict(g=float(g), r=float(r), z=float(z))
                  for g,r,z in zip(cat.decam_flux[:,1], cat.decam_flux[:,2],
                                   cat.decam_flux[:,4])]
        nobs = [dict(g=int(g), r=int(r), z=int(z))
                for g,r,z in zip(cat.decam_nobs[:,1], cat.decam_nobs[:,2],
                                 cat.decam_nobs[:,4])]
        bricknames = list(cat.brickname)
        objids = [int(x) for x in cat.objid]

    json = json.dumps(dict(rd=rd, sourcetype=types, fluxes=fluxes, nobs=nobs,
                                 bricknames=bricknames, objids=objids))
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
    X = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                            [1,H/2,H,H,H,H/2,1,1])
    r,d = X[-2:]
    catpat = os.path.join(basedir, 'cats', tag, '%(brickname).3s',
                          'tractor-%(brickname)s.fits')

    #debug('_get_decals_cat for tag=', tag)
    D = _get_survey(name=tag)
    B = D.get_bricks_readonly()
    I = D.bricks_touching_radec_box(B, r.min(), r.max(), d.min(), d.max())
    #print(len(I), 'bricks touching RA,Dec box', r.min(),r.max(), d.min(),d.max())

    cat = []
    hdr = None
    for brickname in B.brickname[I]:
        fnargs = dict(brickname=brickname)
        #print('Filename args:', fnargs)
        catfn = catpat % fnargs
        if not os.path.exists(catfn):
            print('Does not exist:', catfn)
            continue
        debug('Reading catalog', catfn)
        T = fits_table(catfn)
        # FIXME -- all False
        # debug('brick_primary', np.unique(T.brick_primary))
        # T.cut(T.brick_primary)
        ok,xx,yy = wcs.radec2pixelxy(T.ra, T.dec)
        #debug('xx,yy', xx.min(), xx.max(), yy.min(), yy.max())
        T.cut((xx > 0) * (yy > 0) * (xx < W) * (yy < H))
        # debug('kept', len(T), 'from', catfn)
        cat.append(T)
        if hdr is None:
            hdr = T.get_header()
    if len(cat) == 0:
        cat = None
    else:
        cat = merge_tables(cat)

    return cat,hdr

def map_coadd_bands(req, ver, zoom, x, y, bands, tag, imagedir,
                    wcs=None,
                    imagetag='image2', rgbfunc=None, rgbkwargs={},
                    bricks=None,
                    savecache = True, forcecache = False,
                    return_if_not_found=False, model_gz=False,
                    modeldir=None, scaledir=None, get_images=False,
                    write_jpeg=False,
                    ignoreCached=False, add_gz=False, filename=None,
                    symlink_blank=False,
                    hack_jpeg=False,
                    drname=None, decals=None,
                    basepat=None,
                    nativescale=14, maxscale=8,
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
        return send_file(tilefn, 'image/jpeg', expires=oneyear,
                         modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'),
                         filename=filename)
    else:
        debug('Tile image does not exist:', tilefn)
    from astrometry.util.resample import resample_with_wcs, OverlapError
    from astrometry.util.util import Tan
    import numpy as np
    import fitsio

    if wcs is None:
        try:
            wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
        except RuntimeError as e:
            return HttpResponse(e.strerror)
    else:
        W = wcs.get_width()
        H = wcs.get_height()

    if basepat is None:
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
    if add_gz:
        basepat += '.gz'

    scaled = 0
    scalepat = None
    if scaledir is None:
        scaledir = imagedir
    if zoom < nativescale:
        scaled = (nativescale - zoom)
        scaled = np.clip(scaled, 1, maxscale)
        #debug('Scaled-down:', scaled)
        dirnm = os.path.join(basedir, 'scaled', scaledir)
        scalepat = os.path.join(dirnm, '%(scale)i%(band)s', '%(brickname).3s', imagetag + '-%(brickname)s-%(band)s.fits')

    if decals is None:
        D = _get_survey(name=drname)
    else:
        D = decals
    if bricks is None:
        B = D.get_bricks_readonly()
    else:
        B = bricks

    rlo,d = wcs.pixelxy2radec(W, H/2)[-2:]
    rhi,d = wcs.pixelxy2radec(1, H/2)[-2:]
    r,d1 = wcs.pixelxy2radec(W/2, 1)[-2:]
    r,d2 = wcs.pixelxy2radec(W/2, H)[-2:]

    dlo = min(d1, d2)
    dhi = max(d1, d2)
    I = D.bricks_touching_radec_box(B, rlo, rhi, dlo, dhi)
    debug(len(I), 'bricks touching zoom', zoom, 'x,y', x,y, 'RA', rlo,rhi, 'Dec', dlo,dhi)

    if len(I) == 0:
        if get_images:
            return None
        from django.http import HttpResponseRedirect
        if forcecache and symlink_blank:
            # create symlink to blank.jpg!
            trymakedirs(tilefn)
            src = os.path.join(settings.STATIC_ROOT, 'blank.jpg')
            if os.path.exists(tilefn):
                os.unlink(tilefn)
            os.symlink(src, tilefn)
            debug('Symlinked', tilefn, '->', src)
        return HttpResponseRedirect(settings.STATIC_URL + 'blank.jpg')

    r,d = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                            [1,H/2,H,H,H,H/2,1,1])[-2:]
    foundany = False
    rimgs = []
    for band in bands:
        rimg = np.zeros((H,W), np.float32)
        rn   = np.zeros((H,W), np.uint8)
        for i,brickname in zip(I, B.brickname[I]):
            has = getattr(B, 'has_%s' % band, None)
            if has is not None and not has[i]:
                # No coverage for band in this brick.
                debug('Brick', brickname, 'has no', band, 'band')
                continue

            fnargs = dict(band=band, brickname=brickname)

            if imagetag == 'resid':
                #basefn = basepat % fnargs

                basefn = D.find_file('image', brick=brickname, band=band)

                modbasefn = D.find_file('model', brick=brickname, band=band)
                #modbasefn = modbasepat % fnargs
                #modbasefn = modbasefn.replace('resid', 'model')
                #if model_gz:
                #    modbasefn += '.gz'

                if scalepat is None:
                    imscalepat = None
                    modscalepat = None
                else:
                    imscalepat = scalepat.replace('resid', 'image')
                    modscalepat = scalepat.replace('resid', 'model')
                imbasefn = basefn.replace('resid', 'image')
                debug('resid.  imscalepat, imbasefn', imscalepat, imbasefn)
                debug('resid.  modscalepat, modbasefn', modscalepat, modbasefn)
                imfn = get_scaled(imscalepat, fnargs, scaled, imbasefn)
                modfn = get_scaled(modscalepat, fnargs, scaled, modbasefn)
                debug('resid.  im', imfn, 'mod', modfn)
                fn = imfn

            else:
                basefn = D.find_file(imagetag, brick=brickname, band=band)
                fn = get_scaled(scalepat, fnargs, scaled, basefn)
            if fn is None:
                debug('not found: brick', brickname, 'band', band, 'with basefn', basefn)
                savecache = False
                continue
            if not os.path.exists(fn):
                debug('Does not exist:', fn)
                savecache = False
                continue
            try:
                bwcs = _read_tan_wcs(fn, 0)
            except:
                print('Failed to read WCS:', fn)
                savecache = False
                import traceback
                import sys
                traceback.print_exc(None, sys.stdout)
                continue

            foundany = True
            debug('Reading', fn)
            ok,xx,yy = bwcs.radec2pixelxy(r, d)
            xx = xx.astype(np.int)
            yy = yy.astype(np.int)
            imW,imH = int(bwcs.get_width()), int(bwcs.get_height())
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
                del f

                if imagetag == 'resid':
                    f = fitsio.FITS(modfn)[0]
                    mod = f[slc]
                    del f
                    img = img - mod
                
            except:
                print('Failed to read image and WCS:', fn)
                savecache = False
                import traceback
                import sys
                traceback.print_exc(None, sys.stdout)
                continue

            try:
                Yo,Xo,Yi,Xi,nil = resample_with_wcs(wcs, subwcs, [], 3)
            except OverlapError:
                debug('Resampling exception')
                continue
            rimg[Yo,Xo] += img[Yi,Xi]

            # try:
            #     Yo,Xo,Yi,Xi,[rim] = resample_with_wcs(wcs, subwcs, [img], 3)
            # except OverlapError:
            #     debug('Resampling exception')
            #     continue
            # rimg[Yo,Xo] += rim
            
            rn  [Yo,Xo] += 1
        rimg /= np.maximum(rn, 1)
        rimgs.append(rimg)

    if return_if_not_found and not savecache:
        return

    if get_images and not write_jpeg:
        return rimgs

    if rgbfunc is None:
        from legacypipe.common import get_rgb
        rgbfunc = get_rgb

    rgb = rgbfunc(rimgs, bands, **rgbkwargs)

    if forcecache:
        savecache = True

    if savecache:
        trymakedirs(tilefn)
    else:
        import tempfile
        f,tilefn = tempfile.mkstemp(suffix='.jpg')
        os.close(f)

    # no jpeg output support in matplotlib in some installations...
    if hack_jpeg:
        save_jpeg(tilefn, rgb)
        debug('Wrote', tilefn)
    else:
        import pylab as plt
        plt.imsave(tilefn, rgb)
        debug('Wrote', tilefn)

    if get_images:
        return rimgs

    return send_file(tilefn, 'image/jpeg', unlink=(not savecache),
                     filename=filename)



def cutouts(req):
    from astrometry.util.util import Tan
    from astrometry.util.starutil_numpy import degrees_between
    import numpy as np
    from legacypipe.common import wcs_for_brick

    ra = float(req.GET['ra'])
    dec = float(req.GET['dec'])
    name = req.GET.get('name', None)

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
    
    CCDs = _ccds_touching_box(north, south, east, west, name=name)

    debug(len(CCDs), 'CCDs')

    CCDs = CCDs[np.lexsort((CCDs.extname, CCDs.expnum, CCDs.filter))]

    decals = _get_survey(name)

    ccds = []
    for i in range(len(CCDs)):
        c = CCDs[i]
        try:
            c.cpimage = _get_image_filename(c)
            dim = decals.get_image_object(c)
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
        ccds.append((c, x, y))

    B = decals.get_bricks_readonly()
    I = np.flatnonzero((B.ra1  <= ra)  * (B.ra2  >= ra) *
                       (B.dec1 <= dec) * (B.dec2 >= dec))
    brick = B[I[0]]
    bwcs = wcs_for_brick(brick)
    ok,brickx,bricky = bwcs.radec2pixelxy(ra, dec)
    brick = brick.to_dict()
    
    from django.shortcuts import render
    from django.core.urlresolvers import reverse
    from decals import settings

    url = req.build_absolute_uri('/') + settings.ROOT_URL + '/cutout_panels/%i/%s/'
    # Deployment: http://{s}.DOMAIN/...
    url = url.replace('://www.', '://')
    url = url.replace('://', '://%s.')
    domains = settings.SUBDOMAINS

    ccdsx = []
    for i,(ccd,x,y) in enumerate(ccds):
        fn = ccd.cpimage.replace(settings.DATA_DIR + '/', '')
        theurl = url % (domains[i%len(domains)], int(ccd.expnum), ccd.extname.strip()) + '?x=%i&y=%i' % (x,y)
        if name is not None:
            theurl += '&name=' + name
        ccdsx.append(('CCD %s %i %s, %.1f sec (x,y = %i,%i)<br/><small>(%s [%i])</small>' %
                      (ccd.filter, ccd.expnum, ccd.extname, ccd.exptime, x, y, fn, ccd.cpimage_hdu), theurl))
    return render(req, 'cutouts.html',
                  dict(ra=ra, dec=dec, ccds=ccdsx, name=name,
                       brick=brick, brickx=brickx, bricky=bricky))

def cat_plot(req):
    import pylab as plt
    import numpy as np
    from astrometry.util.util import Tan
    from legacypipe.sdss import get_sdss_sources
    from decals import settings

    ra = float(req.GET['ra'])
    dec = float(req.GET['dec'])
    name = req.GET.get('name', None)

    ver = float(req.GET.get('ver',2))

    # half-size in DECam pixels
    size = 50
    W,H = size*2, size*2
    
    pixscale = 0.262 / 3600.
    wcs = Tan(*[float(x) for x in [
        ra, dec, size+0.5, size+0.5, -pixscale, 0., 0., pixscale, W, H]])

    M = 10
    margwcs = wcs.get_subimage(-M, -M, W+2*M, H+2*M)

    tag = name
    if tag is None:
        tag = 'decals-dr1j'
    tag = str(tag)
    cat,hdr = _get_decals_cat(margwcs, tag=tag)

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
                  SIMP=(0xff, 0xa5, 0),
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


def _get_ccd(expnum, ccdname, name=None):
    decals = _get_survey(name=name)
    expnum = int(expnum, 10)
    ccdname = str(ccdname).strip()
    CCDs = decals.find_ccds(expnum=expnum, ccdname=ccdname)
    assert(len(CCDs) == 1)
    ccd = CCDs[0]
    return ccd

def _get_image_filename(ccd):
    from decals import settings
    basedir = settings.DATA_DIR
    #fn = ccd.cpimage.strip()
    fn = ccd.image_filename.strip()
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

def cutout_panels(req, expnum=None, extname=None, name=None):
    import pylab as plt
    import numpy as np

    x = int(req.GET['x'], 10)
    y = int(req.GET['y'], 10)

    if name is None:
        name = req.GET.get('name', name)
    ccd = _get_ccd(expnum, extname, name=name)

    fn = _get_image_filename(ccd)
    if not os.path.exists(fn):
        return HttpResponse('no such image: ' + fn)

    wfn = fn.replace('ooi', 'oow')
    if not os.path.exists(wfn):
        return HttpResponse('no such image: ' + wfn)

    # half-size in DECam pixels -- must match cutouts():size
    size = 50
    img,slc,xstart,ystart = _get_image_slice(fn, ccd.image_hdu, x, y, size=size)

    from legacypipe.decam import DecamImage
    from legacypipe.desi_common import read_fits_catalog
    from tractor import Tractor

    ccd.cpimage = fn
    D = _get_survey(name=name)
    im = D.get_image_object(ccd)
    kwargs = {}

    if name == 'decals-dr2':
        kwargs.update(pixPsf=True, splinesky=True)
    else:
        kwargs.update(const2psf=True)
    tim = im.get_tractor_image(slc=slc, tiny=1, **kwargs)

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
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'

    class duck(object):
        pass
    
    # ver = 1
    # zoom,x,y = 2, 1, 1
    # req = duck()
    # req.META = dict()
    # map_unwise_w1w2(req, ver, zoom, x, y, savecache=True, ignoreCached=True)

    from tractor.brightness import NanoMaggies
    import fitsio
    import pylab as plt
    import numpy as np
    from astrometry.util.miscutils import estimate_mode
    
    # J,jhdr = fitsio.read('j0.fits', header=True)
    # H,hhdr = fitsio.read('h0.fits', header=True)
    # K,khdr = fitsio.read('k0.fits', header=True)
    J,jhdr = fitsio.read('j2.fits', header=True)
    H,hhdr = fitsio.read('h2.fits', header=True)
    K,khdr = fitsio.read('k2.fits', header=True)

    print('J', J.dtype, J.shape)

    # Convert all to nanomaggies
    J /= NanoMaggies.zeropointToScale(jhdr['MAGZP'])
    H /= NanoMaggies.zeropointToScale(hhdr['MAGZP'])
    K /= NanoMaggies.zeropointToScale(khdr['MAGZP'])

    # Hacky sky subtraction
    J -= np.median(J.ravel())
    H -= np.median(H.ravel())
    K -= np.median(K.ravel())

    mo = estimate_mode(J)
    print('J mode', mo)
    J -= mo
    mo = estimate_mode(H)
    print('H mode', mo)
    H -= mo
    mo = estimate_mode(K)
    print('K mode', mo)
    K -= mo
    
    ha = dict(histtype='step', log=True, range=(-2e3, 2e3), bins=100)
    plt.clf()
    plt.hist(J.ravel(), color='b', **ha)
    plt.hist(H.ravel(), color='g', **ha)
    plt.hist(K.ravel(), color='r', **ha)
    plt.savefig('jhk.png')

    rgb = sdss_rgb([J,H,K], bands=['J','H','K'],
                   scales=dict(J=0.0072,
                               H=0.0032,
                               K=0.002))

    # scales=dict(J=0.0036,
    #             H=0.0016,
    #             K=0.001))

    print('RGB', rgb.shape)
    plt.clf()
    plt.hist(rgb[:,:,0].ravel(), histtype='step', color='r', bins=256)
    plt.hist(rgb[:,:,1].ravel(), histtype='step', color='g', bins=256)
    plt.hist(rgb[:,:,2].ravel(), histtype='step', color='b', bins=256)
    plt.savefig('rgb2.png')

    plt.clf()
    plt.imshow(rgb, interpolation='nearest', origin='lower')
    plt.savefig('rgb.png')

    sys.exit(0)
    
    # http://i.legacysurvey.org/static/tiles/decals-dr1j/1/13/2623/3926.jpg

    ver = 1
    zoom,x,y = 14, 16383, 7875
    req = duck()
    req.META = dict()
    req.GET = dict()

    r = index(req)

    # r = map_sdssco(req, ver, zoom, x, y, savecache=True, ignoreCached=True,
    #                hack_jpeg=True)
    # print('got', r)
    # sys.exit(0)

    ver = 1
    zoom,x,y = 13, 2623, 3926
    req = duck()
    req.META = dict()
    #map_sdss(req, ver, zoom, x, y, savecache=True, ignoreCached=True)

    zoom,x,y = 14, 5246, 7852
    #map_sdss(req, ver, zoom, x, y, savecache=True, ignoreCached=True)

    zoom,x,y = 16, 20990, 31418
    #map_sdss(req, ver, zoom, x, y, savecache=True, ignoreCached=True)

    zoom,x,y = 18, 83958, 125671
    #map_sdss(req, ver, zoom, x, y, savecache=True, ignoreCached=True)
