from __future__ import print_function
import os
import fitsio

from map.utils import save_jpeg, send_file, trymakedirs, oneyear, get_tile_wcs

from decals import settings
debug = print
if not settings.DEBUG_LOGGING:
    def debug(*args, **kwargs):
        pass


def read_tansip_wcs(sourcefn, ext, hdr=None, W=None, H=None, tansip=None):
    if sourcefn.endswith('.gz'):
        return None
    try:
        wcs = tansip(sourcefn, ext)
        return wcs
    except:
        # import sys
        # import traceback
        # print('failed to read WCS from file', sourcefn, 'extension', ext, 'tansip:', tansip)
        # traceback.print_exc(None, sys.stdout)
        pass
    return None

def read_tan_wcs(sourcefn, ext, hdr=None, W=None, H=None, fitsfile=None):
    from astrometry.util.util import Tan
    if not os.path.exists(sourcefn):
        return None
    wcs = read_tansip_wcs(sourcefn, ext, hdr=hdr, W=W, H=H, tansip=Tan)
    if wcs is None:
        import fitsio
        # maybe gzipped; try fitsio header.
        if hdr is None:
            hdr = fitsio.read_header(sourcefn, ext)
        if W is None or H is None:
            if fitsfile is None:
                F = fitsio.FITS(sourcefn)
            else:
                F = fitsfile
            info = F[ext].get_info()
            H,W = info['dims']

        # PS1 wonky WCS
        if (not 'CD1_1' in hdr) and ('PC001001' in hdr):
            cdelt1 = hdr['CDELT1']
            cdelt2 = hdr['CDELT2']
            # ????
            cd11 = hdr['PC001001'] * cdelt1
            cd12 = hdr['PC001002'] * cdelt1
            cd21 = hdr['PC002001'] * cdelt2
            cd22 = hdr['PC002002'] * cdelt2
        else:
            cd11,cd12,cd21,cd22 = hdr['CD1_1'], hdr['CD1_2'], hdr['CD2_1'], hdr['CD2_2'],

        wcs = Tan(*[float(x) for x in [
                    hdr['CRVAL1'], hdr['CRVAL2'], hdr['CRPIX1'], hdr['CRPIX2'],
                    cd11, cd12, cd21, cd22, W, H]])                    
    return wcs

def read_sip_wcs(sourcefn, ext, hdr=None, W=None, H=None, fitsfile=None):
    from astrometry.util.util import Sip
    return read_tansip_wcs(sourcefn, ext, hdr=hdr, W=W, H=H, tansip=Sip)

def get_scaled(scalepat, scalekwargs, scale, basefn, read_wcs=None, read_base_wcs=None,
               wcs=None, img=None, return_data=False): #, base_hdu=0):
    from scipy.ndimage.filters import gaussian_filter
    import fitsio
    from astrometry.util.util import Tan
    import tempfile
    import numpy as np

    if scale <= 0:
        return basefn
    fn = scalepat % dict(scale=scale, **scalekwargs)

    if read_wcs is None:
        read_wcs = read_tan_wcs

    if os.path.exists(fn):
        if return_data:
            F = fitsio.FITS(sourcefn)
            #img = F[0].read()
            #hdr = F[0].read_header()
            img = F[-1].read()
            hdr = F[-1].read_header()
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
            #img = F[0].read()
            #hdr = F[0].read_header()
            img = F[-1].read()
            hdr = F[-1].read_header()
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
                    scalepat=None,
                    nativescale=14, maxscale=8,
                    ):
    from decals import settings
    from map.views import tileversions

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
    if scaledir is None:
        scaledir = imagedir
    if zoom < nativescale:
        scaled = (nativescale - zoom)
        scaled = np.clip(scaled, 1, maxscale)
        #debug('Scaled-down:', scaled)
        dirnm = os.path.join(basedir, 'scaled', scaledir)
        if scalepat is None:
            scalepat = os.path.join(dirnm, '%(scale)i%(band)s', '%(brickname).3s', imagetag + '-%(brickname)s-%(band)s.fits')

    if decals is None:
        from map.views import _get_survey
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
                bwcs = read_tan_wcs(fn, 0)
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


