import os

w_flist = None
w_flist_tree = None

sdssps = None
if False:
    from astrometry.util.plotutils import *
    import matplotlib
    matplotlib.use('Agg')
    sdssps = PlotSequence('sdss')

from map.views import tileversions, get_scaled, _read_sip_wcs, sdss_rgb, save_jpeg
tileversions.update(dict(sdss=[1,]))

def map_sdss(req, ver, zoom, x, y, savecache=None, tag='sdss',
             get_images=False,
             ignoreCached=False,
             wcs=None,
             forcecache=False,
             forcescale=None,
             bestOnly=False,
             **kwargs):
    from decals import settings

    if savecache is None:
        savecache = settings.SAVE_CACHE
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
        if get_images:
            return None
        return send_file(tilefn, 'image/jpeg', expires=oneyear,
                         modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'))

    if not savecache:
        import tempfile
        f,tilefn = tempfile.mkstemp(suffix='.jpg')
        os.close(f)

    if wcs is None:
        try:
            wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
        except RuntimeError as e:
            if get_images:
                return None
            return HttpResponse(e.strerror)
    else:
        W = wcs.get_width()
        H = wcs.get_height()

    from astrometry.util.fits import fits_table
    import numpy as np
    from astrometry.libkd.spherematch import tree_build_radec, tree_search_radec
    from astrometry.util.starutil_numpy import degrees_between, arcsec_between
    from astrometry.util.resample import resample_with_wcs, OverlapError
    from astrometry.util.util import Tan, Sip
    import fitsio

    print 'Tile wcs: center', wcs.radec_center(), 'pixel scale', wcs.pixel_scale()

    global w_flist
    global w_flist_tree
    if w_flist is None:
        w_flist = fits_table(os.path.join(settings.DATA_DIR, 'sdss',
                                          'window_flist.fits'),
                             columns=['run','rerun','camcol','field','ra','dec','score'])
        print 'Read', len(w_flist), 'window_flist entries'
        w_flist.cut(w_flist.rerun == '301')
        print 'Cut to', len(w_flist), 'in rerun 301'
        w_flist_tree = tree_build_radec(w_flist.ra, w_flist.dec)

    # SDSS field size
    radius = 1.01 * np.hypot(10., 14.)/2. / 60.

    # leaflet tile size
    ra,dec = wcs.pixelxy2radec(W/2., H/2.)[-2:]
    r0,d0 = wcs.pixelxy2radec(1, 1)[-2:]
    r1,d1 = wcs.pixelxy2radec(W, H)[-2:]
    radius = radius + max(degrees_between(ra,dec, r0,d0), degrees_between(ra,dec, r1,d1))

    J = tree_search_radec(w_flist_tree, ra, dec, radius)

    print len(J), 'overlapping SDSS fields found'
    if len(J) == 0:
        if get_images:
            return None
        if forcecache:
            # create symlink to blank.jpg!
            trymakedirs(tilefn)
            src = os.path.join(settings.STATIC_ROOT, 'blank.jpg')
            if os.path.exists(tilefn):
                os.unlink(tilefn)
            os.symlink(src, tilefn)
            print 'Symlinked', tilefn, '->', src
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(settings.STATIC_URL + 'blank.jpg')
    
    ww = [1, W*0.25, W*0.5, W*0.75, W]
    hh = [1, H*0.25, H*0.5, H*0.75, H]

    r,d = wcs.pixelxy2radec(
        [1]*len(hh) + ww          + [W]*len(hh) +        list(reversed(ww)),
        hh          + [1]*len(ww) + list(reversed(hh)) + [H]*len(ww))[-2:]

    scaled = 0
    scalepat = None
    scaledir = 'sdss'
    
    if zoom <= 13 and forcescale is None:
        # Get *actual* pixel scales at the top & bottom
        r1,d1 = wcs.pixelxy2radec(W/2., H)[-2:]
        r2,d2 = wcs.pixelxy2radec(W/2., H-1.)[-2:]
        r3,d3 = wcs.pixelxy2radec(W/2., 1.)[-2:]
        r4,d4 = wcs.pixelxy2radec(W/2., 2.)[-2:]
        # Take the min = most zoomed-in
        scale = min(arcsec_between(r1,d1, r2,d2), arcsec_between(r3,d3, r4,d4))
        
        native_scale = 0.396
        scaled = int(np.floor(np.log2(scale / native_scale)))
        print 'Zoom:', zoom, 'x,y', x,y, 'Tile pixel scale:', scale, 'Scale step:', scaled
        scaled = np.clip(scaled, 1, 7)
        dirnm = os.path.join(basedir, 'scaled', scaledir)
        scalepat = os.path.join(dirnm, '%(scale)i%(band)s', '%(rerun)s', '%(run)i', '%(camcol)i', 'sdss-%(run)i-%(camcol)i-%(field)i-%(band)s.fits')

    if forcescale is not None:
        scaled = forcescale

    bands = 'gri'
    rimgs = [np.zeros((H,W), np.float32) for band in bands]
    rns   = [np.zeros((H,W), np.float32)   for band in bands]

    from astrometry.sdss import AsTransWrapper, DR9
    sdss = DR9(basedir=settings.SDSS_DIR)
    sdss.saveUnzippedFiles(settings.SDSS_DIR)
    #sdss.setFitsioReadBZ2()
    if settings.SDSS_PHOTOOBJS:
        sdss.useLocalTree(photoObjs=settings.SDSS_PHOTOOBJS,
                          resolve=settings.SDSS_RESOLVE)

    for jnum,j in enumerate(J):
        print 'SDSS field', jnum, 'of', len(J), 'for zoom', zoom, 'x', x, 'y', y
        im = w_flist[j]

        if im.score >= 0.5:
            weight = 1.
        else:
            weight = 0.001


        for band,rimg,rn in zip(bands, rimgs, rns):
            if im.rerun != '301':
                continue
            tmpsuff = '.tmp%08i' % np.random.randint(100000000)
            basefn = sdss.retrieve('frame', im.run, im.camcol, field=im.field,
                                   band=band, rerun=im.rerun, tempsuffix=tmpsuff)
            if scaled > 0:
                fnargs = dict(band=band, rerun=im.rerun, run=im.run,
                              camcol=im.camcol, field=im.field)
                fn = get_scaled(scalepat, fnargs, scaled, basefn,
                                read_base_wcs=read_astrans, read_wcs=_read_sip_wcs)
                print 'get_scaled:', fn
            else:
                fn = basefn
            frame = None
            if fn == basefn:
                frame = sdss.readFrame(im.run, im.camcol, im.field, band,
                                       filename=fn)
                h,w = frame.getImageShape()
                # Trim off the overlapping top of the image
                # Wimp out and instead of trimming 128 pix, trim 124!
                trim = 124
                subh = h - trim
                astrans = frame.getAsTrans()
                fwcs = AsTransWrapper(astrans, w, subh)
                fullimg = frame.getImage()
                fullimg = fullimg[:-trim,:]
            else:
                fwcs = Sip(fn)
                fitsimg = fitsio.FITS(fn)[0]
                h,w = fitsimg.get_info()['dims']
                fullimg = fitsimg.read()

            try:
                #Yo,Xo,Yi,Xi,nil = resample_with_wcs(wcs, fwcs, [], 3)
                Yo,Xo,Yi,Xi,[resamp] = resample_with_wcs(wcs, fwcs, [fullimg], 2)
            except OverlapError:
                continue
            if len(Xi) == 0:
                #print 'No overlap'
                continue

            if sdssps is not None:
                x0 = Xi.min()
                x1 = Xi.max()
                y0 = Yi.min()
                y1 = Yi.max()
                slc = (slice(y0,y1+1), slice(x0,x1+1))
                if frame is not None:
                    img = frame.getImageSlice(slc)
                else:
                    img = fitsimg[slc]
            #rimg[Yo,Xo] += img[Yi-y0, Xi-x0]

            if bestOnly:
                K = np.flatnonzero(weight > rn[Yo,Xo])
                print('Updating', len(K), 'of', len(Yo), 'pixels')
                if len(K):
                    rimg[Yo[K],Xo[K]] = resamp[K] * weight
                    rn  [Yo[K],Xo[K]] = weight
            else:
                rimg[Yo,Xo] += resamp * weight
                rn  [Yo,Xo] += weight

            if sdssps is not None:
                # goodpix = np.ones(img.shape, bool)
                # fpM = sdss.readFpM(im.run, im.camcol, im.field, band)
                # for plane in [ 'INTERP', 'SATUR', 'CR', 'GHOST' ]:
                #     fpM.setMaskedPixels(plane, goodpix, False, roi=[x0,x1,y0,y1])
                plt.clf()
                #ima = dict(vmin=-0.05, vmax=0.5)
                #ima = dict(vmin=-0.5, vmax=2.)
                ima = dict(vmax=np.percentile(img, 99))
                plt.subplot(2,3,1)
                dimshow(img, ticks=False, **ima)
                plt.title('image')
                rthis = np.zeros_like(rimg)
                #rthis[Yo,Xo] += img[Yi-y0, Xi-x0]
                rthis[Yo,Xo] += resamp
                plt.subplot(2,3,2)
                dimshow(rthis, ticks=False, **ima)
                plt.title('resampled')
                # plt.subplot(2,3,3)
                # dimshow(goodpix, ticks=False, vmin=0, vmax=1)
                # plt.title('good pix')
                plt.subplot(2,3,4)
                dimshow(rimg / np.maximum(rn, 1), ticks=False, **ima)
                plt.title('coadd')
                plt.subplot(2,3,5)
                dimshow(rn, vmin=0, ticks=False)
                plt.title('coverage: max %i' % rn.max())
                plt.subplot(2,3,6)
                rgb = sdss_rgb([rimg/np.maximum(rn,1)
                                for rimg,rn in zip(rimgs,rns)], bands)
                dimshow(rgb)
                plt.suptitle('SDSS %s, R/C/F %i/%i/%i' % (band, im.run, im.camcol, im.field))
                sdssps.savefig()
                
    for rimg,rn in zip(rimgs, rns):
        rimg /= np.maximum(rn, 1e-3)
    del rns

    if get_images:
        return rimgs

    rgb = sdss_rgb(rimgs, bands)
    trymakedirs(tilefn)
    save_jpeg(tilefn, rgb)
    print 'Wrote', tilefn

    return send_file(tilefn, 'image/jpeg', unlink=(not savecache))

Tdepth = None
Tdepthkd = None

def map_decam_depth(req, ver, zoom, x, y, savecache=False, band=None,
                    ignoreCached=False):
    global Tdepth
    global Tdepthkd

    if band is None:
        band = req.GET.get('band')
    if not band in ['g','r','z']:
        raise RuntimeError('Invalid band')
    tag = 'decam-depth-%s' % band
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
        print 'Cached:', tilefn
        return send_file(tilefn, 'image/jpeg', expires=oneyear,
                         modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'))
    from astrometry.util.util import Tan
    from astrometry.libkd.spherematch import match_radec
    from astrometry.libkd.spherematch import tree_build_radec, tree_search_radec
    from astrometry.util.fits import fits_table
    from astrometry.util.starutil_numpy import degrees_between
    import numpy as np
    import fitsio
    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)
    rlo,d = wcs.pixelxy2radec(W, H/2)[-2:]
    rhi,d = wcs.pixelxy2radec(1, H/2)[-2:]
    r,d1 = wcs.pixelxy2radec(W/2, 1)[-2:]
    r,d2 = wcs.pixelxy2radec(W/2, H)[-2:]

    r,d = wcs.pixelxy2radec(W/2, H/2)[-2:]
    rad = max(degrees_between(r, d, rlo, d1),
              degrees_between(r, d, rhi, d2))

    if Tdepth is None:
        T = fits_table(os.path.join(basedir, 'decals-zpt-nondecals.fits'),
                            columns=['ccdra','ccddec','arawgain', 'avsky',
                                     'ccdzpt', 'filter', 'crpix1','crpix2',
                                     'crval1','crval2','cd1_1','cd1_2',
                                     'cd2_1','cd2_2', 'naxis1', 'naxis2', 'exptime', 'fwhm'])
        T.rename('ccdra',  'ra')
        T.rename('ccddec', 'dec')

        Tdepth = {}
        Tdepthkd = {}
        for b in ['g','r','z']:
            Tdepth[b] = T[T.filter == b]
            Tdepthkd[b] = tree_build_radec(Tdepth[b].ra, Tdepth[b].dec)

    T = Tdepth[band]
    Tkd = Tdepthkd[band]

    #I,J,d = match_radec(T.ra, T.dec, r, d, rad + 0.2)
    I = tree_search_radec(Tkd, r, d, rad + 0.2)
    print len(I), 'CCDs in range'
    if len(I) == 0:
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(settings.STATIC_URL + 'blank.jpg')

    depthiv = np.zeros((H,W), np.float32)
    for t in T[I]:
        twcs = Tan(*[float(x) for x in [
            t.crval1, t.crval2, t.crpix1, t.crpix2,
            t.cd1_1, t.cd1_2, t.cd2_1, t.cd2_2, t.naxis1, t.naxis2]])
        w,h = t.naxis1, t.naxis2
        r,d = twcs.pixelxy2radec([1,1,w,w], [1,h,h,1])
        ok,x,y = wcs.radec2pixelxy(r, d)
        #print 'x,y coords of CCD:', x, y
        x0 = int(x.min())
        x1 = int(x.max())
        y0 = int(y.min())
        y1 = int(y.max())
        if y1 < 0 or x1 < 0 or x0 >= W or y0 >= H:
            continue

        readnoise = 10. # e-; 7.0 to 15.0 according to DECam Data Handbook
        skysig = np.sqrt(t.avsky * t.arawgain + readnoise**2) / t.arawgain
        zpscale = 10.**((t.ccdzpt - 22.5)/2.5) * t.exptime
        sig1 = skysig / zpscale
        psf_sigma = t.fwhm / 2.35
        # point-source depth
        psfnorm = 1./(2. * np.sqrt(np.pi) * psf_sigma)
        detsig1 = sig1 / psfnorm

        #print '5-sigma point-source depth:', NanoMaggies.nanomaggiesToMag(detsig1 * 5.)

        div = 1 / detsig1**2
        depthiv[max(y0,0):min(y1,H), max(x0,0):min(x1,W)] += div

    ptsrc = -2.5 * (np.log10(np.sqrt(1./depthiv) * 5) - 9)
    ptsrc[depthiv == 0] = 0.

    if savecache:
        trymakedirs(tilefn)
    else:
        import tempfile
        f,tilefn = tempfile.mkstemp(suffix='.jpg')
        os.close(f)

    import pylab as plt
    plt.imsave(tilefn, ptsrc, vmin=22., vmax=25., cmap='hot')#nipy_spectral')

    return send_file(tilefn, 'image/jpeg', unlink=(not savecache))


def map_decals_wl(req, ver, zoom, x, y):
    tag = 'decals-wl'
    ignoreCached = False
    filename = None
    forcecache = False

    from decals import settings
    savecache = settings.SAVE_CACHE

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
        print('Cached:', tilefn)
        return send_file(tilefn, 'image/jpeg', expires=oneyear,
                         modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'),
                         filename=filename)
    else:
        print('Tile image does not exist:', tilefn)
    from astrometry.util.resample import resample_with_wcs, OverlapError
    from astrometry.util.util import Tan
    from astrometry.libkd.spherematch import match_radec
    from astrometry.util.fits import fits_table
    from astrometry.util.starutil_numpy import degrees_between
    import numpy as np
    import fitsio

    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        return HttpResponse(e.strerror)

    mydir = os.path.join(basedir, 'coadd', 'weak-lensing')

    rlo,d = wcs.pixelxy2radec(W, H/2)[-2:]
    rhi,d = wcs.pixelxy2radec(1, H/2)[-2:]
    r,d1 = wcs.pixelxy2radec(W/2, 1)[-2:]
    r,d2 = wcs.pixelxy2radec(W/2, H)[-2:]
    #dlo = min(d1, d2)
    #dhi = max(d1, d2)

    r,d = wcs.pixelxy2radec(W/2, H/2)[-2:]
    rad = degrees_between(r, d, rlo, d1)

    fn = os.path.join(mydir, 'index.fits')
    if not os.path.exists(fn):
        #
        ii,rr,dd = [],[],[]
        for i in range(1, 52852+1):
            imgfn = os.path.join(mydir, 'map%i.fits' % i)
            hdr = fitsio.read_header(imgfn)
            r = hdr['CRVAL1']
            d = hdr['CRVAL2']
            ii.append(i)
            rr.append(r)
            dd.append(d)
        T = fits_table()
        T.ra  = np.array(rr)
        T.dec = np.array(dd)
        T.i   = np.array(ii)
        T.writeto(fn)

    T = fits_table(fn)
    I,J,d = match_radec(T.ra, T.dec, r, d, rad + 0.2)
    T.cut(I)
    print(len(T), 'weak-lensing maps in range')
    
    if len(I) == 0:
        from django.http import HttpResponseRedirect
        if forcecache:
            # create symlink to blank.jpg!
            trymakedirs(tilefn)
            src = os.path.join(settings.STATIC_ROOT, 'blank.jpg')
            if os.path.exists(tilefn):
                os.unlink(tilefn)
            os.symlink(src, tilefn)
            print('Symlinked', tilefn, '->', src)
        return HttpResponseRedirect(settings.STATIC_URL + 'blank.jpg')

    r,d = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                            [1,H/2,H,H,H,H/2,1,1])[-2:]

    foundany = False
    rimg = np.zeros((H,W), np.float32)
    rn   = np.zeros((H,W), np.uint8)
    for tilei in T.i:
        fn = os.path.join(mydir, 'map%i.fits' % tilei)
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
        print('Reading', fn)
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
            print('Resampling exception')
            continue

        rimg[Yo,Xo] += img[Yi,Xi]
        rn  [Yo,Xo] += 1
    rimg /= np.maximum(rn, 1)

    if forcecache:
        savecache = True

    if savecache:
        trymakedirs(tilefn)
    else:
        import tempfile
        f,tilefn = tempfile.mkstemp(suffix='.jpg')
        os.close(f)

    import pylab as plt

    # S/N
    #lo,hi = 1.5, 5.0
    lo,hi = 0, 5.0
    rgb = plt.cm.hot((rimg - lo) / (hi - lo))
    plt.imsave(tilefn, rgb)
    print('Wrote', tilefn)

    return send_file(tilefn, 'image/jpeg', unlink=(not savecache),
                     filename=filename)




B_dr1n = None

def get_dr1n_bricks():
    global B_dr1n
    if B_dr1n is not None:
        return B_dr1n
    from astrometry.util.fits import fits_table
    import numpy as np
    B_dr1n = fits_table(os.path.join(settings.DATA_DIR,
                                     'decals-bricks.fits'))
    print('Total bricks:', len(B_dr1n))
    B_dr1n.cut(np.logical_or(
        # Virgo
        (B_dr1n.ra > 185.) * (B_dr1n.ra < 190.) *
        (B_dr1n.dec > 10.)  * (B_dr1n.dec < 15.),
        # Arjun's LSB
        (B_dr1n.ra > 147.2) * (B_dr1n.ra < 147.8) *
        (B_dr1n.dec > -0.4)  * (B_dr1n.dec < 0.4)
    ))
    print(len(B_dr1n), 'bricks in Virgo/LSB region')
    return B_dr1n


def map_decals_model_dr1n(*args, **kwargs):
    return map_decals_dr1n(*args, model=True, model_gz=False, **kwargs)

def map_decals_resid_dr1n(*args, **kwargs):
    return map_decals_dr1n(*args, resid=True, model_gz=False, **kwargs)

def map_decals_dr1n(req, ver, zoom, x, y, savecache=None,
                    model=False, resid=False, nexp=False,
                    **kwargs):
    if savecache is None:
        savecache = settings.SAVE_CACHE
    B_dr1n = get_dr1n_bricks()

    imagetag = 'image'
    tag = 'decals-dr1n'
    imagedir = 'decals-dr1n'
    rgb = rgbkwargs
    if model:
        imagetag = 'model'
        tag = 'decals-model-dr1n'
        scaledir = 'decals-dr1n'
        kwargs.update(model_gz=False, add_gz=True, scaledir=scaledir)
    if resid:
        imagetag = 'resid'
        kwargs.update(modeldir = 'decals-dr1n-model')
        tag = 'decals-resid-dr1n'
    # if nexp:
    #     imagetag = 'nexp'
    #     tag = 'decals-nexp-dr1n'
    #     rgb = rgbkwargs_nexp

    return map_coadd_bands(req, ver, zoom, x, y, 'grz', tag, imagedir,
                           imagetag=imagetag,
                           rgbkwargs=rgb,
                           bricks=B_dr1n,
                           savecache=savecache, **kwargs)


B_dr1k = None

def map_decals_model_dr1k(*args, **kwargs):
    return map_decals_dr1k(*args, model=True, model_gz=False, **kwargs)

def map_decals_dr1k(req, ver, zoom, x, y, savecache=None,
                    model=False, resid=False, nexp=False,
                    **kwargs):
    if savecache is None:
        savecache = settings.SAVE_CACHE
    global B_dr1k
    if B_dr1k is None:
        from astrometry.util.fits import fits_table
        import numpy as np

        B_dr1k = fits_table(os.path.join(settings.DATA_DIR, 'decals-dr1k',
                                         'decals-bricks-exist.fits'))
        B_dr1k.cut((B_dr1k.ra > 148.7) * (B_dr1k.ra < 151.5) *
                   (B_dr1k.dec > 0.9)  * (B_dr1k.dec < 3.6))
        # B_dr1k.cut(reduce(np.logical_or, [B_dr1k.has_image_g,
        #                                   B_dr1k.has_image_r,
        #                                   B_dr1k.has_image_z]))
        # B_dr1k.has_g = B_dr1k.has_image_g
        # B_dr1k.has_r = B_dr1k.has_image_r
        # B_dr1k.has_z = B_dr1k.has_image_z
        print(len(B_dr1k), 'bricks in COSMOS region')
        print(sum(B_dr1k.has_g), 'with g')
        print(sum(B_dr1k.has_r), 'with r')
        print(sum(B_dr1k.has_z), 'with z')
        B_dr1k.cut(reduce(np.logical_or, [B_dr1k.has_g > 0,
                                          B_dr1k.has_r > 0,
                                          B_dr1k.has_z > 0]))
        print(len(B_dr1k), 'bricks with coverage')

    imagetag = 'image'
    tag = 'decals-dr1k'
    imagedir = 'decals-dr1k'
    rgb = rgbkwargs
    if model:
        imagetag = 'model'
        tag = 'decals-model-dr1k'
        scaledir = 'decals-dr1k'
        kwargs.update(model_gz=False, add_gz=True, scaledir=scaledir)
    if resid:
        imagetag = 'resid'
        kwargs.update(modeldir = 'decals-dr1k-model')
        tag = 'decals-resid-dr1k'
    if nexp:
        imagetag = 'nexp'
        tag = 'decals-nexp-dr1k'
        rgb = rgbkwargs_nexp

    return map_coadd_bands(req, ver, zoom, x, y, 'grz', tag, imagedir,
                           imagetag=imagetag,
                           rgbkwargs=rgb,
                           bricks=B_dr1k,
                           savecache=savecache, **kwargs)




def map_decals_nexp_dr1j(*args, **kwargs):
    return map_decals_dr1j(*args, nexp=True, model_gz=False, add_gz=True, **kwargs)

def map_unwise_w3w4(*args, **kwargs):
    kwargs.update(S=[1e5, 1e6])
    return map_unwise(*args, bands=[3,4], tag='unwise-w3w4', **kwargs)

def map_unwise_w1234(*args, **kwargs):
    kwargs.update(S=[3e3, 3e3, 3e5, 1e6])
    return map_unwise(*args, bands=[1,2,3,4], tag='unwise-w1234', **kwargs)

def cat_vcc(req, ver):
    import json
    tag = 'ngc'
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
    T = fits_table(os.path.join(settings.DATA_DIR, 'virgo-cluster-cat-2.fits'))
    print(len(T), 'in VCC 2; ra', ralo, rahi, 'dec', declo, dechi)
    T.cut((T.ra > ralo) * (T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    print(len(T), 'in cut')
    TT.append(T)

    T = fits_table(os.path.join(settings.DATA_DIR, 'virgo-cluster-cat-3.fits'))
    print(len(T), 'in VCC 3; ra', ralo, rahi, 'dec', declo, dechi)
    T.cut((T.ra > ralo) * (T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    print(len(T), 'in cut')
    T.evcc_id = np.array(['-']*len(T))
    T.rename('id', 'vcc_id')
    TT.append(T)
    T = merge_tables(TT)

    rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
    names = []

    for t in T:
        evcc = t.evcc_id.strip()
        vcc = t.vcc_id.strip()
        ngc = t.ngc.strip()
        nms = []
        if evcc != '-':
            nms.append('EVCC ' + evcc)
        if vcc != '-':
            nms.append('VCC ' + vcc)
        if ngc != '-':
            nms.append('NGC ' + ngc)
        names.append(' / '.join(nms))

    return HttpResponse(json.dumps(dict(rd=rd, name=names)),
                        content_type='application/json')


def read_astrans(fn, hdu, hdr=None, W=None, H=None, fitsfile=None):
    from astrometry.sdss import AsTransWrapper, AsTrans
    from astrometry.util.util import Tan, fit_sip_wcs_py
    from astrometry.util.starutil_numpy import radectoxyz
    import numpy as np
    
    astrans = AsTrans.read(fn, F=fitsfile, primhdr=hdr)
    # Approximate as SIP.
    if hdr is None and fn.endswith('.bz2'):
        import fitsio
        hdr = fitsio.read_header(fn, 0)

    if hdr is not None:
        tan = Tan(*[float(hdr[k]) for k in [
                    'CRVAL1', 'CRVAL2', 'CRPIX1', 'CRPIX2',
                    'CD1_1', 'CD1_2', 'CD2_1', 'CD2_2', 'NAXIS1','NAXIS2']])
    else:
        # Frame files include a TAN header... start there.
        tan = Tan(fn)

    # Evaluate AsTrans on a pixel grid...
    h,w = tan.shape
    xx = np.linspace(1, w, 20)
    yy = np.linspace(1, h, 20)
    xx,yy = np.meshgrid(xx, yy)
    xx = xx.ravel()
    yy = yy.ravel()
    rr,dd = astrans.pixel_to_radec(xx, yy)

    xyz = radectoxyz(rr, dd)
    fieldxy = np.vstack((xx, yy)).T

    sip_order = 5
    inv_order = 7
    sip = fit_sip_wcs_py(xyz, fieldxy, None, tan, sip_order, inv_order)
    return sip





if __name__ == '__main__':
    from astrometry.util.util import Tan
    import fitsio

    W,H = 9000,9000
    #W,H = 500,500
    pixscale = 0.4 / 3600.

    wcs = Tan(*[float(x) for x in 
                [194.954, 27.980, (W+1)/2., (H+1)/2., -pixscale, 0, 0, pixscale,
                 W, H]])
    gri = map_sdss(None, 1, 1, 1, 1, get_images=True, wcs=wcs, forcescale=0,
                   bestOnly=True)
    #print 'Got', gri
    g,r,i = gri
    print 'g', g.shape

    hdr = fitsio.FITSHDR()
    wcs.add_to_header(hdr)

    fitsio.write('coma-g.fits', g, header=hdr, clobber=True)
    fitsio.write('coma-r.fits', r, header=hdr, clobber=True)
    fitsio.write('coma-i.fits', i, header=hdr, clobber=True)

    bands = 'gri'
    rgb = sdss_rgb(gri, bands)
    save_jpeg('coma.jpg', rgb)
