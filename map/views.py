from __future__ import print_function
if __name__ == '__main__':
    ## NOTE, if you want to run this from the command-line, probably have to do so
    # from sgn04 node within the virtualenv.
    import sys
    sys.path.insert(0, 'django-1.9')
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'
    import django
    #print('Django:', django.__file__)
    #print('Version:', django.get_version())

import os
import re
from django.http import HttpResponse, StreamingHttpResponse
from django.core.urlresolvers import reverse
from django import forms

from decals import settings
from map.utils import (get_tile_wcs, trymakedirs, save_jpeg, ra2long, ra2long_B,
                       send_file, oneyear)
from map.coadds import get_scaled, map_coadd_bands
from map.cats import get_random_galaxy

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
    'sfd': [1, 2],
    'halpha': [1,],
    'sdss': [1,],
    'sdssco': [1,],

    'mzls-dr3': [1],

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

galaxycat = None

def index(req):
    from cats import cat_user

    layer = req.GET.get('layer', 'decals-dr3')
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

    static_tile_url_B = settings.STATIC_TILE_URL_B
    subdomains_B = settings.SUBDOMAINS_B
    subdomains_B = '[' + ','.join(["'%s'" % s for s in subdomains_B]) + '];'

    ccdsurl = settings.ROOT_URL + '/ccds/?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&id={id}'
    bricksurl = settings.ROOT_URL + '/bricks/?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&id={id}'
    expsurl = settings.ROOT_URL + '/exps/?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&id={id}'
    platesurl = settings.ROOT_URL + '/sdss-plates/?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}'
    sqlurl = settings.ROOT_URL + '/sql-box/?north={north}&east={east}&south={south}&west={west}&q={q}'
    namequeryurl = settings.ROOT_URL + '/namequery/?obj={obj}'

    uploadurl = settings.ROOT_URL + '/upload-cat/'

    usercatalog = req.GET.get('catalog', None)
    usercats = None
    if usercatalog is not None:
        usercats = usercatalog.split(',')
        keepcats = []
        for cat in usercats:
            if not re.match('\w?', cat):
                print('Usercatalog "%s" did not match regex' % cat)
                continue
            keepcats.append(cat)
        usercats = keepcats
        if len(usercats) == 0:
            usercats = None
    usercatalogurl = reverse(cat_user, args=(1,)) + '?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&cat={cat}'

    baseurl = req.path

    absurl = req.build_absolute_uri(settings.ROOT_URL)

    from django.shortcuts import render

    return render(req, 'index.html',
                  dict(ra=ra, dec=dec, zoom=zoom,
                       mosaic_bok=False,
                       dr1=False,
                       galname=galname,
                       layer=layer, tileurl=tileurl,
                       absurl=absurl,
                       sqlurl=sqlurl,
                       uploadurl=uploadurl,
                       baseurl=baseurl, caturl=caturl, bricksurl=bricksurl,
                       smallcaturl=smallcaturl,
                       namequeryurl=namequeryurl,
                       ccdsurl=ccdsurl,
                       expsurl=expsurl,
                       platesurl=platesurl,
                       static_tile_url=static_tile_url,
                       subdomains=subdomains,

                       static_tile_url_B=static_tile_url_B,
                       subdomains_B=subdomains_B,

                       maxNativeZoom = settings.MAX_NATIVE_ZOOM,
                       usercatalogs = usercats,
                       usercatalogurl = usercatalogurl,
                       enable_sql = settings.ENABLE_SQL,
                       enable_vcc = settings.ENABLE_VCC,
                       enable_wl = settings.ENABLE_WL,
                       enable_cutouts = settings.ENABLE_CUTOUTS,
                       enable_mzls = settings.ENABLE_MZLS,
                       ))


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

    # Check for RA,Dec in decimal degrees or H:M:S.
    words = obj.strip().split()
    print('Parsing name query: words', words)
    if len(words) == 2:
        try:
            rastr,decstr = words
            ra,dec = parse_radec_strings(rastr, decstr)
            print('Parsed as:', ra,dec)
            return HttpResponse(json.dumps(dict(ra=ra, dec=dec, name=obj)),
                                content_type='application/json')

        except:
            # import traceback
            # print('Failed to parse string as RA,Dec:', obj)
            # traceback.print_exc()
            pass

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

def parse_radec_strings(rastr, decstr):
    try:
        ra = float(rastr)
        dec = float(decstr)
        return ra,dec
    except:
        pass
    # or raise...
    from astrometry.util.starutil_numpy import hmsstring2ra, dmsstring2dec
    ra = hmsstring2ra(rastr)
    dec = dmsstring2dec(decstr)
    return ra,dec

def data_for_radec(req):
    import numpy as np
    ra  = float(req.GET['ra'])
    dec = float(req.GET['dec'])
    name = req.GET.get('layer', 'decals-dr3')

    ## FIXME -- could point to unWISE data!
    #if 'unwise' in name or name == 'sdssco':
    #    name = 'decals-dr3'

    survey = _get_survey(name)
    if survey is None:
        survey = _get_survey('decals-dr3')

    bricks = survey.get_bricks()
    I = np.flatnonzero((ra >= bricks.ra1) * (ra < bricks.ra2) *
                       (dec >= bricks.dec1) * (dec < bricks.dec2))
    if len(I) == 0:
        return HttpResponse('No DECaLS data overlaps RA,Dec = %.4f, %.4f for version %s' % (ra, dec, name))
    I = I[0]
    brickname = bricks.brickname[I]

    return brick_detail(req, brickname)



class MapLayer(object):
    '''
    Represents a "bricked" image map layer: eg, DECaLS DRx (image, model, or
    resid), SDSSco, unWISE.
    '''
    def __init__(self, name,
                 nativescale=14, maxscale=8):
        ''' name: like 'decals-dr2-model'
        '''
        self.name = name
        self.nativescale = nativescale
        self.minscale = 1
        self.maxscale = maxscale
        self.hack_jpeg = False
        self.pixscale = 0.262

    def get_bricks(self):
        pass

    def get_bands(self):
        pass
    
    def get_rgb(self, imgs, bands, **kwargs):
        pass

    def tileversion_ok(self, ver):
        global tileversions
        return ver in tileversions.get(self.name, [])

    def get_tile_filename(self, ver, zoom, x, y):
        '''Pre-rendered JPEG tile filename.'''
        from decals import settings
        basedir = settings.DATA_DIR
        tilefn = os.path.join(basedir, 'tiles', self.name,
                              '%i' % ver, '%i' % zoom, '%i' % x, '%i.jpg' % y)
        return tilefn

    def get_scale(self, zoom, x, y, wcs):
        import numpy as np
        '''Integer scale step (1=binned 2x2, 2=binned 4x4, ...)'''
        if zoom >= self.nativescale:
            return 0
        scale = (self.nativescale - zoom)
        scale = np.clip(scale, self.minscale, self.maxscale)
        return scale

    def bricks_touching_aa_wcs(self, wcs):
        '''Assumes WCS is axis-aligned and normal parity'''
        W = wcs.get_width()
        H = wcs.get_height()
        rlo,d = wcs.pixelxy2radec(W, H/2)[-2:]
        rhi,d = wcs.pixelxy2radec(1, H/2)[-2:]
        r,d1 = wcs.pixelxy2radec(W/2, 1)[-2:]
        r,d2 = wcs.pixelxy2radec(W/2, H)[-2:]
        dlo = min(d1, d2)
        dhi = max(d1, d2)
        #print('RA,Dec bounds of WCS:', rlo,rhi,dlo,dhi)
        return self.bricks_touching_radec_box(rlo, rhi, dlo, dhi)

    def bricks_touching_general_wcs(self, wcs):
        import numpy as np
        W = wcs.get_width()
        H = wcs.get_height()
        r,d = wcs.radec_center()
        rad = np.hypot(W, H)/2. * wcs.pixel_scale() / 3600.
        # margin
        rad *= 1.01

        ## FIXME -- cos(Dec) of center Dec is an approximation...
        dra = rad / np.cos(np.deg2rad(d))

        allbricks = []


        #print('Bricks touching general WCS: RA,Dec center', r,d)
        #print('radius', rad, 'degrees; dRA', dra, 'degrees')

        # Near RA=0 boundary?
        if r - dra < 0.:
            allbricks.append(self.bricks_touching_radec_box(0., r+dra, d-rad, d+rad))
            allbricks.append(self.bricks_touching_radec_box(r-dra+360., 360., d-rad, d+rad))
        # Near RA=360 boundary?
        elif r + dra > 360.:
            allbricks.append(self.bricks_touching_radec_box(r-dra, 360., d-rad, d+rad))
            allbricks.append(self.bricks_touching_radec_box(0., r+dra-360., d-rad, d+rad))
        else:
            allbricks.append(self.bricks_touching_radec_box(r-dra, r+dra, d-rad, d+rad))

        allbricks = [b for b in allbricks if b is not None]
        if len(allbricks) == 1:
            return allbricks[0]
        # append
        from astrometry.util.fits import merge_tables
        return merge_tables(allbricks)

    def bricks_touching_radec_box(self, rlo, rhi, dlo, dhi):
        pass

    def bricknames_for_band(self, bricks, band):
        return bricks.brickname
        '''
            has = getattr(B, 'has_%s' % band, None)
            if has is not None and not has[i]:
                # No coverage for band in this brick.
                debug('Brick', brickname, 'has no', band, 'band')
                continue
        '''

    def get_filename(self, brickname, band, scale):
        pass

    def read_image(self, brickname, band, scale, slc):
        import fitsio
        fn = self.get_filename(brickname, band, scale)
        f = fitsio.FITS(fn)[0]
        img = f[slc]
        return img

    def read_wcs(self, brickname, band, scale):
        from coadds import read_tan_wcs
        fn = self.get_filename(brickname, band, scale)
        if fn is None:
            return None
        return read_tan_wcs(fn, 0)

    def render_into_wcs(self, wcs, zoom, x, y, bands=None, general_wcs=False):
        import numpy as np
        from astrometry.util.resample import resample_with_wcs, OverlapError
        if not general_wcs:
            bricks = self.bricks_touching_aa_wcs(wcs)
        else:
            bricks = self.bricks_touching_general_wcs(wcs)

        if bricks is None or len(bricks) == 0:
            return None
    
        if bands is None:
            bands = self.get_bands()
        scale = self.get_scale(zoom, x, y, wcs)
        print('render_into_wcs: scale', scale, 'N bricks:', len(bricks))
        
        W = wcs.get_width()
        H = wcs.get_height()
        r,d = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                                [1,H/2,H,H,H,H/2,1,1])[-2:]
        rimgs = []
        for band in bands:
            rimg = np.zeros((H,W), np.float32)
            rn   = np.zeros((H,W), np.uint8)
            bricknames = self.bricknames_for_band(bricks, band)
            for brickname in bricknames:
                #print('Reading', brickname, 'band', band, 'scale', scale)
                try:
                    bwcs = self.read_wcs(brickname, band, scale)
                    if bwcs is None:
                        print('No such file:', brickname, band, scale)
                        continue
                except:
                    print('Failed to read WCS:', brickname, band, scale)
                    savecache = False
                    import traceback
                    import sys
                    traceback.print_exc(None, sys.stdout)
                    continue

                # Check for pixel overlap area
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
                    #print('No pixel overlap')
                    continue
    
                subwcs = bwcs.get_subimage(xlo, ylo, xhi-xlo, yhi-ylo)
                slc = slice(ylo,yhi), slice(xlo,xhi)
                try:
                    img = self.read_image(brickname, band, scale, slc)
                except:
                    print('Failed to read image:', brickname, band, scale)
                    savecache = False
                    import traceback
                    import sys
                    traceback.print_exc(None, sys.stdout)
                    continue

                #print('Resampling', img.shape)
                try:
                    Yo,Xo,Yi,Xi,nil = resample_with_wcs(wcs, subwcs, [], 3)
                except OverlapError:
                    debug('Resampling exception')
                    continue
                rimg[Yo,Xo] += img[Yi,Xi]
                rn  [Yo,Xo] += 1
            rimg /= np.maximum(rn, 1)
            rimgs.append(rimg)
        return rimgs

    def get_tile(self, req, ver, zoom, x, y,
                 wcs=None,
                 savecache = None, forcecache = False,
                 return_if_not_found=False,
                 get_images=False,
                 write_jpeg=False,
                 ignoreCached=False,
                 filename=None,
                 bands=None,
                ):
        '''
        *filename*: filename returned in http response
        *wcs*: render into the given WCS rather than zoom/x/y Mercator
        '''
        from decals import settings
        from map.views import tileversions
        if savecache is None:
            savecache = settings.SAVE_CACHE

        zoom = int(zoom)
        zoomscale = 2.**zoom
        x = int(x)
        y = int(y)
        if zoom < 0 or x < 0 or y < 0 or x >= zoomscale or y >= zoomscale:
            raise RuntimeError('Invalid zoom,x,y %i,%i,%i' % (zoom,x,y))

        if ver is not None:
            ver = int(ver)
            if not self.tileversion_ok(ver):
                raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))
        else:
            # Set default version...?
            ver = tileversions[self.name][-1]

        if (not get_images) and (wcs is None):
            tilefn = self.get_tile_filename(ver, zoom, x, y)
            if os.path.exists(tilefn) and not ignoreCached:
                print('Sending tile', tilefn)
                return send_file(tilefn, 'image/jpeg', expires=oneyear,
                                 modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'),
                                 filename=filename)
    
        from astrometry.util.resample import resample_with_wcs, OverlapError
        from astrometry.util.util import Tan
        import numpy as np
        import fitsio
    
        if wcs is None:
            wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)

        rimgs = self.render_into_wcs(wcs, zoom, x, y, bands=bands)
        if rimgs is None:
            if get_images:
                return None
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(settings.STATIC_URL + 'blank.jpg')
    
        if return_if_not_found and not savecache:
            return
        if get_images and not write_jpeg:
            return rimgs
    
        if bands is None:
            bands = self.get_bands()
        rgb = self.get_rgb(rimgs, bands)

        if forcecache:
            savecache = True
        if savecache:
            trymakedirs(tilefn)
        else:
            import tempfile
            f,tilefn = tempfile.mkstemp(suffix='.jpg')
            os.close(f)

        self.write_jpeg(tilefn, rgb)
    
        if get_images:
            return rimgs
    
        return send_file(tilefn, 'image/jpeg', unlink=(not savecache),
                         filename=filename)

    def write_jpeg(self, fn, rgb):
        # no jpeg output support in matplotlib in some installations...
        if self.hack_jpeg:
            save_jpeg(fn, rgb)
            debug('Wrote', fn)
        else:
            import pylab as plt
            plt.imsave(fn, rgb)
            debug('Wrote', fn)

    def get_tile_view(self):
        def view(request, ver, zoom, x, y):
            return self.get_tile(request, ver, zoom, x, y)
        return view

    def populate_fits_cutout_header(self, hdr):
        pass

    def parse_bands(self, bands):
        # default: assume single-character band names
        mybands = self.get_bands()
        bb = []
        for b in bands:
            if b in mybands:
                bb.append(b)
            else:
                return None
        return bb

    def get_cutout(self, req, fits=False, jpeg=False, outtag=None):
        hdr = None
        if fits:
            import fitsio
            hdr = fitsio.FITSHDR()
            self.populate_fits_cutout_header(hdr)

        native_pixscale = self.pixscale
        native_zoom = self.nativescale

        ra  = float(req.GET['ra'])
        dec = float(req.GET['dec'])
        pixscale = float(req.GET.get('pixscale', self.pixscale))
        maxsize = 3000
        size   = min(int(req.GET.get('size',    256)), maxsize)
        width  = min(int(req.GET.get('width',  size)), maxsize)
        height = min(int(req.GET.get('height', size)), maxsize)
        bands = req.GET.get('bands', None)
        #print('get_cutout: GET bands=', bands)

        if not 'pixscale' in req.GET and 'zoom' in req.GET:
            zoom = int(req.GET.get('zoom'))
            pixscale = pixscale * 2**(native_zoom - zoom)
            print('Request has zoom=', zoom, ': setting pixscale=', pixscale)

        if bands is not None:
            bands = self.parse_bands(bands)
            #print('parsed bands:', bands)
        if bands is None:
            bands = self.get_bands()

        #print('get_cutout: bands=', bands)

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

        rtn = self.get_tile(req, None, zoom, 0, 0, wcs=wcs, get_images=fits,
                             savecache=False, bands=bands)
        if jpeg:
            return rtn
        ims = rtn
    
        if hdr is not None:
            hdr['BANDS'] = ''.join([str(b) for b in bands])
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

    def get_jpeg_cutout_view(self):
        def view(request, ver, zoom, x, y):
            return self.get_cutout(request, jpeg=True)
        return view

    def get_fits_cutout_view(self):
        def view(request, ver, zoom, x, y):
            return self.get_cutout(request, fits=True)
        return view

        
class DecalsLayer(MapLayer):
    def __init__(self, name, imagetype, survey, bands='grz', drname=None):
        '''
        name like 'decals-dr2-model'
        imagetype: 'image', 'model', 'resid'
        survey: LegacySurveyData object
        drname like 'decals-dr2'
        '''
        super(DecalsLayer, self).__init__(name)
        self.imagetype = imagetype
        self.survey = survey
        self.rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)
        self.bands = bands
        if drname is None:
            drname = name
        self.drname = drname

    def get_bricks(self):
        B = self.survey.get_bricks_readonly()
        # drop unnecessary columns.
        cols = B.columns()
        for k in ['brickid', 'brickq', 'brickrow', 'brickcol']:
            if k in cols:
                B.delete_column(k)
        return B

    def get_bands(self):
        return self.bands
        
    def bricks_touching_radec_box(self, rlo, rhi, dlo, dhi):
        bricks = self.get_bricks()
        I = self.survey.bricks_touching_radec_box(bricks, rlo, rhi, dlo, dhi)
        if len(I) == 0:
            return None
        return bricks[I]

    def get_scaled_pattern(self):
        from decals import settings
        basedir = settings.DATA_DIR
        return os.path.join(
            basedir, 'scaled', self.drname,
            '%(scale)i%(band)s', '%(brickname).3s',
            self.imagetype + '-%(brickname)s-%(band)s.fits')

    def get_filename(self, brickname, band, scale):
        print('get_filename for', brickname, band, 'scale', scale)
        fn = self.survey.find_file(self.imagetype, brick=brickname, band=band)
        print('get_filename ->', fn)
        if scale == 0:
            return fn
        fnargs = dict(band=band, brickname=brickname)
        fn = get_scaled(self.get_scaled_pattern(), fnargs, scale, fn)
        print('get_filename: scaled ->', fn)
        return fn

    def get_rgb(self, imgs, bands, **kwargs):
        return dr2_rgb(imgs, bands, **self.rgbkwargs)

    def populate_fits_cutout_header(self, hdr):
        hdr['SURVEY'] = 'DECaLS'
        hdr['VERSION'] = self.survey.drname.split(' ')[-1]
        hdr['IMAGETYP'] = self.imagetype

class ResidMixin(object):
    def __init__(self, image_layer, model_layer, *args, **kwargs):
        '''
        image_layer, model_layer: DecalsLayer objects
        '''
        super(ResidMixin, self).__init__(*args, **kwargs)
        self.image_layer = image_layer
        self.model_layer = model_layer
        self.rgbkwargs = dict(mnmx=(-5,5))

    def read_image(self, brickname, band, scale, slc):
        img = self.image_layer.read_image(brickname, band, scale, slc)
        if img is None:
            return None
        mod = self.model_layer.read_image(brickname, band, scale, slc)
        if mod is None:
            return None
        return img - mod

    def read_wcs(self, brickname, band, scale):
        return self.image_layer.read_wcs(brickname, band, scale)

class DecalsResidLayer(ResidMixin, DecalsLayer):
    pass

class MzlsMixin(object):
    def __init__(self, *args, **kwargs):
        super(MzlsMixin, self).__init__(*args, **kwargs)
        self.bands = 'z'

    def get_rgb(self, imgs, bands, **kwargs):
        return mzls_dr3_rgb(imgs, bands, **kwargs)

    def populate_fits_cutout_header(self, hdr):
        hdr['SURVEY'] = 'MzLS'
        hdr['VERSION'] = self.survey.drname.split(' ')[-1]

class MzlsLayer(MzlsMixin, DecalsLayer):
    pass

class MzlsResidLayer(ResidMixin, DecalsLayer):
    pass


class SdssLayer(MapLayer):
    def __init__(self, name):
        super(SdssLayer, self).__init__(name, nativescale=13)
        self.bricks = None
        
    def get_bricks(self):
        if self.bricks is not None:
            return self.bricks
        from decals import settings
        from astrometry.util.fits import fits_table
        basedir = settings.DATA_DIR
        self.bricks = fits_table(os.path.join(basedir, 'bricks-sdssco.fits'),
                                 columns=['brickname', 'ra1', 'ra2',
                                          'dec1', 'dec2'])
        return self.bricks

    def get_bands(self):
        return 'gri'

    def bricks_touching_radec_box(self, ralo, rahi, declo, dechi):
        import numpy as np
        bricks = self.get_bricks()
        if rahi < ralo:
            I, = np.nonzero(np.logical_or(bricks.ra2 >= ralo,
                                          bricks.ra1 <= rahi) *
                            (bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        else:
            I, = np.nonzero((bricks.ra1  <= rahi ) * (bricks.ra2  >= ralo) *
                            (bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        if len(I) == 0:
            return None
        return bricks[I]

    def get_filename(self, brickname, band, scale):
        from decals import settings
        basedir = settings.DATA_DIR
        brickpre = brickname[:3]
        fn = os.path.join(basedir, 'sdssco', 'coadd', brickpre,
                          'sdssco-%s-%s.fits' % (brickname, band))
        if scale == 0:
            return fn
        fnargs = dict(band=band, brickname=brickname)
        fn = get_scaled(self.get_scaled_pattern(), fnargs, scale, fn)
        return fn
    
    def get_scaled_pattern(self):
        from decals import settings
        basedir = settings.DATA_DIR
        return os.path.join(
            basedir, 'scaled', self.name,
            '%(scale)i%(band)s', '%(brickname).3s',
            'sdssco' + '-%(brickname)s-%(band)s.fits')

    def get_rgb(self, imgs, bands, **kwargs):
        return sdss_rgb(imgs, bands)

    def populate_fits_cutout_header(self, hdr):
        hdr['SURVEY'] = 'SDSS'

class UnwiseLayer(MapLayer):
    def __init__(self, name, unwise_dir):
        super(UnwiseLayer, self).__init__(name, nativescale=13)
        self.bricks = None
        self.dir = unwise_dir
        
    def get_bricks(self):
        if self.bricks is not None:
            return self.bricks
        from decals import settings
        from astrometry.util.fits import fits_table
        basedir = settings.DATA_DIR
        self.bricks = fits_table(os.path.join(basedir, 'unwise-bricks.fits'))
        return self.bricks

    def get_bands(self):
        # Note, not 'w1','w2'...
        return '12'

    def bricks_touching_radec_box(self, ralo, rahi, declo, dechi):
        import numpy as np
        bricks = self.get_bricks()
        if rahi < ralo:
            I, = np.nonzero(np.logical_or(bricks.ra2 >= ralo,
                                          bricks.ra1 <= rahi) *
                            (bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        else:
            I, = np.nonzero((bricks.ra1  <= rahi ) * (bricks.ra2  >= ralo) *
                            (bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        if len(I) == 0:
            return None
        return bricks[I]

    def get_filename(self, brickname, band, scale):
        '''
        band: string '1' or '2'
        '''
        assert(band in self.get_bands())
        brickpre = brickname[:3]
        fn = os.path.join(self.dir, brickpre, brickname,
                          'unwise-%s-w%s-img-u.fits' % (brickname, band))
        if scale == 0:
            return fn
        fnargs = dict(band=band, brickname=brickname)
        fn = get_scaled(self.get_scaled_pattern(), fnargs, scale, fn)
        return fn
    
    def get_scaled_pattern(self):
        from decals import settings
        basedir = settings.DATA_DIR
        return os.path.join(
            basedir, 'scaled', self.name,
            #'%(scale)i%(band)s',
            '%(scale)iw%(band)s',
            '%(brickname).3s', 'unwise-%(brickname)s-w%(band)s.fits')
            

    def get_scale(self, zoom, x, y, wcs):
        import numpy as np
        from astrometry.util.starutil_numpy import arcsec_between

        '''Integer scale step (1=binned 2x2, 2=binned 4x4, ...)'''
        if zoom >= self.nativescale:
            return 0

        # Get *actual* pixel scales at the top & bottom
        W,H = wcs.get_width(), wcs.get_height()
        r1,d1 = wcs.pixelxy2radec(W/2., H)[-2:]
        r2,d2 = wcs.pixelxy2radec(W/2., H-1.)[-2:]
        r3,d3 = wcs.pixelxy2radec(W/2., 1.)[-2:]
        r4,d4 = wcs.pixelxy2radec(W/2., 2.)[-2:]
        # Take the min = most zoomed-in
        tilescale = min(arcsec_between(r1,d1, r2,d2), arcsec_between(r3,d3, r4,d4))
        native_pixscale = 2.75
        scale = int(np.floor(np.log2(tilescale / native_pixscale)))
        debug('Zoom:', zoom, 'x,y', x,y, 'Tile pixel scale:', tilescale, 'Scale:',scale)
        scale = np.clip(scale, 0, 7)
        return scale

    def get_rgb(self, imgs, bands, **kwargs):
        return _unwise_to_rgb(imgs, **kwargs)

class ZeaLayer(MapLayer):
    def __init__(self, name, zeamap, stretch=None, vmin=0., vmax=1.,
                 cmap=None):
        super(ZeaLayer, self).__init__(name)
        self.zeamap = zeamap
        self.stretch = stretch
        if cmap is None:
            self.cmap = matplotlib.cm.hot
        else:
            self.cmap = cmap
        self.vmin = vmin
        self.vmax = vmax

    def render_into_wcs(self, wcs, zoom, x, y, bands=None):
        import numpy as np
        xx,yy = np.meshgrid(np.arange(wcs.get_width()), np.arange(wcs.get_height()))
        rr,dd = wcs.pixelxy2radec(1. + xx.ravel(), 1. + yy.ravel())[-2:]
        #print('ZeaLayer rendering: RA range', rr.min(), rr.max(),
        #  'Dec', dd.min(), dd.max())
        # Calling ebv function for historical reasons, works for any ZEA map.
        val = self.zeamap.ebv(rr, dd) 
        val = val.reshape(xx.shape)
        #print('ZeaLayer: map range', val.min(), val.max())
        return [val]

    def get_rgb(self, imgs, bands, **kwargs):
        val = imgs[0]
        if self.stretch is not None:
            val = self.stretch(val)
        rgb = self.cmap((val - self.vmin) / (self.vmax - self.vmin))
        #print('RGB', rgb.shape, rgb.dtype)
        s = rgb.shape
        if len(s) == 3 and s[2] == 4:
            # cut out alpha layer
            rgb = rgb[:,:,:3]
        #print('red range', rgb[:,:,0].min(), rgb[:,:,0].max())
        return rgb

# "PR"
#rgbkwargs=dict(mnmx=(-0.3,100.), arcsinh=1.))

rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)

#rgbkwargs_nexp = dict(mnmx=(0,25), arcsinh=1.,
#                      scales=dict(g=(2,1),r=(1,1),z=(0,1)))

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

            'mzls-dr3-ccds': 'mzls-dr3',

    }.get(name, name)

# get_bricks_in_X...
#     decals = _get_survey('mzls-dr3')
#     B = decals.get_bricks()
#     C = decals.get_ccds_readonly()
#     # CCD radius
#     radius = np.hypot(2048, 4096) / 2. * 0.262 / 3600.
#     # Brick radius
#     radius += np.hypot(0.25, 0.25)/2.
#     I,J,d = match_radec(B.ra, B.dec, C.ra, C.dec, radius * 1.05)
#     for band in 'grz':
#         has = np.zeros(len(B), bool)
#         K = (C.filter[J] == band)
#         has[I[K]] = True
#         B.set('has_%s' % band, has)
#         debug(sum(has), 'bricks have coverage in', band)
# 
#     keep = np.zeros(len(B), bool)
#     keep[I] = True
#     B.cut(keep)
#     B_mzls_dr3 = B
#     B_mzls_dr3.writeto('/tmp/mzls-bricks-in-dr3.fits')


# z-band only B&W images
def mzls_dr3_rgb(rimgs, bands, scales=None,
                 m = 0.02, **stuff):
    import numpy as np
    rgbscales = {'z': 0.4,}
    if scales is not None:
        rgbscales.update(scales)
    assert(bands == 'z')
    assert(len(rimgs) == 1)

    z = rimgs[0] * rgbscales[bands[0]]
    z = np.maximum(0, z + m)
    I = z
    Q = 20
    fI = np.arcsinh(Q * I) / np.sqrt(Q)
    I += (I == 0.) * 1e-6
    Z = fI * z / I
    rgb = np.dstack((Z,Z,Z))
    rgb = np.clip(rgb, 0, 1)
    return rgb

def dr2_rgb(rimgs, bands, **ignored):
    return sdss_rgb(rimgs, bands, scales=dict(g=6.0, r=3.4, z=2.2), m=0.03)

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
        B_dr1j.rename('has_image_r', 'has_r')
        B_dr1j.rename('has_image_z', 'has_z')
        print(len(B_dr1j), 'DR1 bricks with images')

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

from legacypipe.common import LegacySurveyData
class MyLegacySurveyData(LegacySurveyData):
    def get_ccds(self):
        import numpy as np
        dirnm = self.survey_dir
        # plug in a cut version of the CCDs table, if it exists
        cutfn = os.path.join(dirnm, 'ccds-cut.fits')
        if os.path.exists(cutfn):
            from astrometry.util.fits import fits_table
            C = fits_table(cutfn)
        else:
            C = super(MyLegacySurveyData,self).get_ccds()
            # HACK -- cut to photometric & not-blacklisted CCDs.
            C.cut(self.photometric_ccds(C))
            debug('Cut to', len(C), 'photometric CCDs')
            C.cut(self.apply_blacklist(C))
            debug('Cut to', len(C), 'not-blacklisted CCDs')
            for k in [#'date_obs', 'ut', 'airmass',
                      'zpt', 'avsky', 'arawgain', 'ccdnum', 'ccdzpta',
                      'ccdzptb', 'ccdphoff', 'ccdphrms', 'ccdskyrms',
                      'ccdtransp', 'ccdnstar', 'ccdnmatch', 'ccdnmatcha',
                      'ccdnmatchb', 'ccdmdncol', 'expid',]:
                if k in C.columns():
                    C.delete_column(k)
            fn = '/tmp/cut-ccds-%s.fits' % os.path.basename(self.survey_dir)
            C.writeto(fn)
            print('Wrote', fn)
        # Remove trailing spaces...
        C.ccdname = np.array([s.strip() for s in C.ccdname])
        C.camera  = np.array([c.strip() for c in C.camera ])
        return C


surveys = {}
def _get_survey(name=None):
    import numpy as np
    global surveys
    if name is not None:
        name = str(name)
    if name in surveys:
        return surveys[name]

    debug('Creating LegacySurveyData() object for "%s"' % name)
    
    from decals import settings
    basedir = settings.DATA_DIR

    if name in [ 'decals-dr2', 'decals-dr3', 'mobo-dr3', 'mzls-dr3']:
        dirnm = os.path.join(basedir, name)

        if name == 'decals-dr2':
            d = MyLegacySurveyData(survey_dir=dirnm, version='dr2')
        else:
            d = MyLegacySurveyData(survey_dir=dirnm)

        if name == 'decals-dr2':
            d.drname = 'DECaLS DR2'
            d.drurl = 'http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr2/'
        elif name == 'decals-dr3':
            d.drname = 'DECaLS DR3'
            d.drurl = 'http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr3/'
        elif name == 'mobo-dr3':
            d.drname = 'Mosaic+BASS DR3'
            d.drurl = 'http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr3-mobo/'
        elif name == 'mzls-dr3':
            d.drname = 'MzLS DR3'
            d.drurl = 'http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr3-mzls/'

        surveys[name] = d
        return d

    return None
    # if name is None:
    #     name = 'decals-dr1'
    # if name in surveys:
    #     return surveys[name]
    # 
    # assert(name == 'decals-dr1')
    # 
    # dirnm = os.path.join(basedir, 'decals-dr1')
    # d = LegacySurveyData(survey_dir=dirnm, version='dr1')
    # d.drname = 'DECaLS DR1'
    # d.drurl = 'http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr1/'
    # surveys[name] = d
    # 
    # return d

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

    # if name == 'decals-dr1k':
    #     from astrometry.util.fits import fits_table
    #     B = fits_table(os.path.join(settings.DATA_DIR, 'decals-dr1k',
    #                                 'decals-bricks.fits'))
    # elif name == 'decals-dr1n':
    #     from astrometry.util.fits import fits_table
    #     B = fits_table(os.path.join(settings.DATA_DIR,
    #                                 'decals-bricks.fits'))

    D = _get_survey(name=name)
    if B is None:
        B = D.get_bricks_readonly()

    I = D.bricks_touching_radec_box(B, east, west, south, north)
    # Limit result size...
    if len(I) > 10000:
        return HttpResponse(json.dumps(dict(bricks=[])),
                            content_type='application/json')
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

# A cache of kd-trees of CCDs
ccd_cache = {}

def _ccds_touching_box(north, south, east, west, Nmax=None, name=None, survey=None):
    from astrometry.libkd.spherematch import tree_build_radec
    import numpy as np
    global ccd_cache

    if not name in ccd_cache:
        debug('Finding CCDs for name=', name)
        if survey is None:
            survey = _get_survey(name=name)
        CCDs = survey.get_ccds_readonly()
        print('Read CCDs:', CCDs.columns())
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
        ccds.append(dict(name='%s %i-%s-%s' % (c.camera, c.expnum, c.ccdname, c.filter),
                         poly=zip(d, ra2long(r)),
                         color=ccmap[c.filter]))
    return HttpResponse(json.dumps(dict(polys=ccds)), content_type='application/json')

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

def parse_ccd_name(name):
    words = name.split('-')
    #print('Words:', words)
    #assert(len(words) == 3)
    if len(words) == 4:
        # "decam-EXPNUM-CCD-BAND"
        words = words[1:]
    expnum = words[0]
    expnum = int(expnum, 10)
    ccdname = words[1]
    return expnum, ccdname
    
def get_ccd_object(survey, ccd):
    expnum,ccdname = parse_ccd_name(ccd)
    survey = _get_survey(name=survey)
    #
    # import numpy as np
    # allccds = survey.get_ccds_readonly()
    # print('Got', len(allccds), 'CCDs')
    # print('Got', sum(allccds.expnum == expnum), 'matching exposure number')
    # print('CCDnames:', np.unique(allccds.ccdname))
    # allccds.ccdname = np.array([s.strip() for s in allccds.ccdname])
    # print('CCDnames:', np.unique(allccds.ccdname))
    # print('Got', sum(allccds.ccdname == ccdname), 'matching ccdname')
    # print('Got', sum((allccds.ccdname == ccdname) * (allccds.expnum == expnum)),
    #       'matching ccdname & expnum')
    #
    C = survey.find_ccds(expnum=expnum, ccdname=str(ccdname))
    print('Searching for expnum=%i, ccdname="%s" -> %i ccds' % (expnum, ccdname,len(C)))
    assert(len(C) == 1)
    c = C[0]
    #c.about()
    return survey, c

def ccd_detail(req, name, ccd):
    survey, c = get_ccd_object(name, ccd)

    if name in ['decals-dr2', 'decals-dr3', 'mzls-dr3']:
        imgurl = reverse('image_data', args=[name, ccd])
        dqurl  = reverse('dq_data', args=[name, ccd])
        about = '''
<html><body>
CCD %s, image %s, hdu %i; exptime %.1f sec, seeing %.1f arcsec, fwhm %.1f pix
<br />
<ul>
<li>image <a href="%s">%s</a>
<li>data quality (flags) <a href="%s">%s</a>
</ul>
</body></html>
'''
        about = about % (ccd, c.image_filename, c.image_hdu, c.exptime, c.seeing, c.fwhm,
                         imgurl, ccd, dqurl, ccd)

    else:
        about = ('CCD %s, image %s, hdu %i; exptime %.1f sec, seeing %.1f arcsec' %
                 (ccd, c.cpimage, c.cpimage_hdu, c.exptime, c.fwhm*0.262))

    return HttpResponse(about)


def exposure_detail(req, name, exp):
    import numpy as np
    expnum = exp.split('-')[0]
    expnum = int(expnum)
    T = get_exposure_table(name)
    T.cut(T.expnum == expnum)
    t = T[0]
    pixscale = 0.262
    t.about()
    return HttpResponse('Exposure %i, %s band, %.1f sec exposure time, seeing %.2f arcsec, file %s' %
                        (t.expnum, t.filter, t.exptime, t.fwhm * pixscale,
                         t.image_filename))

def nil(req):
    pass

def brick_detail(req, brickname):
    import numpy as np

    name = req.GET.get('layer', 'decals-dr3')
    survey = _get_survey(name)
    #survey = _get_survey(name)
    if survey is None:
        survey = _get_survey('decals-dr3')

    bricks = survey.get_bricks()
    I = np.flatnonzero(brickname == bricks.brickname)
    assert(len(I) == 1)
    brick = bricks[I[0]]

    html = [
        '<html><head><title>%s data for brick %s</title></head>' % (survey.drname, brickname),
        '<body>',
        '<h1>%s data for brick %s:</h1>' % (survey.drname, brickname),
        '<p>Brick bounds: RA [%.4f to %.4f], Dec [%.4f to %.4f]</p>' % (brick.ra1, brick.ra2, brick.dec1, brick.dec2),
        '<ul>',
        '<li><a href="%s/coadd/%s/%s/decals-%s-image.jpg">JPEG image</a></li>' % (survey.drurl, brickname[:3], brickname, brickname),
        '<li><a href="%s/coadd/%s/%s/">Coadded images</a></li>' % (survey.drurl, brickname[:3], brickname),
        '<li><a href="%s/tractor/%s/tractor-%s.fits">Catalog (FITS table)</a></li>' % (survey.drurl, brickname[:3], brickname),
        '</ul>',
        ]

    ccdsfn = survey.find_file('ccds-table', brick=brickname)
    if not os.path.exists(ccdsfn):
        print('No CCDs table:', ccdsfn)
    else:
        from astrometry.util.fits import fits_table
        ccds = fits_table(ccdsfn)
        if len(ccds):
            html.extend(['CCDs overlapping brick:', '<ul>'])
            for ccd in ccds:
                ccdname = '%s %i %s %s' % (ccd.camera.strip(), ccd.expnum, ccd.ccdname.strip(), ccd.filter.strip())
                html.append('<li><a href="%s">%s</a></li>' % (
                        reverse(ccd_detail, args=(name, ccdname.replace(' ','-'))),
                        ccdname))
            html.append('</ul>')

    html.extend([
            '</body></html>',
            ])

    return HttpResponse('\n'.join(html))


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
    
    print('Survey name:', name)
    survey = _get_survey(name)
    CCDs = _ccds_touching_box(north, south, east, west, name=name, survey=survey)
    debug(len(CCDs), 'CCDs')
    print('CCDs:', CCDs.columns())

    CCDs = CCDs[np.lexsort((CCDs.ccdname, CCDs.expnum, CCDs.filter))]

    ccds = []
    for i in range(len(CCDs)):
        c = CCDs[i]
        try:
            c.image_filename = _get_image_filename(c)
            dim = survey.get_image_object(c)
            wcs = dim.get_wcs()
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

    B = survey.get_bricks_readonly()
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
        fn = ccd.image_filename.replace(settings.DATA_DIR + '/', '')
        theurl = url % (domains[i%len(domains)], int(ccd.expnum), ccd.ccdname.strip()) + '?x=%i&y=%i' % (x,y)
        if name is not None:
            theurl += '&name=' + name
        print('CCD columns:', ccd.columns())
        ccdsx.append(('CCD %s %i %s, %.1f sec (x,y = %i,%i)<br/><small>(%s [%i])</small><br/><small>(observed %s @ %s)</small>' %
                      (ccd.filter, ccd.expnum, ccd.ccdname, ccd.exptime, x, y, fn, ccd.image_hdu, ccd.date_obs, ccd.ut), theurl))
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

    # half-size in DECam pixels -- must match cutouts():size
    size = 50
    img,slc,xstart,ystart = _get_image_slice(fn, ccd.image_hdu, x, y, size=size)

    plt.clf()
    import tempfile
    f,jpegfn = tempfile.mkstemp(suffix='.jpg')
    os.close(f)
    mn,mx = np.percentile(img.ravel(), [25, 99])
    save_jpeg(jpegfn, img, origin='lower', cmap='gray',
              vmin=mn, vmax=mx)
    return send_file(jpegfn, 'image/jpeg', unlink=True)



    wfn = fn.replace('ooi', 'oow')
    if not os.path.exists(wfn):
        return HttpResponse('no such image: ' + wfn)

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


def image_data(req, survey, ccd):
    import fitsio
    survey, c = get_ccd_object(survey, ccd)
    im = survey.get_image_object(c)
    fn = im.imgfn
    #dirnm = survey.get_image_dir()
    #fn = os.path.join(dirnm, c.image_filename)
    print('Opening', fn)
    import tempfile
    ff,tmpfn = tempfile.mkstemp(suffix='.fits.gz')
    os.close(ff)
    primhdr = fitsio.read_header(fn)
    pix,hdr = fitsio.read(fn, ext=c.image_hdu, header=True)

    os.unlink(tmpfn)
    fits = fitsio.FITS(tmpfn, 'rw')
    fits.write(None, header=primhdr, clobber=True)
    fits.write(pix,  header=hdr)
    fits.close()
    return send_file(tmpfn, 'image/fits', unlink=True, filename='image-%s.fits.gz' % ccd)

def dq_data(req, survey, ccd):
    import fitsio
    survey, c = get_ccd_object(survey, ccd)
    im = survey.get_image_object(c)
    fn = im.dqfn
    print('Opening', fn)
    import tempfile
    ff,tmpfn = tempfile.mkstemp(suffix='.fits.gz')
    os.close(ff)
    primhdr = fitsio.read_header(fn)
    pix,hdr = fitsio.read(fn, ext=c.image_hdu, header=True)

    os.unlink(tmpfn)
    fits = fitsio.FITS(tmpfn, 'rw')
    fits.write(None, header=primhdr, clobber=True)
    fits.write(pix,  header=hdr)
    fits.close()
    return send_file(tmpfn, 'image/fits', unlink=True, filename='dq-%s.fits.gz' % ccd)


layers = {}
def _get_layer(name, default=None):
    global layers
    if name in layers:
        return layers[name]

    layer = None
    if name == 'sdssco':
        layer = SdssLayer('sdssco')

    elif name in ['decals-dr3', 'decals-dr3-model', 'decals-dr3-resid']:
        survey_dr3 = _get_survey('decals-dr3')
        dr3_image = DecalsLayer('decals-dr3', 'image', survey_dr3)
        dr3_model = DecalsLayer('decals-dr3-model', 'model', survey_dr3,
                                drname='decals-dr3')
        dr3_resid = DecalsResidLayer(dr3_image, dr3_model,
                                     'decals-dr3-resid', 'resid', survey_dr3,
                                     drname='decals-dr3')
        # No disk space for DR3 scale=1 !
        dr3_image.minscale = dr3_model.minscale = dr3_resid.minscale = 2
        
        layers['decals-dr3'] = dr3_image
        layers['decals-dr3-model'] = dr3_model
        layers['decals-dr3-resid'] = dr3_resid
        layer = layers[name]

    elif name in ['decals-dr2', 'decals-dr2-model', 'decals-dr2-resid']:
        survey_dr2 = _get_survey('decals-dr2')
        dr2_image = DecalsLayer('decals-dr2', 'image', survey_dr2)
        dr2_model = DecalsLayer('decals-dr2-model', 'model', survey_dr2,
                                drname='decals-dr2')
        dr2_resid = DecalsResidLayer(dr2_image, dr2_model,
                                     'decals-dr2-resid', 'resid', survey_dr2,
                                     drname='decals-dr2')
        layers['decals-dr2'] = dr2_image
        layers['decals-dr2-model'] = dr2_model
        layers['decals-dr2-resid'] = dr2_resid
        layer = layers[name]

    elif name in ['mzls-dr3', 'mzls-dr3-model', 'mzls-dr3-resid']:

        survey_dr3mzls = _get_survey('mzls-dr3')
        mzls3_image = MzlsLayer('mzls-dr3', 'image', survey_dr3mzls,
                                drname='mzls-dr3')
        mzls3_model = MzlsLayer('mzls-dr3-model', 'model', survey_dr3mzls,
                                drname='mzls-dr3')
        mzls3_resid = MzlsResidLayer(mzls3_image, mzls3_model,
                                     'mzls-dr3-resid', 'resid', survey_dr3mzls,
                                     drname='mzls-dr3')
        layers['mzls-dr3'] = mzls3_image
        layers['mzls-dr3-model'] = mzls3_model
        layers['mzls-dr3-resid'] = mzls3_resid
        layer = layers[name]

    elif name == 'unwise-w1w2':
        from decals import settings
        layer = UnwiseLayer('unwise-w1w2',
                            settings.UNWISE_DIR)
    elif name == 'unwise-neo1':
        from decals import settings
        layer = UnwiseLayer('unwise-neo1',
                            settings.UNWISE_NEO1_DIR)

    elif name == 'halpha':
        from tractor.sfd import SFDMap
        from decals import settings
        halpha = SFDMap(
            ngp_filename=os.path.join(settings.HALPHA_DIR,'Halpha_4096_ngp.fits'),
            sgp_filename=os.path.join(settings.HALPHA_DIR,'Halpha_4096_sgp.fits'))
        # Doug says: np.log10(halpha + 5) stretched to 0.5 to 2.5
        def stretch_halpha(x):
            import numpy as np
            return np.log10(x + 5)
        layer = ZeaLayer('halpha', halpha, stretch=stretch_halpha,
                         vmin=0.5, vmax=2.5)

    elif name == 'sfd':
        from tractor.sfd import SFDMap
        from decals import settings
        sfd_map = SFDMap(dustdir=settings.DUST_DIR)
        def stretch_sfd(x):
            import numpy as np
            return np.arcsinh(x * 10.)
        layer = ZeaLayer('sfd', sfd_map, stretch=stretch_sfd, vmin=0.0, vmax=5.0)



    if layer is None:
        return default
    layers[name] = layer
    return layer

def get_tile_view(name):
    def view(request, ver, zoom, x, y):
        layer = _get_layer(name)
        return layer.get_tile(request, ver, zoom, x, y)
    return view

def sdss_wcs(req):
    from astrometry.util.util import Tan,Sip
    import numpy as np
    wcs = Tan(*[float(req.GET.get(k)) for k in ['crval1','crval2','crpix1','crpix2',
                                                'cd11','cd12','cd21','cd22','imagew','imageh']])
    print('wcs:', wcs)
    pixscale = wcs.pixel_scale()
    zoom = 13 - int(np.ceil(np.log2(pixscale / 0.396)))
    x = y = 0

    sdss = _get_layer('sdssco')

    rimgs = sdss.render_into_wcs(wcs, zoom, x, y, general_wcs=True)
    if rimgs is None:
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(settings.STATIC_URL + 'blank.jpg')
    bands = sdss.get_bands()
    rgb = sdss.get_rgb(rimgs, bands)
    
    import tempfile
    f,tilefn = tempfile.mkstemp(suffix='.jpg')
    os.close(f)
    sdss.write_jpeg(tilefn, rgb)
    return send_file(tilefn, 'image/jpeg', unlink=True)

if __name__ == '__main__':
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'
    import django

    class duck(object):
        pass



    req = duck()
    req.META = dict()
    req.GET = dict()
    req.GET['wcs'] = '{"imageh": 2523.0, "crval2": 30.6256920573, "crpix1": 1913.90799288, "crpix2": 1288.18061444, "crval1": 23.4321763196, "cd22": 2.68116215986e-05, "cd21": -0.000375943381269, "cd12": 0.000376062675113, "cd11": 2.6797256038e-05, "imagew": 3770.0}'
    sdss_wcs(req)

    import sys
    sys.exit(0)
    
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
