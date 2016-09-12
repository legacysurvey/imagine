from __future__ import print_function
import os
import fitsio
import numpy as np

from map.utils import send_file

from map.views import dr2_rgb

from map.coadds import map_coadd_bands

from decals import settings

debug = print
if not settings.DEBUG_LOGGING:
    def debug(*args, **kwargs):
        pass

def jpeg_cutout_decals_dr1j(req):
    return cutout_decals(req, jpeg=True, default_tag='decals-dr1j')

def fits_cutout_decals_dr1j(req):
    return cutout_decals(req, fits=True, default_tag='decals-dr1j')

def jpeg_cutout_decals_dr2(req):
    return cutout_decals(req, jpeg=True, default_tag='decals-dr2', dr2=True)

def fits_cutout_decals_dr2(req):
    return cutout_decals(req, fits=True, default_tag='decals-dr2', dr2=True)

def cutout_decals(req, jpeg=False, fits=False, default_tag='decals-dr1j',
                  dr2=False, dr3=False):
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

    hdr = None
    if fits:
        import fitsio
        hdr = fitsio.FITSHDR()
        hdr['SURVEY'] = 'DECaLS'
        if dr3:
            hdr['VERSION'] = 'DR3'
        elif dr2:
            hdr['VERSION'] = 'DR2'
        else:
            hdr['VERSION'] = 'DR1'

    rgbfunc = None
    if dr2 or dr3:
        rgbfunc = dr2_rgb

    return cutout_on_bricks(req, tag, imagetag=imagetag, drname=tag,
                            jpeg=jpeg, fits=fits,
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

    from decals import settings
    basedir = settings.DATA_DIR
    scalepat = os.path.join(basedir, 'scaled', 'sdssco', '%(scale)i%(band)s',
                            '%(brickname).3s', 'sdssco-%(brickname)s-%(band)s.fits')

    from views import get_sdssco_bricks, sdss_rgb

    from views import _get_survey
    survey = _get_survey('sdssco')

    return cutout_on_bricks(req, 'sdssco',
                            decals=survey,
                            jpeg=jpeg, fits=fits,
                            pixscale=0.396, bands='gri', native_zoom=13, maxscale=6,
                            rgbfunc=sdss_rgb, outtag='sdss', hdr=hdr,
                            scalepat=scalepat)

# def jpeg_cutout_unwise(req):
#     return cutout_unwise(req, jpeg=True)
# 
# def fits_cutout_unwise(req):
#     return cutout_unwise(req, fits=True)
# 
# def cutout_unwise(req, jpeg=False, fits=False):
#     hdr = None
#     if fits:
#         import fitsio
#         hdr = fitsio.FITSHDR()
#         hdr['SURVEY'] = 'SDSS'
# 
#     from decals import settings
# 
#     unwise_dir=settings.UNWISE_DIR
#     basepat = os.path.join(unwise_dir, '%(brickname).3s', '%(brickname)s', 'unwise-%(brickname)s-%(band)s-img-u.fits')
# 
#     return cutout_on_bricks(req, 'unwise', bricks=get_sdssco_bricks(), imagetag='sdssco',
#                             jpeg=jpeg, fits=fits,
#                             pixscale=0.396, bands='gri', native_zoom=13, maxscale=6,
#                             rgbfunc=sdss_rgb, outtag='sdss', hdr=hdr, basepat=basepat)

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
    layer = req.GET.get('layer', 'decals-dr3')
    if layer == 'decals-dr1j':
        return jpeg_cutout_decals_dr1j(req)
    if layer in ['sdss', 'sdssco']:
        return jpeg_cutout_sdssco(req)
    if layer == 'decals-dr2':
        return cutout_decals(req, jpeg=True, default_tag='decals-dr2', dr2=True)
    if layer == 'decals-dr3':
        return cutout_decals(req, jpeg=True, default_tag='decals-dr3', dr3=True)

def fits_cutout(req):
    layer = req.GET.get('layer', 'decals-dr3')
    if layer == 'decals-dr1j':
        return fits_cutout_decals_dr1j(req)
    if layer in ['sdss', 'sdssco']:
        return fits_cutout_sdssco(req)
    if layer == 'decals-dr2':
        return cutout_decals(req, fits=True, default_tag='decals-dr2', dr2=True)
    if layer == 'decals-dr3':
        return cutout_decals(req, fits=True, default_tag='decals-dr3', dr3=True)

