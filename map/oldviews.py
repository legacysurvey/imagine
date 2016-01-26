w_flist = None
w_flist_tree = None

sdssps = None
if False:
    from astrometry.util.plotutils import *
    import matplotlib
    matplotlib.use('Agg')
    sdssps = PlotSequence('sdss')

def map_sdss(req, ver, zoom, x, y, savecache=None, tag='sdss',
             get_images=False,
             ignoreCached=False,
             wcs=None,
             forcecache=False,
             forcescale=None,
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

