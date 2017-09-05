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
               wcs=None, img=None, return_data=False, read_base_image=None):
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

    F = None
    if img is None:
        sourcefn = get_scaled(scalepat, scalekwargs, scale-1, basefn,
                              read_base_wcs=read_base_wcs, read_wcs=read_wcs,
                              read_base_image=read_base_image)
        debug('Source:', sourcefn)
        if sourcefn is None or not os.path.exists(sourcefn):
            debug('Image source file', sourcefn, 'not found')
            return None
        try:
            #debug('Reading image:', sourcefn, 'for scale', scale, '; read_base_image is', read_base_image)

            if scale == 1 and read_base_image is not None:
                img,hdr = read_base_image(sourcefn)
            else:
                F = fitsio.FITS(sourcefn)
                # img = F[0].read()
                # hdr = F[0].read_header()
                img = F[-1].read()
                hdr = F[-1].read_header()
        except:
            debug('Failed to read:', sourcefn)
            import traceback
            traceback.print_exc()
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
    #debug('Temp file', tmpfn)
    # To avoid overwriting the (empty) temp file (and fitsio
    # debuging "Removing existing file")
    os.unlink(tmpfn)
    fitsio.write(tmpfn, I2, header=hdr, clobber=True)
    if not ro:
        os.rename(tmpfn, fn)
        debug('Wrote', fn)
    else:
        print('Leaving temp file for get_scaled:', scalepat, scalekwargs, scale, basefn)
        fn = tmpfn
    if return_data:
        return I2,wcs2,fn
    return fn

