from __future__ import print_function
if __name__ == '__main__':
    ## NOTE, if you want to run this from the command-line, probably have to do so
    # from sgn04 node within the virtualenv.
    import sys
    sys.path.insert(0, 'django-1.9')
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'
    import django
    django.setup()
    #print('Django:', django.__file__)
    #print('Version:', django.get_version())

    #from decals import settings
    #settings.ALLOWED_HOSTS += 'testserver'


import os
import sys
import re
from django.http import HttpResponse, StreamingHttpResponse
from django.core.urlresolvers import reverse
from django import forms

from decals import settings
from map.utils import (get_tile_wcs, trymakedirs, save_jpeg, ra2long, ra2long_B,
                       send_file, oneyear)
from map.coadds import get_scaled
from map.cats import get_random_galaxy

import matplotlib
matplotlib.use('Agg')

py3 = (sys.version_info[0] >= 3)


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
    'ps1': [1],

    'sdss2': [1,],

    'eboss': [1,],

    'decaps': [1, 2],
    'decaps-model': [1, 2],
    'decaps-resid': [1, 2],

    'decals-dr5': [1],
    'decals-dr5-model': [1],
    'decals-dr5-resid': [1],

    'mzls+bass-dr4': [1,2],
    'mzls+bass-dr4-model': [1,2],
    'mzls+bass-dr4-resid': [1,2],

    'decals-dr3': [1],
    'decals-dr3-model': [1],
    'decals-dr3-resid': [1],

    'decals-dr2': [1, 2],
    'decals-dr2-model': [1],
    'decals-dr2-resid': [1],

    'unwise-w1w2': [1],
    'unwise-neo2': [1],
    #'unwise-w3w4': [1],

    'cutouts': [1],
    }

galaxycat = None

def index(req, **kwargs):
    host = req.META.get('HTTP_HOST', None)
    #print('Host:', host)
    if host == 'decaps.legacysurvey.org':
        return decaps(req)
    return _index(req, **kwargs)

def _index(req,
           default_layer = 'mzls+bass-dr4',
           default_radec = (None,None),
           default_zoom = 13,
           rooturl=settings.ROOT_URL,
           **kwargs):
    kwkeys = dict(
        enable_sql = settings.ENABLE_SQL,
        enable_vcc = settings.ENABLE_VCC,
        enable_wl = settings.ENABLE_WL,
        enable_cutouts = settings.ENABLE_CUTOUTS,
        enable_dr2 = settings.ENABLE_DR2,
        enable_dr3 = settings.ENABLE_DR3,
        enable_dr4 = settings.ENABLE_DR4,
        enable_dr5 = settings.ENABLE_DR5,
        enable_decaps = settings.ENABLE_DECAPS,
        enable_ps1 = settings.ENABLE_PS1,
        enable_dr3_models = settings.ENABLE_DR3,
        enable_dr3_resids = settings.ENABLE_DR3,
        enable_dr4_models = settings.ENABLE_DR4,
        enable_dr4_resids = settings.ENABLE_DR4,
        enable_dr5_models = settings.ENABLE_DR5,
        enable_dr5_resids = settings.ENABLE_DR5,
        enable_dr2_overlays = settings.ENABLE_DR2,
        enable_dr3_overlays = settings.ENABLE_DR3,
        enable_dr4_overlays = settings.ENABLE_DR4,
        enable_dr5_overlays = settings.ENABLE_DR5,
        enable_eboss = settings.ENABLE_EBOSS,
        enable_desi_targets = True,
        enable_spectra = True,
        maxNativeZoom = settings.MAX_NATIVE_ZOOM,
    )

    for k in kwargs.keys():
        if not k in kwkeys:
            raise RuntimeError('unknown kwarg "%s" in map.index()' % k)
    for k,v in kwkeys.items():
        if not k in kwargs:
            kwargs[k] = v
    
    from map.cats import cat_user

    layer = req.GET.get('layer', default_layer)
    # Nice spiral galaxy
    #ra, dec, zoom = 244.7, 7.4, 13
    #print('Layer:', layer)
    layer = layer_name_map(layer)

    ra, dec = default_radec
    zoom = default_zoom

    try:
        zoom = int(req.GET.get('zoom', zoom))
    except:
        pass
    try:
        ra,dec = parse_radec_strings(req.GET.get('ra'), req.GET.get('dec'))
    except:
        pass

    try:
        brickname = req.GET.get('brick')
        brick_regex = r'(\d{4}[pm]\d{3})'
        if re.match(brick_regex, brickname) is not None:
            ra = 0.1 * int(brickname[:4], 10)
            dec = 0.1 * int(brickname[-3:], 10)
            pm = (1. if brickname[4] == 'p' else -1.)
            dec *= pm
    except:
        pass

    galname = None
    if ra is None or dec is None:
        ra,dec,galname = get_random_galaxy(layer=layer)

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
            m = re.match('(?P<fn>\w+)(-n(?P<name>\w+))?(-c(?P<color>\w+))?', cat)
            if m is None:
                print('Usercatalog "%s" did not match regex' % cat)
                continue
            fn = m.group('fn')
            name = m.group('name')
            if name is None:
                name = fn
            color = m.group('color')
            if color is None:
                color = ''
            keepcats.append((fn, name, color))
        usercats = keepcats
        if len(usercats) == 0:
            usercats = None
    print('User catalogs:', usercats)
    usercatalogurl = reverse(cat_user, args=(1,)) + '?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&cat={cat}'
    usercatalogurl2 = reverse(cat_user, args=(1,)) + '?start={start}&N={N}&cat={cat}'

    
    absurl = req.build_absolute_uri(rooturl)

    args = dict(ra=ra, dec=dec, zoom=zoom,
                galname=galname,
                layer=layer, tileurl=tileurl,
                absurl=absurl,
                sqlurl=sqlurl,
                uploadurl=uploadurl,
                caturl=caturl, bricksurl=bricksurl,
                smallcaturl=smallcaturl,
                namequeryurl=namequeryurl,
                ccdsurl=ccdsurl,
                expsurl=expsurl,
                platesurl=platesurl,
                static_tile_url=static_tile_url,
                subdomains=subdomains,

                static_tile_url_B=static_tile_url_B,
                subdomains_B=subdomains_B,

                usercatalogs = usercats,
                usercatalogurl = usercatalogurl,
                usercatalogurl2 = usercatalogurl2,
    )

    args.update(kwargs)
    
    from django.shortcuts import render
    # (it's not supposed to be **args, trust me)
    return render(req, 'index.html', args)


def decaps(req):
    return _index(req, enable_decaps=True,
                 enable_dr3_models=False,
                 enable_dr3_resids=False,
                 enable_dr4_models=False,
                 enable_dr4_resids=False,
                 enable_dr5_models=False,
                 enable_dr5_resids=False,
                 enable_dr3=False,
                 enable_dr5=True,
                 enable_ps1=False,
                 enable_dr3_overlays=False,
                 enable_dr4_overlays=False,
                 enable_dr5_overlays=False,
                 enable_desi_targets=False,
                 enable_spectra=False,
                 default_layer='decaps',
                 default_radec=(225.0, -63.2),
                 default_zoom=10,
                 rooturl=settings.ROOT_URL + '/decaps',
    )

def dr5(req):
    return _index(req, enable_decaps=True,
                 enable_ps1=False,
                 enable_desi_targets=True,
                 default_layer='decals-dr5',
                 default_radec=(234.7, 13.6),
                 rooturl=settings.ROOT_URL + '/dr5',
    )

def name_query(req):
    import json

    try:
        # py2
        from urllib2 import urlopen
        from urllib import urlencode
    except:
        # py3
        from urllib.request import urlopen
        from urllib.parse import urlencode

    obj = req.GET.get('obj')
    #print('Name query: "%s"' % obj)

    if len(obj) == 0:
        layer = req.GET.get('layer', None)
        if layer is not None:
            layer = layer_name_map(layer)
        
        ra,dec,name = get_random_galaxy(layer=layer)
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

    url = 'http://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame/NSV?'
    url += urlencode(dict(q=obj)).replace('q=','')
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
        f = urlopen(url)
        code = f.getcode()
        print('Code', code)
        for line in f.readlines():
            if py3:
                line = line.decode()
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

ccds_table_css = '''<style type="text/css">
.ccds { text-align: center; border-bottom: 2px solid #6678b1; margin: 15px; }
.ccds td { padding: 5px; }
.ccds th { border-bottom: 2px solid #6678b1; }
</style>'''

html_tag = '''<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<link rel="icon" type="image/png" href="%s/favicon.png" />
<link rel="shortcut icon" href="%s/favicon.ico" />
''' % (settings.STATIC_URL, settings.STATIC_URL)

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

    brick_html,ccds = brick_detail(req, brickname, get_html=True)
    html = brick_html

    if ccds is not None and len(ccds):
        from legacypipe.survey import wcs_for_brick
        brickwcs = wcs_for_brick(bricks[I])
        ok,bx,by = brickwcs.radec2pixelxy(ra, dec)
        print('Brick x,y:', bx,by)
        ccds.cut((bx >= ccds.brick_x0) * (bx <= ccds.brick_x1) *
                 (by >= ccds.brick_y0) * (by <= ccds.brick_y1))
        print('Cut to', len(ccds), 'CCDs containing RA,Dec point')

        html = [html_tag + '<head><title>%s data for RA,Dec (%.4f, %.4f)</title></head>' %
                (survey.drname, ra, dec),
                ccds_table_css + '<body>',
                '<h1>%s data for RA,Dec = (%.4f, %.4f): CCDs overlapping</h1>' %
                (survey.drname, ra, dec)]
        html.extend(ccds_overlapping_html(ccds, name))
        html = html + brick_html[1:]

    return HttpResponse('\n'.join(html))


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
        self.hack_jpeg = True
        self.pixscale = 0.262

        self.basedir = os.path.join(settings.DATA_DIR, self.name)
        self.tiledir = os.path.join(settings.DATA_DIR, 'tiles', self.name)
        self.scaleddir = os.path.join(settings.DATA_DIR, 'scaled', self.name)

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
        tilefn = os.path.join(self.tiledir,
                              '%i' % ver, '%i' % zoom, '%i' % x, '%i.jpg' % y)
        return tilefn

    def get_scale(self, zoom, x, y, wcs):
        import numpy as np
        from astrometry.util.starutil_numpy import arcsec_between

        '''Integer scale step (1=binned 2x2, 2=binned 4x4, ...)'''

        # # previously used value:
        # if zoom >= self.nativescale:
        #     oldscale = 0
        # else:
        #     oldscale = (self.nativescale - zoom)
        #     oldscale = np.clip(oldscale, self.minscale, self.maxscale)
        # 
        if zoom >= self.nativescale:
            #     print('Old scale', oldscale, 'scale 0 -- zoom', zoom, 'native scale', self.nativescale)
            return 0

        # Get *actual* pixel scales at the top & bottom
        W,H = wcs.get_width(), wcs.get_height()
        r1,d1 = wcs.pixelxy2radec(W/2., H)[-2:]
        r2,d2 = wcs.pixelxy2radec(W/2., H-1.)[-2:]
        r3,d3 = wcs.pixelxy2radec(W/2., 1.)[-2:]
        r4,d4 = wcs.pixelxy2radec(W/2., 2.)[-2:]
        # Take the min = most zoomed-in
        tilescale = min(arcsec_between(r1,d1, r2,d2), arcsec_between(r3,d3, r4,d4))
        native_pixscale = self.pixscale
        scale = int(np.floor(np.log2(tilescale / native_pixscale)))
        debug('Zoom:', zoom, 'x,y', x,y, 'Tile pixel scale:', tilescale, 'Scale:',scale)
        scale = np.clip(scale, 0, 7)
        #print('Old scale', oldscale, 'scale', scale)
        return scale

    def bricks_touching_aa_wcs(self, wcs, scale=None):
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
        return self.bricks_touching_radec_box(rlo, rhi, dlo, dhi, scale=scale)

    def bricks_touching_general_wcs(self, wcs, scale=None):
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
            allbricks.append(self.bricks_touching_radec_box(0., r+dra, d-rad, d+rad,
                                                            scale=scale))
            allbricks.append(self.bricks_touching_radec_box(r-dra+360., 360., d-rad, d+rad,
                                                            scale=scale))
        # Near RA=360 boundary?
        elif r + dra > 360.:
            allbricks.append(self.bricks_touching_radec_box(r-dra, 360., d-rad, d+rad,
                                                            scale=scale))
            allbricks.append(self.bricks_touching_radec_box(0., r+dra-360., d-rad, d+rad,
                                                            scale=scale))
        else:
            allbricks.append(self.bricks_touching_radec_box(r-dra, r+dra, d-rad, d+rad,
                                                            scale=scale))

        allbricks = [b for b in allbricks if b is not None]
        allbricks = [b for b in allbricks if len(b) > 0]
        if len(allbricks) == 0:
            return None
        if len(allbricks) == 1:
            return allbricks[0]
        # append
        from astrometry.util.fits import merge_tables
        return merge_tables(allbricks)

    def bricks_touching_radec_box(self, rlo, rhi, dlo, dhi, scale=None):
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

    def get_filename(self, brick, band, scale, tempfiles=None):
        if scale == 0:
            return self.get_base_filename(brick, band)
        fn = self.get_scaled_filename(brick, band, scale)
        if os.path.exists(fn):
            return fn
        fn = self.create_scaled_image(brick, band, scale, fn, tempfiles=tempfiles)
        if fn is None:
            return None
        if os.path.exists(fn):
            return fn
        return None

    def create_scaled_image(self, brick, band, scale, fn, tempfiles=None):
        from scipy.ndimage.filters import gaussian_filter
        import fitsio
        import tempfile
        import numpy as np
        
        # Read scale-1 image and scale it
        sourcefn = self.get_filename(brick, band, scale-1)
        if sourcefn is None or not os.path.exists(sourcefn):
            print('Image source file', sourcefn, 'not found')
            return None
        img = self.read_image(brick, band, scale-1, None, fn=sourcefn)
        wcs = self.read_wcs(brick, band, scale-1, fn=sourcefn)

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
        # include the even size clip; this may be a no-op
        H,W = img.shape
        wcs = wcs.get_subimage(0, 0, W, H)
        wcs2 = wcs.scale(0.5)

        dirnm = os.path.dirname(fn)
        ro = settings.READ_ONLY_BASEDIR
        if ro:
            dirnm = None
        hdr = fitsio.FITSHDR()
        wcs2.add_to_header(hdr)
        trymakedirs(fn)
        f,tmpfn = tempfile.mkstemp(suffix='.fits.tmp', dir=dirnm)
        os.close(f)
        os.unlink(tmpfn)
        fitsio.write(tmpfn, I2, header=hdr, clobber=True)
        if not ro:
            os.rename(tmpfn, fn)
            debug('Wrote', fn)
        else:
            print('Leaving temp file for get_scaled:', fn, '->', tmpfn)
            # import traceback
            # for line in traceback.format_stack():
            #     print(line.strip())
            if tempfiles is not None:
                tempfiles.append(tmpfn)
            fn = tmpfn
        return fn
        
    def get_base_filename(self, brick, band):
        pass

    def get_scaled_filename(self, brick, band, scale):
        brickname = brick.brickname
        fnargs = dict(band=band, brickname=brickname, scale=scale)
        pat = self.get_scaled_pattern()
        fn = pat % fnargs
        return fn
    
    def get_fits_extension(self, scale, fn):
        return 0
    
    def read_image(self, brick, band, scale, slc, fn=None):
        import fitsio
        if fn is None:
            fn = self.get_filename(brick, band, scale)
        print('Reading image from', fn)
        ext = self.get_fits_extension(scale, fn)
        f = fitsio.FITS(fn)[ext]
        if slc is None:
            return f.read()
        img = f[slc]
        return img

    def read_wcs(self, brick, band, scale, fn=None):
        from map.coadds import read_tan_wcs
        if fn is None:
            fn = self.get_filename(brick, band, scale)
        if fn is None:
            return None
        ext = self.get_fits_extension(scale, fn)
        return read_tan_wcs(fn, ext)

    def render_into_wcs(self, wcs, zoom, x, y, bands=None, general_wcs=False,
                        scale=None, tempfiles=None):
        import numpy as np
        from astrometry.util.resample import resample_with_wcs, OverlapError

        if scale is None:
            scale = self.get_scale(zoom, x, y, wcs)
        if not general_wcs:
            bricks = self.bricks_touching_aa_wcs(wcs, scale=scale)
        else:
            bricks = self.bricks_touching_general_wcs(wcs, scale=scale)

        if bricks is None or len(bricks) == 0:
            print('No bricks touching WCS')
            return None

        if bands is None:
            bands = self.get_bands()
        #print('render_into_wcs: scale', scale, 'N bricks:', len(bricks))

        W = int(wcs.get_width())
        H = int(wcs.get_height())
        r,d = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                                [1,H/2,H,H,H,H/2,1,1])[-2:]

        #print('Render into wcs: RA,Dec points', r, d)

        rimgs = []
        for band in bands:
            rimg = np.zeros((H,W), np.float32)
            rn   = np.zeros((H,W), np.uint8)
            bricknames = self.bricknames_for_band(bricks, band)
            for brick,brickname in zip(bricks,bricknames):
                print('Reading', brickname, 'band', band, 'scale', scale)
                # call get_filename to possibly generate scaled version
                fn = self.get_filename(brick, band, scale, tempfiles=tempfiles)

                try:
                    bwcs = self.read_wcs(brick, band, scale, fn=fn)
                    if bwcs is None:
                        print('No such file:', brickname, band, scale, 'fn', fn)
                        continue
                except:
                    print('Failed to read WCS:', brickname, band, scale, 'fn', fn)
                    savecache = False
                    import traceback
                    import sys
                    traceback.print_exc(None, sys.stdout)
                    continue

                # Check for pixel overlap area
                ok,xx,yy = bwcs.radec2pixelxy(r, d)
                xx = xx.astype(np.int)
                yy = yy.astype(np.int)

                #print('Brick', brickname, 'band', band, 'shape', bwcs.shape,
                #      'pixel coords', xx, yy)

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
                    img = self.read_image(brick, band, scale, slc, fn=fn)
                except:
                    print('Failed to read image:', brickname, band, scale, 'fn', fn)
                    savecache = False
                    import traceback
                    import sys
                    traceback.print_exc(None, sys.stdout)
                    continue

                #print('Resampling', img.shape)
                try:
                    Yo,Xo,Yi,Xi,nil = resample_with_wcs(wcs, subwcs, [], 3)
                except OverlapError:
                    #debug('Resampling exception')
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
                 tempfiles=None,
                ):
        '''
        *filename*: filename returned in http response
        *wcs*: render into the given WCS rather than zoom/x/y Mercator
        '''
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
                raise RuntimeError('Invalid tile version %i for %s' % (ver, str(self)))
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

        # ok,ra,dec = wcs.pixelxy2radec([1, W/2, W, W, W, W/2, 1, 1],
        #                            [1, 1, 1, H/2, H, H, H, H/2])
        # print('WCS range: RA', ra.min(), ra.max(), 'Dec', dec.min(), dec.max())
            
        rimgs = self.render_into_wcs(wcs, zoom, x, y, bands=bands, tempfiles=tempfiles)
        #print('rimgs:', rimgs)
        if rimgs is None:
            if get_images:
                return None
            if return_if_not_found and not forcecache:
                return
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(settings.STATIC_URL + 'blank.jpg')
    
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
        def view(request, ver, zoom, x, y, **kwargs):
            return self.get_tile(request, ver, zoom, x, y, **kwargs)
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

    def get_cutout(self, req, fits=False, jpeg=False, outtag=None, tempfiles=None):
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

        # For retrieving a single-CCD cutout, not coadd
        #ccd = req.GET.get('ccd', None)
        #decam-432057-S26

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
                             savecache=False, bands=bands, tempfiles=tempfiles)
        if jpeg:
            return rtn
        ims = rtn
        if ims is None:
            # ...?
            print('ims is None')
    
        if hdr is not None:
            hdr['BANDS'] = ''.join([str(b) for b in bands])
            for i,b in enumerate(bands):
                hdr['BAND%i' % i] = b
            wcs.add_to_header(hdr)

        if ims is None:
            hdr['OVERLAP'] = False
            cube = None
        elif len(bands) > 1:
            cube = np.empty((len(bands), height, width), np.float32)
            for i,im in enumerate(ims):
                cube[i,:,:] = im
        else:
            cube = ims[0]
        del ims

        f,tmpfn = tempfile.mkstemp(suffix='.fits')
        os.close(f)
        os.unlink(tmpfn)
        fitsio.write(tmpfn, cube, clobber=True, header=hdr)
        if outtag is None:
            fn = 'cutout_%.4f_%.4f.fits' % (ra,dec)
        else:
            fn = 'cutout_%s_%.4f_%.4f.fits' % (outtag, ra,dec)
        return send_file(tmpfn, 'image/fits', unlink=True, filename=fn)

    # Note, see cutouts.py : jpeg_cutout, which calls get_cutout directly!
    def get_jpeg_cutout_view(self):
        def view(request, ver, zoom, x, y):
            tempfiles = []
            rtn = self.get_cutout(request, jpeg=True, tempfiles=tempfiles)
            for fn in tempfiles:
                print('Deleting temp file', fn)
                os.unlink(fn)
            return rtn
        return view

    def get_fits_cutout_view(self):
        def view(request, ver, zoom, x, y):
            tempfiles = []
            rtn = self.get_cutout(request, fits=True, tempfiles=tempfiles)
            for fn in tempfiles:
                print('Deleting temp file', fn)
                os.unlink(fn)
            return rtn
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

        self.basedir = os.path.join(settings.DATA_DIR, self.drname)
        self.scaleddir = os.path.join(settings.DATA_DIR, 'scaled', self.drname)

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
        
    def bricks_touching_radec_box(self, rlo, rhi, dlo, dhi, scale=None):
        bricks = self.get_bricks()
        I = self.survey.bricks_touching_radec_box(bricks, rlo, rhi, dlo, dhi)
        if len(I) == 0:
            return None
        return bricks[I]

    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
            '%(scale)i%(band)s', '%(brickname).3s',
            self.imagetype + '-%(brickname)s-%(band)s.fits')

    def get_base_filename(self, brick, band):
        brickname = brick.brickname
        return self.survey.find_file(self.imagetype, brick=brickname, band=band)
    
    def get_rgb(self, imgs, bands, **kwargs):
        return dr2_rgb(imgs, bands, **self.rgbkwargs)

    def populate_fits_cutout_header(self, hdr):
        hdr['SURVEY'] = 'DECaLS'
        hdr['VERSION'] = self.survey.drname.split(' ')[-1]
        hdr['IMAGETYP'] = self.imagetype

    def get_fits_extension(self, scale, fn):
        #if scale == 0:
        #    return 1
        if fn.endswith('.fz'):
            return 1
        return 0

class DecalsDr3Layer(DecalsLayer):
    '''The data model changed (added .fz compression) as of DR5; this
    class retrofits pre-DR5 filenames.
    '''
    def get_base_filename(self, brick, band):
        brickname = brick.brickname
        fn = self.survey.find_file(self.imagetype, brick=brickname, band=band)
        if fn is not None:
            if self.imagetype == 'image':
                fn = fn.replace('.fits.fz', '.fits')
            elif self.imagetype == 'model':
                fn = fn.replace('.fits.fz', '.fits.gz')
        return fn

    # Allow fpacked (or not) scaled images.
    def get_scaled_filename(self, brick, band, scale):
        fn = super(DecalsDr3Layer, self).get_scaled_filename(brick, band, scale)
        if not os.path.exists(fn) and os.path.exists(fn + '.fz'):
            return fn + '.fz'
        return fn

    def get_fits_extension(self, scale, fn):
        if fn.endswith('.fz'):
            return 1
        return super(DecalsDr3Layer, self).get_fits_extension(scale, fn)

class RebrickedMixin(object):

    def get_fits_extension(self, scale, fn):
        # Original and scaled images are in ext 1.
        return 1

    def get_filename(self, brick, band, scale, tempfiles=None):
        if scale == 0:
            return super(RebrickedMixin, self).get_filename(brick, band, scale,
                                                            tempfiles=tempfiles)
        brickname = brick.brickname
        fnargs = dict(band=band, brickname=brickname, scale=scale)
        fn = self.get_scaled_pattern() % fnargs
        if not os.path.exists(fn):
            self.create_scaled_image(brick, band, scale, fn, tempfiles=tempfiles)
        if not os.path.exists(fn):
            return None
        return fn

    def get_scaled_pattern(self):
        fn = super(RebrickedMixin, self).get_scaled_pattern()
        if fn.endswith('.fits'):
            fn += '.fz'
        return fn

    def get_scaled_wcs(self, brick, band, scale):
        pass
    
    def create_scaled_image(self, brick, band, scale, fn, tempfiles=None):
        import numpy as np
        from scipy.ndimage.filters import gaussian_filter
        import fitsio
        import tempfile
        
        # Create scaled-down image (recursively).
        #print('Creating scaled-down image for', brick.brickname, band, 'scale', scale)
        # This is a little strange -- we resample into a WCS twice
        # as big but with half the scale of the image we need, then
        # smooth & bin the image and scale the WCS.
        finalwcs = self.get_scaled_wcs(brick, band, scale)
        print('Scaled WCS:', finalwcs)
        wcs = finalwcs.scale(2.)
        print('Double-size WCS:', wcs)
        
        imgs = self.render_into_wcs(wcs, None, 0, 0, bands=[band], scale=scale-1,
                                    tempfiles=tempfiles)
        if imgs is None:
            return None
        img = imgs[0]

        H,W = img.shape
        # make even size
        if H % 2 == 1:
            img = img[:-1,:]
        if W % 2 == 1:
            img = img[:,:-1]
        # smooth
        img = gaussian_filter(img, 1.)
        # bin
        img = (img[::2,::2] + img[1::2,::2] + img[1::2,1::2] + img[::2,1::2])/4.
        img = img.astype(np.float32)
        H,W = img.shape
        # create half-size WCS
        wcs = wcs.get_subimage(0, 0, W*2, H*2)
        wcs = wcs.scale(0.5)
        hdr = fitsio.FITSHDR()
        wcs.add_to_header(hdr)

        # (r1,r2,nil,nil),(nil,nil,d1,d2) = wcs.pixelxy2radec(
        #     [1, size/2, size/4, size/4], [size/4, size/4, 1, size/2,])
        # print('Brick RA1,RA2', brick.ra1, brick.ra2, 'vs WCS', r1, r2)
        # print('  Dec1,Dec2', brick.dec1, brick.dec2, 'vs WCS', d1, d2)
        
        trymakedirs(fn)
        dirnm = os.path.dirname(fn)
        f,tmpfn = tempfile.mkstemp(suffix='.fits.fz.tmp', dir=dirnm)
        os.close(f)
        os.unlink(tmpfn)
        compress = '[compress R 100,100; qz 4]'
        fitsio.write(tmpfn + compress, img, header=hdr, clobber=True)
        os.rename(tmpfn, fn)
        print('Wrote', fn)

    def get_bricks_for_scale(self, scale):
        if scale in [0, None]:
            return self.get_bricks()
        scale = min(scale, 7)

        from astrometry.util.fits import fits_table
        import numpy as np
        from astrometry.libkd.spherematch import match_radec

        fn = os.path.join(self.basedir, 'survey-bricks-%i.fits.gz' % scale)
        print('Brick file:', fn, 'exists?', os.path.exists(fn))
        if os.path.exists(fn):
            return fits_table(fn)
        bsmall = self.get_bricks_for_scale(scale - 1)
        # Find generic bricks for scale...
        afn = os.path.join(settings.DATA_DIR, 'bricks-%i.fits' % scale)
        print('Generic brick file:', afn)
        assert(os.path.exists(afn))
        allbricks = fits_table(afn)
        print('Generic bricks:', len(allbricks))
        
        # Brick side lengths
        brickside = 0.25 * 2**scale
        brickside_small = 0.25 * 2**(scale-1)

        # Spherematch from smaller scale to larger scale bricks
        radius = (brickside + brickside_small) * np.sqrt(2.) / 2. * 1.01

        inds = match_radec(allbricks.ra, allbricks.dec, bsmall.ra, bsmall.dec, radius,
                           indexlist=True)
        keep = []
        for ia,I in enumerate(inds):
            #if (allbricks.dec[ia] > 80):
            #    print('Brick', allbricks.brickname[ia], ': matches', I)
            if I is None:
                continue
            # Check for actual RA,Dec box overlap, not spherematch possible overlap
            good = np.any((bsmall.dec2[I] >= allbricks.dec1[ia]) *
                          (bsmall.dec1[I] <= allbricks.dec2[ia]) *
                          (bsmall.ra2[I] >= allbricks.ra1[ia]) *
                          (bsmall.ra1[I] <= allbricks.ra2[ia]))
            if (allbricks.dec[ia] > 80):
                print('Keep?', good)
            if good:
                keep.append(ia)
        keep = np.array(keep)
        allbricks.cut(keep)
        print('Cut generic bricks to', len(allbricks))
        allbricks.writeto(fn)
        print('Wrote', fn)
        return allbricks

    def bricks_touching_radec_box(self, ralo, rahi, declo, dechi, scale=None):
        import numpy as np
        bricks = self.get_bricks_for_scale(scale)
        #print('Bricks touching RA,Dec box', ralo, rahi, 'Dec', declo, dechi, 'scale', scale)
        # Hacky margin
        m = { 7: 1. }.get(scale, 0.)

        if rahi < ralo:
            I, = np.nonzero(np.logical_or(bricks.ra2 >= ralo,
                                          bricks.ra1 <= rahi) *
                            (bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        else:
            I, = np.nonzero((bricks.ra1  <= rahi +m) * (bricks.ra2  >= ralo -m) *
                            (bricks.dec1 <= dechi+m) * (bricks.dec2 >= declo-m))
        #print('Returning', len(I), 'bricks')
        #for i in I:
        #    print('  Brick', bricks.brickname[i], 'RA', bricks.ra1[i], bricks.ra2[i], 'Dec', bricks.dec1[i], bricks.dec2[i])
        if len(I) == 0:
            return None
        return bricks[I]


        
class Decaps2Layer(DecalsDr3Layer):

    # Some of the DECaPS2 images do not have WCS headers, so create them based on the brick center.
    def read_wcs(self, brick, band, scale, fn=None):
        if scale > 0:
            return super(Decaps2Layer, self).read_wcs(brick, band, scale, fn=fn)
        from legacypipe.survey import wcs_for_brick
        return wcs_for_brick(brick)

    def get_fits_extension(self, scale, fn):
        if scale == 0:
            return 1
        return 0

    # For zoom layers above 13, optionally redirect to NERSC
    def get_tile(self, req, ver, zoom, x, y, **kwargs):
        zoom = int(zoom)
        if (settings.REDIRECT_CUTOUTS_DECAPS and
            zoom > 13):
            from django.http import HttpResponseRedirect
            host = req.META.get('HTTP_HOST')
            #print('Host:', host)
            if host is None:
                host = 'legacysurvey.org'
            else:
                host = host.replace('imagine.legacysurvey.org', 'legacysurvey.org')
            return HttpResponseRedirect('http://' + host + '/viewer' + req.path)
        return super(Decaps2Layer, self).get_tile(req, ver, zoom, x, y, **kwargs)
        
class ResidMixin(object):
    def __init__(self, image_layer, model_layer, *args, **kwargs):
        '''
        image_layer, model_layer: DecalsLayer objects
        '''
        super(ResidMixin, self).__init__(*args, **kwargs)
        self.image_layer = image_layer
        self.model_layer = model_layer
        self.rgbkwargs = dict(mnmx=(-5,5))

    def read_image(self, brick, band, scale, slc, fn=None):
        # Note, we drop the fn arg.
        img = self.image_layer.read_image(brick, band, scale, slc)
        if img is None:
            return None
        mod = self.model_layer.read_image(brick, band, scale, slc)
        if mod is None:
            return None
        return img - mod

    def read_wcs(self, brick, band, scale, fn=None):
        return self.image_layer.read_wcs(brick, band, scale, fn=fn)

    def get_filename(self, brick, band, scale, tempfiles=None):
        mfn = self.model_layer.get_filename(brick, band, scale, tempfiles=tempfiles)
        ifn = self.image_layer.get_filename(brick, band, scale, tempfiles=tempfiles)
        return ifn

class DecalsResidLayer(ResidMixin, DecalsLayer):
    pass

class Decaps2ResidLayer(ResidMixin, Decaps2Layer):
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
        super(SdssLayer, self).__init__(name, nativescale=13, maxscale=6)
        self.pixscale = 0.396
        self.bricks = None
        
    def get_bricks(self):
        if self.bricks is not None:
            return self.bricks
        from astrometry.util.fits import fits_table
        self.bricks = fits_table(os.path.join(self.basedir, 'bricks-sdssco.fits'),
                                 columns=['brickname', 'ra1', 'ra2',
                                          'dec1', 'dec2', 'ra', 'dec'])
        return self.bricks

    def get_bands(self):
        return 'gri'

    def bricks_touching_radec_box(self, ralo, rahi, declo, dechi, scale=None):
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

    def get_filename(self, brick, band, scale, tempfiles=None):
        brickname = brick.brickname
        brickpre = brickname[:3]
        fn = os.path.join(self.basedir, 'coadd', brickpre,
                          'sdssco-%s-%s.fits.fz' % (brickname, band))
        if scale == 0:
            return fn
        fnargs = dict(band=band, brickname=brickname)
        fn = get_scaled(self.get_scaled_pattern(), fnargs, scale, fn)
        return fn
    
    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
            '%(scale)i%(band)s', '%(brickname).3s',
            'sdssco' + '-%(brickname)s-%(band)s.fits')

    def get_rgb(self, imgs, bands, **kwargs):
        return sdss_rgb(imgs, bands)

    def populate_fits_cutout_header(self, hdr):
        hdr['SURVEY'] = 'SDSS'

    # Need to override this function to read WCS from ext 1 of fits.fz files,
    # ext 0 of regular scaled images.
    def get_fits_extension(self, scale, fn):
        if scale == 0:
            return 1
        return 0
    
class ReSdssLayer(RebrickedMixin, SdssLayer):
    def get_scaled_wcs(self, brick, band, scale):
        from astrometry.util.util import Tan
        size = 2400
        pixscale = 0.396 * 2**scale
        cd = pixscale / 3600.
        crpix = size/2. + 0.5
        wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                  float(size), float(size))
        return wcs

class ReDecalsLayer(RebrickedMixin, DecalsLayer):

    def get_scaled_wcs(self, brick, band, scale):
        from astrometry.util.util import Tan
        size = 3600
        pixscale = self.pixscale * 2**scale
        cd = pixscale / 3600.
        crpix = size/2. + 0.5
        wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                  float(size), float(size))
        return wcs

class ReDecalsResidLayer(ResidMixin, ReDecalsLayer):
    pass
    
class PS1Layer(MapLayer):
    def __init__(self, name):
        super(PS1Layer, self).__init__(name, nativescale=14, maxscale=6)
        self.pixscale = 0.25
        self.bricks = None
        self.rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)

    def get_bands(self):
        return 'grz'
        #return 'gri'

    def get_bricks(self):
        if self.bricks is not None:
            return self.bricks
        from astrometry.util.fits import fits_table
        basedir = settings.DATA_DIR
        self.bricks = fits_table(os.path.join(basedir, 'ps1skycells-sub.fits'))
        print('Read', len(self.bricks), 'bricks')
        self.bricks.cut(self.bricks.filter == 'r')
        print('Cut to', len(self.bricks), 'r-band bricks')
        self.bricks.ra += (360. * (self.bricks.ra < 0.))
        self.bricks.ra += (-360. * (self.bricks.ra > 360.))
        # ROUGHLY...
        self.bricks.dec1 = self.bricks.dec - 0.2
        self.bricks.dec2 = self.bricks.dec + 0.2
        import numpy as np
        cosdec = np.cos(np.deg2rad(self.bricks.dec))
        self.bricks.ra1 = self.bricks.ra - 0.2 / cosdec
        self.bricks.ra2 = self.bricks.ra + 0.2 / cosdec
        self.bricks.brickname = np.array(['%04i.%03i' % (c,s) for c,s in zip(self.bricks.projcell, self.bricks.subcell)])
        #self.bricks.writeto('/tmp/ps1.fits')
        return self.bricks

    def bricks_touching_radec_box(self, ralo, rahi, declo, dechi, scale=None):
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

    def get_filename(self, brick, band, scale, tempfiles=None):
        brickname = brick.brickname
        cell = brickname[:4]
        fn = os.path.join(self.basedir, 'skycells', cell,
                          'ps1-%s-%s.fits' % (brickname.replace('.','-'), band))
        if scale == 0:
            return fn
        fnargs = dict(band=band, brickname=brickname)
        def read_base_wcs(sourcefn, hdu, hdr=None, W=None, H=None, fitsfile=None):
            #print('read_base_wcs() for', sourcefn)
            return self.read_wcs(brick, band, 0)
        def read_base_image(sourcefn):
            #print('read_base_image() for', sourcefn)
            return self.read_image(brick, band, 0, None, header=True)
        #print('calling get_scaled: scale', scale)
        fn = get_scaled(self.get_scaled_pattern(), fnargs, scale, fn,
                        read_base_wcs=read_base_wcs, read_base_image=read_base_image)
        #print('get_scaled: fn', fn)
        return fn

    def read_image(self, brick, band, scale, slc, header=False, fn=None):
        #print('read_image for', brickname, 'band', band, 'scale', scale)
        #if scale > 0:
        #    return super(PS1Layer, self).read_image(brickname, band, scale, slc)

        # HDU = 1
        import fitsio
        #print('-> get_filename')
        if fn is None:
            fn = self.get_filename(brick, band, scale)
        #print('-> got filename', fn)

        if scale == 0:
            hdu = 1
        else:
            hdu = 0

        #print('Reading image from', fn)
        F = fitsio.FITS(fn)
        f = F[hdu]
        if slc is None:
            img = f.read()
        else:
            img = f[slc]
        hdr = f.read_header()

        if scale == 0:
            #print('scale == 0; scaling pixels')
            exptime = hdr['EXPTIME']
            import numpy as np
            # print('Exptime:', exptime, 'in band', band, '; image 90th pctile:', np.percentile(img.ravel(), 90))

            # Srsly?
            alpha = 2.5 * np.log10(np.e)
            boff = hdr['BOFFSET']
            bsoft = hdr['BSOFTEN']
            img = boff + bsoft * 2. * np.sinh(img / alpha)

            # print('After linearitity: image 90th pctile:', np.percentile(img.ravel(), 90))

            # Zeropoint of 25 = factor of 10 vs nanomaggies
            img *= 0.1 / exptime

        if header:
            return img,hdr

        return img

    '''
    Obsolete WCS keywords:

    CDELT1  = 6.94444461259988E-05
    CDELT2  = 6.94444461259988E-05
    PC001001=                  -1.
    PC001002=                   0.
    PC002001=                   0.
    PC002002=                   1.
    '''
    def read_wcs(self, brick, band, scale, fn=None):
        #if scale > 0:
        #    return super(PS1Layer, self).read_wcs(brickname, band, scale)
        #print('read_wcs for', brickname, 'band', band, 'scale', scale)

        from map.coadds import read_tan_wcs
        if fn is None:
            fn = self.get_filename(brick, band, scale)
        if fn is None:
            #print('read_wcs: filename is None')
            return None

        #print('read_wcs got fn', fn)
        if scale > 0:
            return read_tan_wcs(fn, 0)

        #print('Handling PS1 WCS for', fn)
        import fitsio
        from astrometry.util.util import Tan
        hdr = fitsio.read_header(fn, 1)

        # PS1 wonky WCS
        cdelt1 = hdr['CDELT1']
        cdelt2 = hdr['CDELT2']
        # ????
        cd11 = hdr['PC001001'] * cdelt1
        cd12 = hdr['PC001002'] * cdelt1
        cd21 = hdr['PC002001'] * cdelt2
        cd22 = hdr['PC002002'] * cdelt2
        H = hdr['ZNAXIS1']
        W = hdr['ZNAXIS2']
        wcs = Tan(*[float(x) for x in [
                    hdr['CRVAL1'], hdr['CRVAL2'], hdr['CRPIX1'], hdr['CRPIX2'],
                    cd11, cd12, cd21, cd22, W, H]])
        return wcs
    
    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
            '%(scale)i%(band)s', '%(brickname).4s',
            'ps1' + '-%(brickname)s-%(band)s.fits')

    def get_rgb(self, imgs, bands, **kwargs):
        return dr2_rgb(imgs, bands, **self.rgbkwargs)
        #return sdss_rgb(imgs, bands)

    #def get_rgb(self, imgs, bands, **kwargs):
    #    return sdss_rgb(imgs, bands)

    def populate_fits_cutout_header(self, hdr):
        hdr['SURVEY'] = 'PS1'


class UnwiseLayer(MapLayer):
    def __init__(self, name, unwise_dir):
        super(UnwiseLayer, self).__init__(name, nativescale=13)
        self.bricks = None
        self.dir = unwise_dir

    def get_bricks(self):
        if self.bricks is not None:
            return self.bricks
        from astrometry.util.fits import fits_table
        basedir = settings.DATA_DIR
        self.bricks = fits_table(os.path.join(basedir, 'unwise-bricks.fits'))
        return self.bricks

    def get_bands(self):
        # Note, not 'w1','w2'...
        return '12'

    def bricks_touching_radec_box(self, ralo, rahi, declo, dechi, scale=None):
        import numpy as np
        bricks = self.get_bricks()
        #print('Unwise bricks touching RA,Dec box', ralo, rahi, declo, dechi)
        I, = np.nonzero((bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        ok = ra_ranges_overlap(ralo, rahi, bricks.ra1[I], bricks.ra2[I])
        I = I[ok]
        #print('-> bricks', bricks.brickname[I])
        if len(I) == 0:
            return None
        return bricks[I]

    def get_base_filename(self, brick, band):
        brickname = brick.brickname
        brickpre = brickname[:3]
        fn = os.path.join(self.dir, brickpre, brickname,
                          'unwise-%s-w%s-img-u.fits' % (brickname, band))
        return fn
    
    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
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
            import matplotlib.cm
            self.cmap = matplotlib.cm.hot
        else:
            self.cmap = cmap
        self.vmin = vmin
        self.vmax = vmax

    def render_into_wcs(self, wcs, zoom, x, y, bands=None, tempfiles=None):
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

            'mzls bass-dr4': 'mzls+bass-dr4',

            'decaps2': 'decaps',
            'decaps2-model': 'decaps-model',
            'decaps2-resid': 'decaps-resid',

    }.get(name, name)

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

from legacypipe.survey import LegacySurveyData
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
            C.photometric = np.zeros(len(C), bool)
            I = self.photometric_ccds(C)
            C.photometric[I] = True

            C.ccd_cuts = self.ccd_cuts(C)

            from legacypipe.survey import LegacySurveyData
            bits = LegacySurveyData.ccd_cut_bits

            C.blacklist_ok = ((C.ccd_cuts & bits['BLACKLIST']) == 0)

            C.good_ccd = C.photometric * (C.ccd_cuts == 0)
            #debug('Cut to', len(C), 'photometric CCDs')
            #C.cut(self.apply_blacklist(C))
            #debug('Cut to', len(C), 'not-blacklisted CCDs')
            for k in [#'date_obs', 'ut', 'arawgain', 
                      'zpt', 'avsky', 'ccdnum', 'ccdzpta',
                      'ccdzptb', 'ccdphoff', 'ccdphrms', 'ccdskyrms',
                      'ccdtransp', 'ccdnstar', 'ccdnmatch', 'ccdnmatcha',
                      'ccdnmatchb', 'ccdmdncol', 'expid']:
                if k in C.columns():
                    C.delete_column(k)
            fn = '/tmp/cut-ccds-%s.fits' % os.path.basename(self.survey_dir)
            C.writeto(fn)
            print('Wrote', fn)
        # Remove trailing spaces...
        C.ccdname = np.array([s.strip() for s in C.ccdname])
        C.camera  = np.array([c.strip() for c in C.camera ])
        return C

class Decaps2LegacySurveyData(MyLegacySurveyData):
    def find_file(self, filetype, brick=None, brickpre=None, band='%(band)s',
                  output=False):
        if brick is None:
            brick = '%(brick)s'
            brickpre = '%(brick).3s'
        else:
            brickpre = brick[:3]
        if output:
            basedir = self.output_dir
        else:
            basedir = self.survey_dir
        if brick is not None:
            codir = os.path.join(basedir, 'coadd', brickpre, brick)
        sname = self.file_prefix
        if filetype == 'model':
            return os.path.join(codir,
                                '%s-%s-%s-%s.fits' % (sname, brick, filetype, band))
        return super(Decaps2LegacySurveyData, self).find_file(filetype, brick=brick,
                                                              brickpre=brickpre,
                                                              band=band,
                                                              output=output)
    
surveys = {}
def _get_survey(name=None):
    import numpy as np
    global surveys
    if name is not None:
        name = str(name)

        # mzls+bass-dr4 in URLs turns the "+" into a " "
        name = name.replace(' ', '+')

    print('Survey name', name)

    if name in surveys:
        print('Cache hit for survey', name)
        return surveys[name]

    debug('Creating LegacySurveyData() object for "%s"' % name)
    
    basedir = settings.DATA_DIR

    if name in [ 'decals-dr2', 'decals-dr3', 'decals-dr5',
                 'mzls+bass-dr4', 'decaps', 'eboss']:
        dirnm = os.path.join(basedir, name)
        print('survey_dir', dirnm)

        if name == 'decals-dr2':
            d = MyLegacySurveyData(survey_dir=dirnm, version='dr2')
        elif name == 'decaps':
            d = Decaps2LegacySurveyData(survey_dir=dirnm)
        else:
            d = MyLegacySurveyData(survey_dir=dirnm)

        if name == 'decals-dr2':
            d.drname = 'DECaLS DR2'
            d.drurl = 'http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr2/'
        elif name == 'decals-dr3':
            d.drname = 'DECaLS DR3'
            d.drurl = 'http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr3/'
        elif name == 'mzls+bass-dr4':
            d.drname = 'MzLS+BASS DR4'
            d.drurl = 'http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr4/'
        elif name == 'decals-dr5':
            d.drname = 'DECaLS DR5'
            d.drurl = 'http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr5/'
        elif name == 'decaps':
            d.drname = 'DECaPS'
            d.drurl = 'http://legacysurvey.org/'
        elif name == 'eboss':
            d.drname = 'eBOSS'
            d.drurl = 'http://legacysurvey.org/'

        print('Caching survey', name)
        surveys[name] = d
        return d

    return None

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
                           radecs=[[b.ra1 - mra, b.dec1 - mdec],
                                   [b.ra1 - mra, b.dec2 + mdec],
                                   [b.ra2 + mra, b.dec2 + mdec],
                                   [b.ra2 + mra, b.dec1 - mdec]]))
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
    from astrometry.libkd.spherematch import tree_open, tree_search_radec
    from astrometry.util.fits import fits_table
    import numpy as np
    global ccd_cache

    print('ccds_touching_box: ccd_cache keys:', ccd_cache.keys())
    
    if not name in ccd_cache:
        debug('Finding CCDs for name:', name)
        if survey is None:
            survey = _get_survey(name=name)

        kdfns = survey.find_file('ccd-kds')
        print('KD filenames:', kdfns)
        if len(kdfns) == 1:
            kdfn = kdfns[0]
            tree = tree_open(kdfn, 'ccds')
            def read_ccd_rows_kd(fn, J):
                return fits_table(fn, rows=J)
            ccd_cache[name] = (tree, read_ccd_rows_kd, kdfn)

        else:
            CCDs = survey.get_ccds_readonly()
            print('Read CCDs:', CCDs.columns())
            tree = tree_build_radec(CCDs.ra, CCDs.dec)
            def read_ccd_rows_table(ccds, J):
                return ccds[J]
            ccd_cache[name] = (tree, read_ccd_rows_table, CCDs)
    tree,readrows,readrows_arg = ccd_cache[name]

    # image size -- DECam
    radius = np.hypot(2048, 4096) * 0.262/3600. / 2.
    # image size -- 90prime
    radius = max(radius, np.hypot(4096,4096) * 0.45 / 3600. / 2.)

    J = _objects_touching_box(tree, north, south, east, west, Nmax=Nmax,
                              radius=radius)
    #return CCDs[J]
    return readrows(readrows_arg, J)

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

    if name == 'sdss':
        '''
        DR8 window_flist, processed...
        T.ra1,T.dec1 = munu_to_radec_deg(T.mu_start, T.nu_start, T.node, T.incl)
        T.ra2,T.dec2 = munu_to_radec_deg(T.mu_end, T.nu_start, T.node, T.incl)
        T.ra3,T.dec3 = munu_to_radec_deg(T.mu_end, T.nu_end, T.node, T.incl)
        T.ra4,T.dec4 = munu_to_radec_deg(T.mu_start, T.nu_end, T.node, T.incl)
        '''
        from astrometry.libkd.spherematch import tree_open, tree_search_radec
        from astrometry.util.starutil import radectoxyz, xyztoradec, degrees_between
        from astrometry.util.fits import fits_table
        x1,y1,z1 = radectoxyz(east, north)
        x2,y2,z2 = radectoxyz(west, south)
        rc,dc = xyztoradec((x1+x2)/2., (y1+y2)/2., (z1+z2)/2.)
        # 0.15: SDSS field radius is ~ 0.13
        radius = 0.15 + degrees_between(east, north, west, south)/2.
        fn = os.path.join(settings.DATA_DIR, 'sdss', 'sdss-fields-trimmed.kd.fits')
        kd = tree_open(fn, 'ccds')
        I = tree_search_radec(kd, rc, dc, radius)
        print(len(I), 'CCDs within', radius, 'deg of RA,Dec (%.3f, %.3f)' % (rc,dc))
        if len(I) == 0:
            return HttpResponse(json.dumps(dict(polys=[])),
                                content_type='application/json')
        # Read only the CCD-table rows within range.
        T = fits_table(fn, rows=I)
        ccds = [dict(name='SDSS R/C/F %i/%i/%i' % (t.run, t.camcol, t.field),
                     radecs=[[t.ra1,t.dec1],[t.ra2,t.dec2],
                             [t.ra3,t.dec3],[t.ra4,t.dec4]],)
                     #run=int(t.run), camcol=int(t.camcol), field=int(t.field))
                for t in T]
        return HttpResponse(json.dumps(dict(polys=ccds)), content_type='application/json')

    CCDS = _ccds_touching_box(north, south, east, west, Nmax=10000, name=name)
    print('CCDs in box for', name, ':', len(CCDS))
    if 'good_ccd' in CCDS.columns():
        CCDS.cut(CCDS.good_ccd)
        print('Good CCDs in box for', name, ':', len(CCDS))
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
        ccds.append(dict(name='%s %i-%s-%s' % (c.camera.strip(), c.expnum,
                                               c.ccdname.strip(), c.filter.strip()),
                         radecs=list(zip(r, d)),
                         color=ccmap[c.filter]))
    return HttpResponse(json.dumps(dict(polys=ccds)), content_type='application/json')

def get_exposure_table(name):
    from astrometry.util.fits import fits_table
    name = str(name)
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
    elif name == 'decals-dr5':
        fn = os.path.join(settings.DATA_DIR, name, 'exposures.fits')
        if not os.path.exists(fn):
            import numpy as np
            survey = _get_survey(name)
            ccds = survey.get_ccds_readonly()
            e,I = np.unique(ccds.expnum, return_index=True)
            exps = ccds[I]
            exps.ra  = exps.ra_bore
            exps.dec = exps.dec_bore
            ## hack -- should average
            exps.zpt = exps.ccdzpt
            # DECam
            exps.seeing = exps.fwhm * 0.262
            print('Exposures: columns', exps.columns())
            # no airmass in dr5 kd-tree file
            exps.writeto('/tmp/exposures-%s.fits' % name,
                         columns=['ra','dec','expnum','seeing','propid','fwhm','zpt',
                                  'exptime','date_obs','ut','filter','mjd_obs',
                                  'image_filename'])
            T = exps
        else:
            T = fits_table(fn)
    else:
        T = fits_table(os.path.join(settings.DATA_DIR, 'decals-exposures-dr1.fits'))
    return T

exposure_cache = {}

def exposure_list(req):
    import json
    from astrometry.util.fits import fits_table
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
        plates.append(dict(name='%i' % t.plate,
                           ra=t.ra, dec=t.dec, radius=radius,
                           color='#ffffff'))

    return HttpResponse(json.dumps(dict(objs=plates)),
                        content_type='application/json')

def parse_ccd_name(name):
    words = name.split('-')
    #print('Words:', words)
    #assert(len(words) == 3)
    if len(words) == 4:
        # "decam-EXPNUM-CCD-BAND", mabye
        words = words[1:]
    elif len(words) == 3:
        # "decam-EXPNUM-CCD", maybe
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

    if name in ['decals-dr2', 'decals-dr3', 'mzls+bass-dr4', 'decals-dr5']:
        imgurl = reverse('image_data', args=[name, ccd])
        dqurl  = reverse('dq_data', args=[name, ccd])
        ivurl  = reverse('iv_data', args=[name, ccd])
        imgstamp = reverse('image_stamp', args=[name, ccd])
        flags = ''
        cols = c.columns()
        if 'photometric' in cols and 'blacklist_ok' in cols:
            flags = 'Photometric: %s.  Not-blacklisted: %s<br />' % (c.photometric, c.blacklist_ok)
        about = html_tag + '''
<body>
CCD %s, image %s, hdu %i; exptime %.1f sec, seeing %.1f arcsec, fwhm %.1f pix, band %s, RA,Dec <a href="%s/?ra=%.4f&dec=%.4f">%.4f, %.4f</a>
<br />
%s
Observed MJD %.3f, %s %s UT
<ul>
<li>image: <a href="%s">%s</a>
<li>weight or inverse-variance: <a href="%s">%s</a>
<li>data quality (flags): <a href="%s">%s</a>
</ul>
<img src="%s" />
</body></html>
'''
        args = (ccd, c.image_filename.strip(), c.image_hdu, c.exptime, c.seeing, c.fwhm,
                c.filter, settings.ROOT_URL, c.ra, c.dec, c.ra, c.dec,
                flags,
                c.mjd_obs, c.date_obs, c.ut,
                imgurl, ccd, ivurl, ccd, dqurl, ccd, imgstamp)
        about = about % args

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

def brick_detail(req, brickname, get_html=False):
    import numpy as np

    brickname = str(brickname)
    name = req.GET.get('layer', 'decals-dr3')
    survey = _get_survey(name)
    #survey = _get_survey(name)
    if survey is None:
        survey = _get_survey('decals-dr3')

    bricks = survey.get_bricks()
    I = np.flatnonzero(brickname == bricks.brickname)
    assert(len(I) == 1)
    brick = bricks[I[0]]

    coadd_prefix = 'legacysurvey'

    html = [
        html_tag + '<head><title>%s data for brick %s</title></head>' %
        (survey.drname, brickname)
        + ccds_table_css + '<body>',
        '<h1>%s data for brick %s:</h1>' % (survey.drname, brickname),
        '<p>Brick bounds: RA [%.4f to %.4f], Dec [%.4f to %.4f]</p>' % (brick.ra1, brick.ra2, brick.dec1, brick.dec2),
        '<ul>',
        '<li><a href="%scoadd/%s/%s/%s-%s-image.jpg">JPEG image</a></li>' % (survey.drurl, brickname[:3], brickname, coadd_prefix, brickname),
        '<li><a href="%scoadd/%s/%s/">Coadded images</a></li>' % (survey.drurl, brickname[:3], brickname),
        '<li><a href="%stractor/%s/tractor-%s.fits">Catalog (FITS table)</a></li>' % (survey.drurl, brickname[:3], brickname),
        '</ul>',
        ]

    ccdsfn = survey.find_file('ccds-table', brick=brickname)
    if not os.path.exists(ccdsfn):
        print('No CCDs table:', ccdsfn)
        ccds = None
    else:
        from astrometry.util.fits import fits_table
        ccds = fits_table(ccdsfn)
        ccds = touchup_ccds(ccds, survey)

        if len(ccds):
            html.append('CCDs overlapping brick:')
            html.extend(ccds_overlapping_html(ccds, name))

    html.extend([
            '</body></html>',
            ])

    if get_html:
        return html,ccds

    return HttpResponse('\n'.join(html))

def touchup_ccds(ccds, survey):
    import numpy as np
    ccds = survey.cleanup_ccds_table(ccds)
    cols = ccds.get_columns()
    if not 'seeing' in cols:
        ccds.seeing = ccds.fwhm * (3600. * np.sqrt(np.abs(ccds.cd1_1 * ccds.cd2_2 -
                                                          ccds.cd1_2 * ccds.cd2_1)))
    if not ('date_obs' in cols and 'ut' in cols):
        from astrometry.util.starutil_numpy import mjdtodate
        dates,uts = [],[]
        for ccd in ccds:
            date = mjdtodate(ccd.mjd_obs)
            #date = date.replace(microsecond = 0)
            date = date.isoformat()
            dd = date.split('T')
            dates.append(dd[0])
            uts.append(dd[1])
        ccds.date_obs = np.array(dates)
        ccds.ut = np.array(uts)
    return ccds

def ccds_overlapping_html(ccds, layer):
    html = ['<table class="ccds"><thead><tr><th>name</th><th>exptime</th><th>seeing</th><th>propid</th><th>date</th><th>image</th></tr></thead><tbody>']
    for ccd in ccds:
        ccdname = '%s %i %s %s' % (ccd.camera.strip(), ccd.expnum, ccd.ccdname.strip(), ccd.filter.strip())
        html.append('<tr><td><a href="%s">%s</a></td><td>%.1f</td><td>%.2f</td><td>%s</td><td>%s</td><td>%s</td>' % (
            reverse(ccd_detail, args=(layer, ccdname.replace(' ','-'))), ccdname,
            ccd.exptime, ccd.seeing, ccd.propid, ccd.date_obs + ' ' + ccd.ut[:8],
            ccd.image_filename.strip()))
    html.append('</tbody></table>')
    return html

def cutouts(req):
    from astrometry.util.util import Tan
    from astrometry.util.starutil_numpy import degrees_between
    import numpy as np
    from legacypipe.survey import wcs_for_brick

    ra = float(req.GET['ra'])
    dec = float(req.GET['dec'])
    name = req.GET.get('name', None)

    # half-size in DECam pixels
    size = int(req.GET.get('size', '100'), 10)
    size = min(200, size)
    size = size // 2

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
    #CCDs = _ccds_touching_box(north, south, east, west, name=name, survey=survey)
    CCDs = survey.ccds_touching_wcs(wcs)
    debug(len(CCDs), 'CCDs')
    CCDs = touchup_ccds(CCDs, survey)

    print('CCDs:', CCDs.columns())

    CCDs = CCDs[np.lexsort((CCDs.ccdname, CCDs.expnum, CCDs.filter))]

    ccds = []
    for i in range(len(CCDs)):
        c = CCDs[i]
        try:
            #c.image_filename = _get_image_filename(c)
            dim = survey.get_image_object(c)
            print('Image object:', dim)
            print('Filename:', dim.imgfn)
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

    url = req.build_absolute_uri('/') + settings.ROOT_URL + '/cutout_panels/%i/%s/'
    # Deployment: http://{s}.DOMAIN/...
    url = url.replace('://www.', '://')
    url = url.replace('://', '://%s.')
    domains = settings.SUBDOMAINS

    jpl_url = reverse(jpl_lookup)

    ccdsx = []
    for i,(ccd,x,y) in enumerate(ccds):
        fn = ccd.image_filename.replace(settings.DATA_DIR + '/', '')
        theurl = url % (domains[i%len(domains)], int(ccd.expnum), ccd.ccdname.strip()) + '?x=%i&y=%i&size=%i' % (x, y, size*2)
        if name is not None:
            theurl += '&name=' + name
        print('CCD columns:', ccd.columns())
        ccdsx.append(('<br/>'.join(['CCD %s %i %s, %.1f sec (x,y = %i,%i)' % (ccd.filter, ccd.expnum, ccd.ccdname, ccd.exptime, x, y),
                                    '<small>(%s [%i])</small>' % (fn, ccd.image_hdu),
                                    '<small>(observed %s @ %s)</small>' % (ccd.date_obs, ccd.ut),
                                    '<small><a href="%s?ra=%.4f&dec=%.4f&date=%s&camera=%s">Look up in JPL Small Bodies database</a></small>' %
                                    (jpl_url, ra, dec, ccd.date_obs + ' ' + ccd.ut, ccd.camera.strip())]),
                      theurl))
    return render(req, 'cutouts.html',
                  dict(ra=ra, dec=dec, ccds=ccdsx, name=name, drname=survey.drname,
                       brick=brick, brickx=brickx, bricky=bricky, size=W))


def jpl_lookup(req):
    import sys
    print('jpl_lookup: sys.version', sys.version)

    import requests
    from astrometry.util.starutil_numpy import ra2hmsstring, dec2dmsstring

    date = req.GET.get('date')
    ra = float(req.GET.get('ra'))
    dec = float(req.GET.get('dec'))
    camera = req.GET.get('camera')

    latlongargs = dict(decam=dict(lon='70.81489', lon_u='E',  # not W?
                                  lat='30.16606', lat_u='S',
                                  alt='2215.0', alt_u='m'),
                       mosaic=dict(lon='111.6003', lon_u='E', # W?
                                   lat = '31.9634', lat_u='N',
                                   alt='2120.0', alt_u='m'))[camera]

    hms = ra2hmsstring(ra, separator=':')
    dms = dec2dmsstring(dec)
    if dms.startswith('+'):
        dms = dms[1:]

    # '2016-03-01 00:42'
    s = requests.Session()
    r = s.get('https://ssd.jpl.nasa.gov/sbfind.cgi')
    #r2 = s.get('https://ssd.jpl.nasa.gov/sbfind.cgi?s_time=1')
    print('JPL lookup: setting date', date)
    r3 = s.post('https://ssd.jpl.nasa.gov/sbfind.cgi', data=dict(obs_time=date, time_zone='0', check_time='Use Specified Time'))
    print('Reply code:', r3.status_code)
    #r4 = s.get('https://ssd.jpl.nasa.gov/sbfind.cgi?s_loc=1')
    print('JPL lookup: setting location', latlongargs)
    latlongargs.update(s_pos="Use Specified Coordinates")
    r5 = s.post('https://ssd.jpl.nasa.gov/sbfind.cgi', data=latlongargs)
    print('Reply code:', r5.status_code)
    #r6 = s.get('https://ssd.jpl.nasa.gov/sbfind.cgi?s_region=1')
    print('JPL lookup: setting RA,Dec', (hms, dms))
    r7 = s.post('https://ssd.jpl.nasa.gov/sbfind.cgi', data=dict(ra_1=hms, dec_1=dms,
                                                                 ra_2='w0 0 45', dec_2='w0 0 45', sys='J2000', check_region_1="Use Specified R.A./Dec. Region"))
    print('Reply code:', r7.status_code)
    #r8 = s.get('https://ssd.jpl.nasa.gov/sbfind.cgi?s_constraint=1')
    print('JPL lookup: clearing mag limit')
    r9 = s.post('https://ssd.jpl.nasa.gov/sbfind.cgi', data=dict(group='all', limit='1000', mag_limit='', mag_required='yes', two_pass='yes', check_constraints="Use Specified Settings"))
    print('Reply code:', r9.status_code)
    print('JPL lookup: submitting search')
    r10 = s.post('https://ssd.jpl.nasa.gov/sbfind.cgi', data=dict(search="Find Objects"))
    txt = r10.text
    txt = txt.replace('<a href="sbdb.cgi', '<a href="https://ssd.jpl.nasa.gov/sbdb.cgi')
    return HttpResponse(txt)


# def cat_plot(req):
#     import pylab as plt
#     import numpy as np
#     from astrometry.util.util import Tan
#     from legacypipe.sdss import get_sdss_sources
# 
#     ra = float(req.GET['ra'])
#     dec = float(req.GET['dec'])
#     name = req.GET.get('name', None)
# 
#     ver = float(req.GET.get('ver',2))
# 
#     # half-size in DECam pixels
#     size = 50
#     W,H = size*2, size*2
#     
#     pixscale = 0.262 / 3600.
#     wcs = Tan(*[float(x) for x in [
#         ra, dec, size+0.5, size+0.5, -pixscale, 0., 0., pixscale, W, H]])
# 
#     M = 10
#     margwcs = wcs.get_subimage(-M, -M, W+2*M, H+2*M)
# 
#     tag = name
#     if tag is None:
#         tag = 'decals-dr1j'
#     tag = str(tag)
#     cat,hdr = _get_decals_cat(margwcs, tag=tag)
# 
#     # FIXME
#     nil,sdss = get_sdss_sources('r', margwcs,
#                                 photoobjdir=os.path.join(settings.DATA_DIR, 'sdss'),
#                                 local=True)
#     import tempfile
#     f,tempfn = tempfile.mkstemp(suffix='.png')
#     os.close(f)
# 
#     f = plt.figure(figsize=(2,2))
#     f.subplots_adjust(left=0.01, bottom=0.01, top=0.99, right=0.99)
#     f.clf()
#     ax = f.add_subplot(111, xticks=[], yticks=[])
#     if cat is not None:
#         ok,x,y = wcs.radec2pixelxy(cat.ra, cat.dec)
#         # matching the plot colors in index.html
#         # cc = dict(S=(0x9a, 0xfe, 0x2e),
#         #           D=(0xff, 0, 0),
#         #           E=(0x58, 0xac, 0xfa),
#         #           C=(0xda, 0x81, 0xf5))
#         cc = dict(PSF =(0x9a, 0xfe, 0x2e),
#                   SIMP=(0xff, 0xa5, 0),
#                   DEV =(0xff, 0, 0),
#                   EXP =(0x58, 0xac, 0xfa),
#                   COMP=(0xda, 0x81, 0xf5))
#         ax.scatter(x, y, s=50, c=[[float(x)/255. for x in cc[t.strip()]] for t in cat.type])
#     if sdss is not None:
#         ok,x,y = wcs.radec2pixelxy(sdss.ra, sdss.dec)
#         ax.scatter(x, y, s=30, marker='x', c='k')
#     ax.axis([0, W, 0, H])
#     f.savefig(tempfn)
# 
#     return send_file(tempfn, 'image/png', unlink=True,
#                      expires=0)


def _get_ccd(expnum, ccdname, name=None, survey=None):
    if survey is None:
        survey = _get_survey(name=name)
    expnum = int(expnum, 10)
    ccdname = str(ccdname).strip()
    CCDs = survey.find_ccds(expnum=expnum, ccdname=ccdname)
    assert(len(CCDs) == 1)
    ccd = CCDs[0]
    return ccd

def _get_image_filename(ccd):
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
    hdr = img.read_header()
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
    return img,hdr,slc,xstart,ystart

def cutout_panels(req, expnum=None, extname=None, name=None):
    import pylab as plt
    import numpy as np

    x = int(req.GET['x'], 10)
    y = int(req.GET['y'], 10)

    # half-size in DECam pixels
    size = int(req.GET.get('size', '100'), 10)
    size = min(200, size)
    size = size // 2

    if name is None:
        name = req.GET.get('name', name)
    survey = _get_survey(name=name)
    ccd = _get_ccd(expnum, extname, survey=survey)
    print('CCD:', ccd)
    im = survey.get_image_object(ccd)
    print('Image object:', im)
    fn = im.imgfn
    #fn = _get_image_filename(ccd)
    print('Filename:', fn)
    if not os.path.exists(fn):
        return HttpResponse('no such image: ' + fn)

    print('Getting postage stamp for', fn)
    img,hdr,slc,xstart,ystart = _get_image_slice(fn, ccd.image_hdu, x, y, size=size)

    sky = hdr.get('AVSKY', None)
    if sky is None:
        sky = np.median(img)
    img -= sky

    # band = ccd.filter.strip()
    # zpt = ccd.zpt
    # scales = dict(g = (2, 0.0066),
    #               r = (1, 0.01),
    #               z = (0, 0.025),)
    # scale = scales.get(band, None)
    # if scale is None or not np.isfinite(zpt):
    #     mn,mx = np.percentile(img.ravel(), [25, 99])
    # else:
    #     mn,mx = 

    h,w = img.shape
    destimg = np.zeros((max(h, size*2), max(w,size*2)), img.dtype)
    destimg[ystart:ystart+h, xstart:xstart+w] = img

    plt.clf()
    import tempfile
    f,jpegfn = tempfile.mkstemp(suffix='.jpg')
    os.close(f)
    mn,mx = np.percentile(img.ravel(), [25, 99])
    save_jpeg(jpegfn, destimg, origin='lower', cmap='gray',
              vmin=mn, vmax=mx)
    return send_file(jpegfn, 'image/jpeg', unlink=True)

    # wfn = fn.replace('ooi', 'oow')
    # if not os.path.exists(wfn):
    #     return HttpResponse('no such image: ' + wfn)
    # 
    # from legacypipe.decam import DecamImage
    # from legacypipe.desi_common import read_fits_catalog
    # from tractor import Tractor
    # 
    # ccd.cpimage = fn
    # D = _get_survey(name=name)
    # im = D.get_image_object(ccd)
    # kwargs = {}
    # 
    # if name == 'decals-dr2':
    #     kwargs.update(pixPsf=True, splinesky=True)
    # else:
    #     kwargs.update(const2psf=True)
    # tim = im.get_tractor_image(slc=slc, tiny=1, **kwargs)
    # 
    # if tim is None:
    #     img = np.zeros((0,0))
    # 
    # mn,mx = -1, 100
    # arcsinh = 1.
    # cmap = 'gray'
    # pad = True
    # 
    # scales = dict(g = (2, 0.0066),
    #               r = (1, 0.01),
    #               z = (0, 0.025),
    #               )
    # rows,cols = 1,5
    # f = plt.figure(figsize=(cols,rows))
    # f.clf()
    # f.subplots_adjust(left=0.002, bottom=0.02, top=0.995, right=0.998,
    #                   wspace=0.02, hspace=0)
    # 
    # imgs = []
    # 
    # img = tim.getImage()
    # imgs.append((img,None))
    # 
    # M = 10
    # margwcs = tim.subwcs.get_subimage(-M, -M, int(tim.subwcs.get_width())+2*M, int(tim.subwcs.get_height())+2*M)
    # for dr in ['dr1j']:
    #     cat,hdr = _get_decals_cat(margwcs, tag='decals-%s' % dr)
    #     if cat is None:
    #         tcat = []
    #     else:
    #         cat.shapedev = np.vstack((cat.shapedev_r, cat.shapedev_e1, cat.shapedev_e2)).T
    #         cat.shapeexp = np.vstack((cat.shapeexp_r, cat.shapeexp_e1, cat.shapeexp_e2)).T
    #         tcat = read_fits_catalog(cat, hdr=hdr)
    #     tr = Tractor([tim], tcat)
    #     img = tr.getModelImage(0)
    #     imgs.append((img,None))
    # 
    #     img = tr.getChiImage(0)
    #     imgs.append((img, dict(mn=-5,mx=5, arcsinh = None, scale = 1.)))
    # 
    # th,tw = tim.shape
    # pp = tim.getPsf().getPointSourcePatch(tw/2., th/2.)
    # img = np.zeros(tim.shape, np.float32)
    # pp.addTo(img)
    # imgs.append((img, dict(scale=0.0001, cmap='hot')))
    # 
    # from tractor.psfex import PsfEx
    # from tractor.patch import Patch
    # # HACK hard-coded image sizes.
    # thepsf = PsfEx(im.psffn, 2046, 4096)
    # psfim = thepsf.instantiateAt(x, y)
    # img = np.zeros(tim.shape, np.float32)
    # h,w = tim.shape
    # ph,pw = psfim.shape
    # patch = Patch((w-pw)/2., (h-ph)/2., psfim)
    # patch.addTo(img)
    # imgs.append((img, dict(scale = 0.0001, cmap = 'hot')))
    # 
    # for i,(img,d) in enumerate(imgs):
    # 
    #     mn,mx = -5, 100
    #     arcsinh = 1.
    #     cmap = 'gray'
    #     nil,scale = scales[ccd.filter]
    #     pad = True
    # 
    #     if d is not None:
    #         if 'mn' in d:
    #             mn = d['mn']
    #         if 'mx' in d:
    #             mx = d['mx']
    #         if 'arcsinh' in d:
    #             arcsinh = d['arcsinh']
    #         if 'cmap' in d:
    #             cmap = d['cmap']
    #         if 'scale' in d:
    #             scale = d['scale']
    # 
    #     img = img / scale
    #     if arcsinh is not None:
    #         def nlmap(x):
    #             return np.arcsinh(x * arcsinh) / np.sqrt(arcsinh)
    #         img = nlmap(img)
    #         mn = nlmap(mn)
    #         mx = nlmap(mx)
    # 
    #     img = (img - mn) / (mx - mn)
    #     if pad:
    #         ih,iw = img.shape
    #         padimg = np.zeros((2*size,2*size), img.dtype) + 0.5
    #         padimg[ystart:ystart+ih, xstart:xstart+iw] = img
    #         img = padimg
    # 
    #     ax = f.add_subplot(rows, cols, i+1, xticks=[], yticks=[])
    #     # the chips are turned sideways :)
    #     #plt.imshow(np.rot90(np.clip(img, 0, 1), k=3), cmap=cmap,
    #     #           interpolation='nearest', origin='lower')
    #     ax.imshow(np.rot90(np.clip(img, 0, 1).T, k=2), cmap=cmap,
    #                interpolation='nearest', origin='lower')
    #     #ax.xticks([]); ax.yticks([])
    # 
    # import tempfile
    # ff,tilefn = tempfile.mkstemp(suffix='.jpg')
    # os.close(ff)
    # 
    # f.savefig(tilefn)
    # f.clf()
    # del f
    # 
    # return send_file(tilefn, 'image/jpeg', unlink=True,
    #                  expires=3600)


def image_data(req, survey, ccd):
    import fitsio
    survey, c = get_ccd_object(survey, ccd)
    im = survey.get_image_object(c) #, makeNewWeightMap=False)
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
    im = survey.get_image_object(c) #, makeNewWeightMap=False)
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

def iv_data(req, survey, ccd):
    import fitsio
    survey, c = get_ccd_object(survey, ccd)
    im = survey.get_image_object(c) #, makeNewWeightMap=False)
    fn = im.wtfn
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
    return send_file(tmpfn, 'image/fits', unlink=True, filename='iv-%s.fits.gz' % ccd)


def image_stamp(req, surveyname, ccd):
    import fitsio
    survey, c = get_ccd_object(surveyname, ccd)
    im = survey.get_image_object(c) #, makeNewWeightMap=False)
    fn = im.imgfn
    print('Opening', fn)
    import tempfile
    ff,tmpfn = tempfile.mkstemp(suffix='.jpg')
    os.close(ff)
    pix,hdr = fitsio.read(fn, ext=c.image_hdu, header=True)
    os.unlink(tmpfn)
    import pylab as plt
    import numpy as np
    if 'decals' in surveyname:
        # rotate image
        pix = pix.T

    mn,mx = np.percentile(pix.ravel(), [25, 99])
    h,w = pix.shape
    plt.figure(num=1, figsize=(w/(4*100.), h/(4*100.)), dpi=100)
    plt.clf()
    plt.subplots_adjust(left=0.005, right=0.995, bottom=0.005, top=0.995)
    plt.imshow(pix, interpolation='nearest', origin='lower', cmap='gray',
               vmin=mn, vmax=mx)
    plt.xticks([]); plt.yticks([])
    plt.savefig(tmpfn)
    #plt.imsave(tmpfn, pix, vmin=mn, vmax=mx, cmap='gray')
    return send_file(tmpfn, 'image/jpeg', unlink=True)

layers = {}
def get_layer(name, default=None):
    global layers

    # mzls+bass-dr4 in URLs turns the "+" into a " "
    name = name.replace(' ', '+')

    if name in layers:
        return layers[name]

    layer = None

    print('get_layer: name "%s"' % name)

    if name in ['sdss2', 'sdssco', 'sdss']:
        '''
        "Rebricked" SDSS images.
        - top-level tiles are from sdss2
        - tile levels 6-13 are from sdssco
        (all on sanjaya)
        '''
        layer = ReSdssLayer('sdss2')

    elif name == 'eboss':
        survey = _get_survey('eboss')
        layer = ReDecalsLayer('eboss', 'image', survey)

    elif name in ['decals-dr5', 'decals-dr5-model', 'decals-dr5-resid']:
        survey = _get_survey('decals-dr5')
        image = ReDecalsLayer('decals-dr5', 'image', survey)
        model = ReDecalsLayer('decals-dr5-model', 'model', survey, drname='decals-dr5')
        resid = ReDecalsResidLayer(image, model, 'decals-dr5-resid', 'resid', survey,
                                   drname='decals-dr5')
        layers['decals-dr5'] = image
        layers['decals-dr5-model'] = model
        layers['decals-dr5-resid'] = resid
        layer = layers[name]
        
    elif name == 'ps1':
        layer = PS1Layer('ps1')

    elif name in ['decaps', 'decaps-model', 'decaps-resid']:
        survey = _get_survey('decaps')
        image = Decaps2Layer('decaps', 'image', survey)
        model = Decaps2Layer('decaps-model', 'model', survey)
        resid = Decaps2ResidLayer(image, model,
                                  'decaps-resid', 'resid', survey, drname='decaps')
        layers['decaps'] = image
        layers['decaps-model'] = model
        layers['decaps-resid'] = resid
        layer = layers[name]

    elif name in ['mzls+bass-dr4', 'mzls+bass-dr4-model', 'mzls+bass-dr4-resid']:
        survey = _get_survey('mzls+bass-dr4')
        image = DecalsDr3Layer('mzls+bass-dr4', 'image', survey, drname='mzls+bass-dr4')
        model = DecalsDr3Layer('mzls+bass-dr4-model', 'model', survey,
                            drname='mzls+bass-dr4')
        resid = DecalsResidLayer(image, model, 'mzls+bass-dr4-resid', 'resid', survey,
                                 drname='mzls+bass-dr4')
        layers['mzls+bass-dr4'] = image
        layers['mzls+bass-dr4-model'] = model
        layers['mzls+bass-dr4-resid'] = resid
        layer = layers[name]

    elif name in ['decals-dr3', 'decals-dr3-model', 'decals-dr3-resid']:
        survey = _get_survey('decals-dr3')
        image = DecalsDr3Layer('decals-dr3', 'image', survey)
        model = DecalsDr3Layer('decals-dr3-model', 'model', survey, drname='decals-dr3')
        resid = DecalsResidLayer(image, model, 'decals-dr3-resid', 'resid', survey,
                                 drname='decals-dr3')
        # No disk space for DR3 scale=1 !
        image.minscale = model.minscale = resid.minscale = 2
        
        layers['decals-dr3'] = image
        layers['decals-dr3-model'] = model
        layers['decals-dr3-resid'] = resid
        layer = layers[name]

    elif name in ['decals-dr2', 'decals-dr2-model', 'decals-dr2-resid']:
        survey = _get_survey('decals-dr2')
        image = DecalsDr3Layer('decals-dr2', 'image', survey)
        model = DecalsDr3Layer('decals-dr2-model', 'model', survey, drname='decals-dr2')
        resid = DecalsResidLayer(image, model, 'decals-dr2-resid', 'resid', survey,
                                 drname='decals-dr2')
        layers['decals-dr2'] = image
        layers['decals-dr2-model'] = model
        layers['decals-dr2-resid'] = resid
        layer = layers[name]

    elif name == 'unwise-w1w2':
        layer = UnwiseLayer('unwise-w1w2',
                            settings.UNWISE_DIR)
    elif name == 'unwise-neo2':
        layer = UnwiseLayer('unwise-neo2',
                            settings.UNWISE_NEO2_DIR)

    elif name == 'halpha':
        from tractor.sfd import SFDMap
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
    name = layer_name_map(name)
    def view(request, ver, zoom, x, y, **kwargs):
        layer = get_layer(name)
        return layer.get_tile(request, ver, zoom, x, y, **kwargs)
    return view

def sdss_wcs(req):
    return HttpResponse('sorry, offline for now')

    from astrometry.util.util import Tan
    import numpy as np
    args = []
    for k in ['crval1','crval2','crpix1','crpix2',
              'cd11','cd12','cd21','cd22','imagew','imageh']:
        v = req.GET.get(k)
        fv = float(v)
        args.append(fv)
    #wcs = Tan(*[float(req.GET.get(k)) for k in ['crval1','crval2','crpix1','crpix2',
    #                                            'cd11','cd12','cd21','cd22','imagew','imageh']])
    wcs = Tan(*args)
    print('wcs:', wcs)
    pixscale = wcs.pixel_scale()
    zoom = 13 - int(np.round(np.log2(pixscale / 0.396)))
    x = y = 0

    sdss = get_layer('sdssco')

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


def ra_ranges_overlap(ralo, rahi, ra1, ra2):
    import numpy as np
    x1 = np.cos(np.deg2rad(ralo))
    y1 = np.sin(np.deg2rad(ralo))

    x2 = np.cos(np.deg2rad(rahi))
    y2 = np.sin(np.deg2rad(rahi))

    x3 = np.cos(np.deg2rad(ra1))
    y3 = np.sin(np.deg2rad(ra1))

    x4 = np.cos(np.deg2rad(ra2))
    y4 = np.sin(np.deg2rad(ra2))

    #cw31 = x1*y3 - x3*y1
    cw32 = x2*y3 - x3*y2

    cw41 = x1*y4 - x4*y1
    #cw42 = x2*y4 - x4*y2

    #print('3:', cw31, cw32)
    #print('4:', cw41, cw42)
    return np.logical_and(cw32 <= 0, cw41 >= 0)


if __name__ == '__main__':
    import sys

    from django.test import Client
    c = Client()
    #response = c.get('/viewer/image-data/decals-dr5/decam-335137-N24-g')
    response = c.get('/image-data/decals-dr5/decam-335137-N24-g')
    print('Got:', response.status_code)
    print('Content:', response.content)
    sys.exit(0)


    class duck(object):
        pass

    req = duck()
    req.META = dict()
    req.GET = dict()

    from map import views
    view = views.get_tile_view('halpha')
    view(req, 1, 7, 44, 58)
    # http://c.legacysurvey.org/viewer-dev/halpha/1/7/44/58.jpg
    import sys
    sys.exit(0)

    req.GET['date'] = '2016-03-01 00:42'
    req.GET['ra'] = '131.3078'
    req.GET['dec'] = '20.7488'
    req.GET['camera'] = 'decam'
    jpl_lookup(req)

    import sys
    sys.exit(0)

    assert(ra_ranges_overlap(359, 1, 0.5, 1.5) == True)
    assert(ra_ranges_overlap(359, 1, 358, 0.)  == True)
    assert(ra_ranges_overlap(359, 1, 358, 2.)  == True)
    assert(ra_ranges_overlap(359, 1, 359.5, 0.5) == True)

    assert(ra_ranges_overlap(359, 1, 357, 358) == False)
    assert(ra_ranges_overlap(359, 1, 2, 3) == False)
    assert(ra_ranges_overlap(359, 1, 179, 181) == False)
    assert(ra_ranges_overlap(359, 1, 90, 270) == False)
    
    # vanilla
    ra_ranges_overlap(0, 1, 0.5, 1.5)

    # enclosed
    ra_ranges_overlap(0, 1, -0.5, 1.5)

    # not-enclosed
    ra_ranges_overlap(0, 1, 1.5, -0.5)

    print()
    # greater
    ra_ranges_overlap(0, 1, 2, 3)

    # less
    ra_ranges_overlap(0, 1, -2, -1)

    # just touching
    #ra_ranges_overlap(0, 1, 1, 2)

    print()

    # overlapping bottom of range
    ra_ranges_overlap(0, 1, -0.5, 0.5)

    # within
    ra_ranges_overlap(0, 1, 0.25, 0.75)

    sys.exit(0)



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
