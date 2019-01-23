from __future__ import print_function
if __name__ == '__main__':
    ## NOTE, if you want to run this from the command-line, probably have to do so
    # from sgn04 node within the virtualenv.
    import sys
    sys.path.insert(0, 'django-1.9')
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'viewer.settings'
    import django
    django.setup()
    #print('Django:', django.__file__)
    #print('Version:', django.get_version())

    #from viewer import settings
    #settings.ALLOWED_HOSTS += 'testserver'


import os
import sys
import re
from django.http import HttpResponse, StreamingHttpResponse
try:
    from django.core.urlresolvers import reverse
except:
    # django 2.0
    from django.urls import reverse

from django import forms

from viewer import settings
from map.utils import (get_tile_wcs, trymakedirs, save_jpeg, ra2long, ra2long_B,
                       send_file, oneyear)
from map.coadds import get_scaled
from map.cats import get_random_galaxy

import matplotlib
matplotlib.use('Agg')

py3 = (sys.version_info[0] >= 3)


debug_ps = None
import pylab as plt
if False:
    from astrometry.util.plotutils import PlotSequence
    debug_ps = PlotSequence('debug')


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
    'wssa': [1,],
    'sdss': [1,],
    'sdssco': [1,],
    'ps1': [1],

    'vlass': [1],

    'sdss2': [1,],

    'eboss': [1,],

    'phat': [1,],
    'm33': [1,],

    'decals-dr7': [1],
    'decals-dr7-model': [1],
    'decals-dr7-resid': [1],
    'decals-dr7-invvar': [1],

    'mzls+bass-dr6': [1],
    'mzls+bass-dr6-model': [1],
    'mzls+bass-dr6-resid': [1],

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
    'unwise-neo3': [1],
    'unwise-neo4': [1],
    #'unwise-w3w4': [1],

    'unwise-cat-model': [1],

    '2mass': [1],
    'galex': [1],

    'des-dr1': [1],

    'cutouts': [1],

    'ls-dr56': [1],
    'ls-dr67': [1],
    }

def urls(req):
    from django.shortcuts import render
    return render(req, 'urls.html')

def gfas(req):
    from django.shortcuts import render
    return render(req, 'desi-gfas.html')

def ci(req):
    from django.shortcuts import render
    return render(req, 'desi-ci.html')

def request_layer_name(req, default_layer = 'mzls+bass-dr6'):
    name = req.GET.get('layer', default_layer)
    return clean_layer_name(name)

def clean_layer_name(name):
    name = str(name)
    name = name.replace(' ', '+')
    name = name.replace('decaps2', 'decaps')
    return name

def layer_to_survey_name(layer):
    layer = layer.replace('-model', '')
    layer = layer.replace('-resid', '')
    return layer

galaxycat = None

def is_decaps(req):
    host = req.META.get('HTTP_HOST', None)
    #print('Host:', host)
    return (host == 'decaps.legacysurvey.org')

def is_m33(req):
    host = req.META.get('HTTP_HOST', None)
    return (host == 'm33.legacysurvey.org')

def index(req, **kwargs):
    if is_decaps(req):
        return decaps(req)
    if is_m33(req):
        return m33(req)
    return _index(req, **kwargs)

def _index(req,
           default_layer = 'decals-dr7',
           default_radec = (None,None),
           default_zoom = 12,
           rooturl=settings.ROOT_URL,
           maxZoom = 16,
           **kwargs):
    kwkeys = dict(
        enable_vlass = True,
        enable_dev = settings.ENABLE_DEV,
        enable_m33 = False,
        enable_sql = settings.ENABLE_SQL,
        enable_vcc = settings.ENABLE_VCC,
        enable_wl = settings.ENABLE_WL,
        enable_cutouts = settings.ENABLE_CUTOUTS,
        enable_dr67 = settings.ENABLE_DR67,
        enable_dr56 = settings.ENABLE_DR56,
        enable_dr2 = settings.ENABLE_DR2,
        enable_dr3 = settings.ENABLE_DR3,
        enable_dr4 = settings.ENABLE_DR4,
        enable_dr5 = settings.ENABLE_DR5,
        enable_dr6 = settings.ENABLE_DR6,
        enable_dr7 = settings.ENABLE_DR7,
        enable_decaps = settings.ENABLE_DECAPS,
        enable_ps1 = settings.ENABLE_PS1,
        enable_des_dr1 = settings.ENABLE_DES_DR1,
        enable_dr3_models = settings.ENABLE_DR3,
        enable_dr3_resids = settings.ENABLE_DR3,
        enable_dr4_models = settings.ENABLE_DR4,
        enable_dr4_resids = settings.ENABLE_DR4,
        enable_dr5_models = settings.ENABLE_DR5,
        enable_dr5_resids = settings.ENABLE_DR5,
        enable_dr6_models = settings.ENABLE_DR6,
        enable_dr6_resids = settings.ENABLE_DR6,
        enable_dr7_models = settings.ENABLE_DR7,
        enable_dr7_resids = settings.ENABLE_DR7,
        enable_dr2_overlays = settings.ENABLE_DR2,
        enable_dr3_overlays = settings.ENABLE_DR3,
        enable_dr4_overlays = settings.ENABLE_DR4,
        enable_dr5_overlays = settings.ENABLE_DR5,
        enable_dr6_overlays = settings.ENABLE_DR6,
        enable_dr7_overlays = settings.ENABLE_DR7,
        enable_eboss = settings.ENABLE_EBOSS,
        enable_desi_targets = True,
        enable_desi_footprint = True,
        enable_spectra = True,
        maxNativeZoom = settings.MAX_NATIVE_ZOOM,
        #enable_phat = False,
        enable_phat = True,
    )

    for k in kwargs.keys():
        if not k in kwkeys:
            raise RuntimeError('unknown kwarg "%s" in map.index()' % k)
    for k,v in kwkeys.items():
        if not k in kwargs:
            kwargs[k] = v
    
    from map.cats import cat_user

    layer = request_layer_name(req, default_layer)

    # Nice spiral galaxy
    #ra, dec, zoom = 244.7, 7.4, 13

    ra, dec = default_radec
    zoom = default_zoom

    plate = req.GET.get('plate', None)
    if plate is not None:
        from astrometry.util.fits import fits_table
        plate = int(plate, 10)
        T = fits_table(os.path.join(settings.DATA_DIR, 'sdss',
                                    'plates-dr12.fits'))
        T.cut(T.plate == plate)
        ra,dec = float(T.racen), float(T.deccen)
        zoom = 8
        layer = 'sdss2'

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

    # Can't do this simple thing because CORS prevents
    #decaps.legacysurvey.org from reading from legacysurvey.org.
    #baseurl = 'http://%s%s' % (settings.HOSTNAME, settings.ROOT_URL)
    path = settings.ROOT_URL
    if is_decaps(req):
        path = '/'
    baseurl = req.build_absolute_uri(path)
    if baseurl.endswith('/'):
        baseurl = baseurl[:-1]
    print('Base URL:', baseurl)

    caturl = baseurl + '/{id}/{ver}/{z}/{x}/{y}.cat.json'

    smallcaturl = baseurl + '/{id}/{ver}/cat.json?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}'

    tileurl = settings.TILE_URL

    subdomains = settings.SUBDOMAINS
    # convert to javascript
    subdomains = '[' + ','.join(["'%s'" % s for s in subdomains]) + '];'

    static_tile_url = settings.STATIC_TILE_URL

    static_tile_url_B = settings.STATIC_TILE_URL_B
    subdomains_B = settings.SUBDOMAINS_B
    subdomains_B = '[' + ','.join(["'%s'" % s for s in subdomains_B]) + '];'

    ccdsurl = baseurl + '/ccds/?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&id={id}'
    bricksurl = baseurl + '/bricks/?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&layer={layer}'
    expsurl = baseurl + '/exps/?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&id={id}'
    platesurl = baseurl + '/sdss-plates/?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}'
    sqlurl = baseurl + '/sql-box/?north={north}&east={east}&south={south}&west={west}&q={q}'
    namequeryurl = baseurl + '/namequery/?obj={obj}'

    uploadurl = baseurl + '/upload-cat/'

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
    #print('User catalogs:', usercats)
    usercatalogurl = reverse(cat_user, args=(1,)) + '?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&cat={cat}'
    usercatalogurl2 = reverse(cat_user, args=(1,)) + '?start={start}&N={N}&cat={cat}'

    
    absurl = req.build_absolute_uri(rooturl)
    hostname_url = req.build_absolute_uri('/')

    test_layers = []
    try:
        from map.test_layers import test_layers as tl
        for la in tl:
            if not la in test_layers:
                test_layers.append(la)
    except:
        import traceback
        traceback.print_exc()


    args = dict(ra=ra, dec=dec, zoom=zoom,
                maxZoom=maxZoom,
                galname=galname,
                layer=layer, tileurl=tileurl,
                absurl=absurl,
                hostname_url=hostname_url,
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

                test_layers = test_layers,
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

def m33(req):
    return _index(req, enable_m33=True,
                  enable_decaps=True,
                  enable_dev=False,
                  enable_dr7=False,
                  enable_dr6=False,
                  enable_dr5=False,
                  enable_dr4=False,
                  enable_dr56=False,
                 enable_dr3=False,
                 enable_dr3_models=False,
                 enable_dr3_resids=False,
                 enable_dr4_models=False,
                 enable_dr4_resids=False,
                 enable_dr5_models=False,
                 enable_dr5_resids=False,
                 enable_ps1=False,
                 enable_dr3_overlays=False,
                 enable_dr4_overlays=False,
                 enable_dr5_overlays=False,
                 enable_dr7_overlays=False,
                 enable_desi_footprint=False,
                 enable_desi_targets=False,
                 enable_spectra=False,
                 default_layer='m33',
                 default_radec=(23.390, 30.692),
                 default_zoom=16,
                  maxZoom=18,
                  maxNativeZoom = 18,
                 rooturl=settings.ROOT_URL + '/m33',
    )

def dr5(req):
    return _index(req, enable_decaps=True,
                 enable_ps1=False,
                 enable_desi_targets=True,
                 default_layer='decals-dr5',
                 default_radec=(234.7, 13.6),
                 rooturl=settings.ROOT_URL + '/dr5',
    )

def dr6(req):
    return _index(req, enable_decaps=True,
                 enable_ps1=False,
                 enable_desi_targets=True,
                 default_layer='mzls+bass-dr6',
                 default_radec=(175.32, 47.69),
                 rooturl=settings.ROOT_URL + '/dr6',
    )

def phat(req):
    return _index(req,
                  enable_ps1=False,
                  enable_phat=True,
                  default_layer='phat',
                  default_radec=(11.04, 41.48),
                  rooturl=settings.ROOT_URL + '/phat',
                  maxZoom=18,
    )

def query_ned(q):
    try:
        # py2
        from urllib2 import urlopen
        from urllib import urlencode
    except:
        # py3
        from urllib.request import urlopen
        from urllib.parse import urlencode

    url = 'http://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame/NSV?'
    url += urlencode(dict(q=q)).replace('q=','')
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
            return True,(ra,dec)
        if words[0] == '#!':
            error = ' '.join(words[1:])
            return False,error
    return False,'Failed to parse answer from NED'

def name_query(req):
    import json

    obj = req.GET.get('obj')
    #print('Name query: "%s"' % obj)

    if len(obj) == 0:
        layer = request_layer_name(req)
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
            pass

    try:
        result,val = query_ned(obj)
        if result:
            ra,dec = val
            return HttpResponse(json.dumps(dict(ra=ra, dec=dec, name=obj)),
                                content_type='application/json')
        else:
            error = val
            return HttpResponse(json.dumps(dict(error=error)),
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
    layer = request_layer_name(req)
    layer = layer_to_survey_name(layer)
    ## FIXME -- could point to unWISE data!
    #if 'unwise' in name or name == 'sdssco':
    #    name = 'decals-dr3'

    print('Layer', layer)
    if layer in ['sdss2']:
        # from ccd_list...
        # 0.15: SDSS field radius is ~ 0.13
        radius = 0.15
        T = sdss_ccds_near(ra, dec, radius)
        if T is None:
            return HttpResponse('No SDSS data near RA,Dec = (%.3f, %.3f)' % (ra,dec))

        
        html = [html_tag + '<head><title>%s data for RA,Dec (%.4f, %.4f)</title></head>' %
                ('SDSS', ra, dec),
                ccds_table_css + '<body>',
                '<h1>%s data for RA,Dec = (%.4f, %.4f): CCDs overlapping</h1>' %
                ('SDSS', ra, dec)]
        html.append('<table class="ccds"><thead><tr><th>Details</th><th>Jpeg</th><th>Run</th><th>Camcol</th><th>Field</th></thead><tbody>')
        T.cut(np.lexsort((T.field, T.camcol, T.run)))
        for t in T:
            url = 'https://dr12.sdss.org/fields/runCamcolField?run=%i&camcol=%i&field=%i' % (t.run, t.camcol, t.field)
            #
            jpeg_url = 'https://dr12.sdss.org/sas/dr12/boss/photoObj/frames/301/%i/%i/frame-irg-%06i-%i-%04i.jpg' % (t.run, t.camcol, t.run, t.camcol, t.field)
            html.append('<tr><td><a href="%s">details</a></td><td><a href="%s">jpeg</a></td><td>%i</td><td>%i</td><td>%i</td>' % (url, jpeg_url, t.run, t.camcol, t.field))

        html.append('</tbody></table>')
        html.append('</body></html>')
        return HttpResponse('\n'.join(html))

    survey = get_survey(layer)
    if not hasattr(survey, 'drname'):
        survey.drname = layer
    if not hasattr(survey, 'drurl'):
        survey.drurl = 'http://portal.nersc.gov/project/cosmo/data/legacysurvey/' + layer

    bricks = survey.get_bricks()
    I = np.flatnonzero((ra >= bricks.ra1) * (ra < bricks.ra2) *
                       (dec >= bricks.dec1) * (dec < bricks.dec2))
    if len(I) == 0:
        return HttpResponse('No DECaLS data overlaps RA,Dec = %.4f, %.4f for version %s' % (ra, dec, name))
    I = I[0]
    brick = bricks[I]
    brickname = brick.brickname

    brick_html,ccds = brick_detail(req, brickname, get_html=True, brick=brick)
    html = brick_html

    if ccds is not None and len(ccds):
        from legacypipe.survey import wcs_for_brick
        brickwcs = wcs_for_brick(brick)
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
        html.extend(ccds_overlapping_html(ccds, layer, ra=ra, dec=dec))
        html = html + brick_html[1:]

    return HttpResponse('\n'.join(html))


class MapLayer(object):
    '''
    Represents a "bricked" image map layer: eg, DECaLS DRx (image, model, or
    resid), SDSSco, unWISE.
    '''
    def __init__(self, name,
                 nativescale=14, maxscale=7):
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
        scale = np.clip(scale, 0, self.maxscale)
        #print('Old scale', oldscale, 'scale', scale)
        return scale

    def bricks_touching_aa_wcs(self, wcs, scale=None):
        from astrometry.util.starutil_numpy import degrees_between

        rc,dc = wcs.radec_center()
        # get radius from the max diagonals
        W = wcs.get_width()
        H = wcs.get_height()
        #rr,dd = wcs.pixelxy2radec([0.5,0.5,W+0.5,W+0.5], [0.5,H+0.5,0.5,H+0.5])
        rr,dd = wcs.pixelxy2radec([1,1,W,W], [1,H,1,H])[-2:]
        d1 = degrees_between(rr[0], dd[0], rr[3], dd[3])
        d2 = degrees_between(rr[1], dd[1], rr[2], dd[2])
        rad = 1.01 * max(d1,d2)/2.

        B = self.bricks_within_range(rc, dc, rad, scale=scale)
        if B is None:
            # Previously...
            '''Assumes WCS is axis-aligned and normal parity'''
            rlo,d = wcs.pixelxy2radec(W, H/2)[-2:]
            rhi,d = wcs.pixelxy2radec(1, H/2)[-2:]
            r,d1 = wcs.pixelxy2radec(W/2, 1)[-2:]
            r,d2 = wcs.pixelxy2radec(W/2, H)[-2:]
            dlo = min(d1, d2)
            dhi = max(d1, d2)
            print('RA,Dec bounds of WCS:', rlo,rhi,dlo,dhi)
            return self.bricks_touching_radec_box(rlo, rhi, dlo, dhi, scale=scale)

        from astrometry.util.miscutils import polygons_intersect
        import numpy as np

        keep = []
        xl,xm,xh = 0.5, (W+1)/2., W+0.5
        yl,ym,yh = 0.5, (H+1)/2., H+0.5
        xy = np.array([[xl,yl], [xm, yl], [xh,yl], [xh,ym], [xh,yh],
                       [xm,yh], [xl,yh], [xl,ym], [xl,yl]])

        if debug_ps is not None:
            plt.clf()
            plt.plot(xy[:,0], xy[:,1], 'k-')

        for i,brick in enumerate(B):
            bwcs = self.get_scaled_wcs(brick, None, scale)
            bh,bw = bwcs.shape
            # walk the boundary
            xl,xm,xh = 0.5, (bw+1)/2., bw+0.5
            yl,ym,yh = 0.5, (bh+1)/2., bh+0.5
            rr,dd = bwcs.pixelxy2radec([xl, xm, xh, xh, xh, xm, xl, xl, xl],
                                       [yl, yl, yl, ym, yh, yh, yh, ym, yl])
            #try:
            #    ok,bx,by = wcs.radec2pixelxy(rr, dd, wrap=False)
            #except:
            ok,bx,by = wcs.radec2pixelxy(rr, dd)

            # xx1 = np.linspace(xl, xh, 100)
            # yy1 = np.array([yl]*100)
            # xx2 = np.array([xh]*100)
            # yy2 = np.linspace(yl, yh, 100)
            # xx3 = np.linspace(xh, xl, 100)
            # yy3 = np.array([yh]*100)
            # xx4 = np.array([xl]*100)
            # yy4 = np.linspace(yh, yl, 100)
            # rr,dd = bwcs.pixelxy2radec(np.hstack((xx1,xx2,xx3,xx4)), np.hstack((yy1,yy2,yy3,yy4)))
            # try:
            #     ok,bx,by = wcs.radec2pixelxy(rr, dd, wrap=False)
            # except:
            #     ok,bx,by = wcs.radec2pixelxy(rr, dd)

            bx = bx[ok]
            by = by[ok]
            if len(bx) == 0:
                continue
            if polygons_intersect(xy, np.vstack((bx, by)).T):
                if debug_ps is not None:
                    plt.plot(bx, by, '-')
                keep.append(i)
            #else:
            #    plt.plot(bx, by, 'r-')
        if debug_ps is not None:
            debug_ps.savefig()
                
        print('Looking for bricks touching WCS', wcs)
        # DEBUG
        if True:
            rlo,d = wcs.pixelxy2radec(W, H/2)[-2:]
            rhi,d = wcs.pixelxy2radec(1, H/2)[-2:]
            r,d1 = wcs.pixelxy2radec(W/2, 1)[-2:]
            r,d2 = wcs.pixelxy2radec(W/2, H)[-2:]
            #print('Approx RA,Dec range', rlo,rhi, 'Dec', d1,d2)

        #print('Bricks within range:', B.brickname)
        print('Bricks touching:', B.brickname[np.array(keep)])
        B.cut(keep)
        return B
            


    def bricks_within_range(self, ra, dec, radius, scale=None):
        return None

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

    def bricks_for_band(self, bricks, band):
        has = getattr(bricks, 'has_%s' % band, None)
        if has is not None:
            rtn = bricks[has]
            # print('bricknames for band', band, ':', len(bricks), 'bricks; returning',
            #       len(rtn))
            # print('has:', has)
            # print('All bricks:', bricks.brickname)
            # print('Returning :', bricks.brickname[has])
            return rtn
        #print('bricknames for band', band, ':', len(bricks), 'bricks; no has_%s column' % band)
        return bricks

    def get_filename(self, brick, band, scale, tempfiles=None):
        if scale == 0:
            return self.get_base_filename(brick, band)
        fn = self.get_scaled_filename(brick, band, scale)
        #print('Filename:', fn)
        if os.path.exists(fn):
            return fn
        #print('Creating', fn)
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
            print('create_scaled_image: brick', brick, 'band', band, 'scale', scale, ': Image source file', sourcefn, 'not found')
            return None
        ro = settings.READ_ONLY_BASEDIR
        if ro:
            print('Read-only; not creating scaled', brick, band, scale)
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
        
    def get_base_filename(self, brick, band, **kwargs):
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

        #print('render_into_wcs: wcs', wcs, 'zoom,x,y', zoom,x,y, 'general wcs?', general_wcs)

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

        W = int(wcs.get_width())
        H = int(wcs.get_height())
        target_ra,target_dec = wcs.pixelxy2radec([1,  1,1,W/2,W,W,  W,W/2],
                                                 [1,H/2,H,H,  H,H/2,1,1  ])[-2:]

        #print('Target RA,Dec:', target_ra, target_dec)
        #print('Render into wcs: RA,Dec points', r, d)

        #print('render_into_wcs: scale', scale, 'N bricks:', len(bricks))
        # for band in bands:
        #     bandbricks = self.bricks_for_band(bricks, band)
        #     for brick in bandbricks:
        #         brickname = brick.brickname
        #         print('Will read', brickname, 'for band', band, 'scale', scale)

        rimgs = []
        for band in bands:
            rimg = np.zeros((H,W), np.float32)
            rw   = np.zeros((H,W), np.float32)
            bandbricks = self.bricks_for_band(bricks, band)
            for brick in bandbricks:
                brickname = brick.brickname
                print('Reading', brickname, 'band', band, 'scale', scale)
                # call get_filename to possibly generate scaled version
                fn = self.get_filename(brick, band, scale, tempfiles=tempfiles)
                print('Reading', brickname, 'band', band, 'scale', scale, '-> fn', fn)
                if fn is None:
                    continue

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

                # Check for pixel overlap area (projecting target WCS edges into this brick)
                ok,xx,yy = bwcs.radec2pixelxy(target_ra, target_dec)
                xx = xx.astype(np.int)
                yy = yy.astype(np.int)

                #print('Brick', brickname, 'band', band, 'shape', bwcs.shape, 'pixel coords', xx, yy)

                imW,imH = int(bwcs.get_width()), int(bwcs.get_height())
                M = 10
                xlo = np.clip(xx.min() - M, 0, imW)
                xhi = np.clip(xx.max() + M, 0, imW)
                ylo = np.clip(yy.min() - M, 0, imH)
                yhi = np.clip(yy.max() + M, 0, imH)
                #print('-- x range', xlo,xhi, 'y range', ylo,yhi)
                if xlo >= xhi or ylo >= yhi:
                    print('No pixel overlap')
                    continue

                if debug_ps is not None:
                    plt.clf()
                    plt.plot([1,1,imW,imW,1], [1,imH,imH,1,1], 'k-')
                    plt.plot(xx, yy, 'r-')
                    plt.plot([xlo,xlo,xhi,xhi,xlo], [ylo,yhi,yhi,ylo,ylo], 'm-')
                    plt.title('black=brick, red=target')
                    debug_ps.savefig()

                    plt.clf()
                    xx1 = np.linspace(1, imW, 100)
                    yy1 = np.array([1]*100)
                    xx2 = np.array([imW]*100)
                    yy2 = np.linspace(1, imH, 100)
                    xx3 = np.linspace(imW, 1, 100)
                    yy3 = np.array([imH]*100)
                    xx4 = np.array([1]*100)
                    yy4 = np.linspace(imH, 1, 100)
                    rr,dd = bwcs.pixelxy2radec(np.hstack((xx1,xx2,xx3,xx4)), np.hstack((yy1,yy2,yy3,yy4)))
                    plt.plot(rr, dd, 'k-')
                    plt.plot(target_ra, target_dec, 'r-')
                    xx1 = np.linspace(1, W, 100)
                    yy1 = np.array([1]*100)
                    xx2 = np.array([W]*100)
                    yy2 = np.linspace(1, H, 100)
                    xx3 = np.linspace(W, 1, 100)
                    yy3 = np.array([H]*100)
                    xx4 = np.array([1]*100)
                    yy4 = np.linspace(H, 1, 100)
                    rr,dd = wcs.pixelxy2radec(np.hstack((xx1,xx2,xx3,xx4)), np.hstack((yy1,yy2,yy3,yy4)))
                    plt.plot(rr, dd, 'm-', lw=2, alpha=0.5)
                    plt.title('black=brick, red=target')
                    debug_ps.savefig()
                    
                    

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


                # DEBUG
                # sh,sw = subwcs.shape
                # rr,dd = subwcs.pixelxy2radec([1,1,sw,sw], [1,sh,sh,1])
                # ok,xx,yy = wcs.radec2pixelxy(rr, dd)
                # print('Sub-WCS corners -> target pixels', xx.astype(int), yy.astype(int))

                #ok,xx,yy = wcs.radec2pixelxy(target_ra, target_dec)
                #print('Target_ra,dec to target pix:', xx, yy)

                #rr,dd = bwcs.pixelxy2radec([xlo,xlo,xhi,xhi], [ylo,yhi,yhi,ylo])
                #ok,xx,yy = wcs.radec2pixelxy(rr, dd)
                #print('WCS corners -> target pixels', xx.astype(int), yy.astype(int))

                #print('BWCS shape', bwcs.shape, 'desired subimage shape', yhi-ylo, xhi-xlo,
                #'subwcs shape', subwcs.shape, 'img shape', img.shape)

                #print('Resampling', img.shape)
                try:
                    Yo,Xo,Yi,Xi,nil = resample_with_wcs(wcs, subwcs, [], 3)
                except OverlapError:
                    #debug('Resampling exception')
                    continue

                #print('Resampling', len(Yo), 'pixels')

                bmask = self.get_brick_mask(scale, bwcs, brick)
                if bmask is not None:
                    # Assume bmask is a binary mask as large as the bwcs.
                    # Shift the Xi,Yi coords
                    I = np.flatnonzero(bmask[Yi+ylo, Xi+xlo])
                    if len(I) == 0:
                        continue
                    Yo = Yo[I]
                    Xo = Xo[I]
                    Yi = Yi[I]
                    Xi = Xi[I]

                    #print('get_brick_mask:', len(Yo), 'pixels')

                # print('xlo xhi', xlo,xhi, 'ylo yhi', ylo,yhi,
                #       'image shape', img.shape,
                #       'Xi range', Xi.min(), Xi.max(),
                #       'Yi range', Yi.min(), Yi.max(),
                #       'subwcs shape', subwcs.shape)

                if not np.all(np.isfinite(img[Yi,Xi])):
                    ok, = np.nonzero(np.isfinite(img[Yi,Xi]))
                    Yo = Yo[ok]
                    Xo = Xo[ok]
                    Yi = Yi[ok]
                    Xi = Xi[ok]

                    #print('finite pixels:', len(Yo))

                ok = self.filter_pixels(scale, img, wcs, subwcs, Yo,Xo,Yi,Xi)
                if ok is not None:
                    Yo = Yo[ok]
                    Xo = Xo[ok]
                    Yi = Yi[ok]
                    Xi = Xi[ok]

                    # print('filter pixels:', len(Yo))

                wt = self.get_pixel_weights(band, brick, scale)

                # DEBUG
                #nz = np.sum(rw == 0)

                rimg[Yo,Xo] += img[Yi,Xi] * wt
                rw  [Yo,Xo] += wt

                #print('Coadded', len(Yo), 'pixels;', (nz-np.sum(rw==0)), 'new')

                if False:
                    #import pylab as plt
                    dest = np.zeros(wcs.shape, bool)
                    dest[Yo,Xo] = True
                    source = np.zeros(bwcs.shape, bool)
                    source[Yi + ylo, Xi + xlo] = True
                    subsource = np.zeros(subwcs.shape, bool)
                    subsource[Yi, Xi] = True
                    destval = np.zeros(wcs.shape, float)
                    destval[Yo,Xo] = img[Yi,Xi]
                    plt.clf()
                    plt.subplot(2,3,1)
                    plt.imshow(dest, interpolation='nearest', origin='lower')
                    plt.title('dest')
                    plt.subplot(2,3,2)
                    plt.imshow(source, interpolation='nearest', origin='lower')
                    plt.title('source')
                    plt.subplot(2,3,4)
                    plt.imshow(subsource, interpolation='nearest', origin='lower')
                    plt.title('sub-source')
                    plt.subplot(2,3,5)
                    plt.imshow(destval, interpolation='nearest', origin='lower',
                               vmin=-0.001, vmax=0.01)
                    plt.title('dest')

                    plt.subplot(2,3,3)
                    plt.imshow(rimg / np.maximum(rw, 1e-18),
                               interpolation='nearest', origin='lower',
                               vmin=-0.001, vmax=0.01)
                    plt.title('rimg')
                    plt.subplot(2,3,6)
                    plt.imshow(rw, interpolation='nearest', origin='lower')
                    plt.title('rw')
                    plt.savefig('render-%s-%s.png' % (brickname, band))

            #print('Median image weight:', np.median(rw.ravel()))
            rimg /= np.maximum(rw, 1e-18)
            #print('Median image value:', np.median(rimg.ravel()))
            rimgs.append(rimg)
        return rimgs

    def get_brick_mask(self, scale, bwcs, brick):
        return None

    def filter_pixels(self, scale, img, wcs, sub_brick_wcs, Yo,Xo,Yi,Xi):
        return None

    def get_pixel_weights(self, band, brick, scale, **kwargs):
        return 1.

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
                # allow ver=1 for unknown versions
                if ver != 1:
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

        # For retrieving a single-CCD cutout, not coadd
        #ccd = req.GET.get('ccd', None)
        #decam-432057-S26

        if not 'pixscale' in req.GET and 'zoom' in req.GET:
            zoom = int(req.GET.get('zoom'))
            pixscale = pixscale * 2**(native_zoom - zoom)
            print('Request has zoom=', zoom, ': setting pixscale=', pixscale)

        if bands is not None:
            bands = self.parse_bands(bands)
        if bands is None:
            bands = self.get_bands()


        if 'subimage' in req.GET:
            from astrometry.libkd.spherematch import match_radec
            import tempfile
            import numpy as np
            bricks = self.get_bricks()
            # HACK
            #brickrad = 3600. * 0.262 / 2 * np.sqrt(2.) / 3600.
            I,J,d = match_radec(ra, dec, bricks.ra, bricks.dec, 1., nearest=True)
            if len(I) == 0:
                return HttpResponse('no overlap')
            brick = bricks[J[0]]
            print('RA,Dec', ra,dec, 'in brick', brick.brickname)
            scale = 0
            f,outfn = tempfile.mkstemp(suffix='.fits')
            os.close(f)
            os.unlink(outfn)
            fitsio.write(outfn, None, header=hdr, clobber=True)
            for band in bands:
                fn = self.get_filename(brick, band, scale)
                print('Image filename', fn)
                wcs = self.read_wcs(brick, band, scale, fn=fn)
                if wcs is None:
                    continue
                ok,xx,yy = wcs.radec2pixelxy(ra, dec)
                print('x,y', xx,yy)
                H,W = wcs.shape
                xx = int(np.round(xx - width/2)) - 1
                x0 = max(0, xx)
                x1 = min(x0 + width, W)
                yy = int(np.round(yy - height/2)) - 1
                y0 = max(0, yy)
                y1 = min(y0 + height, H)
                slc = (slice(y0, y1), slice(x0, x1))
                subwcs = wcs.get_subimage(x0, y0, x1-x0, y1-y0)
                try:
                    img = self.read_image(brick, band, 0, slc, fn=fn)
                except Exception as e:
                    print('Failed to read image:', e)
                    continue
                ivfn = self.get_base_filename(brick, band, invvar=True)
                print('Invvar filename', ivfn)
                iv = self.read_image(brick, band, 0, slc, fn=ivfn)
                hdr = fitsio.FITSHDR()
                self.populate_fits_cutout_header(hdr)
                hdr['BAND'] = band
                subwcs.add_to_header(hdr)
                # Append image to FITS file
                fitsio.write(outfn, img, header=hdr)
                # Add invvar
                hdr['IMAGETYP'] = 'invvar'
                fitsio.write(outfn, iv, header=hdr)
            fn = 'cutout_%.4f_%.4f.fits' % (ra,dec)
            return send_file(outfn, 'image/fits', unlink=True, filename=fn)


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

     
class PhatLayer(MapLayer):
    def __init__(self, name, **kwargs):
        import fitsio
        from astrometry.util.util import Tan
        #from astrometry.util.util import anwcs_open_wcslib
        super(PhatLayer, self).__init__(name, **kwargs)
        self.nativescale = 17
        self.pixscale = 0.05
        fn = os.path.join(settings.DATA_DIR, 'm31_full.fits')
        self.fits = fitsio.FITS(fn)[0]
        #self.wcs = anwcs_open_wcslib(fn, 0)
        self.wcs = Tan(fn, 0)
        #print('WCS:', self.wcs)

    def read_image(self, brick, band, scale, slc, fn=None):
        import numpy as np
        img = super(PhatLayer,self).read_image(brick, band, scale, slc, fn=fn)
        return img.astype(np.float32)

    def get_bands(self):
        ### FIXME
        return 'BGR'

    def get_base_filename(self, brick, band, **kwargs):
        #return os.path.join(settings.DATA_DIR, 'm31_full.fits')
        return os.path.join(settings.DATA_DIR, 'm31_full_%s.fits' % band)

    def get_scaled_filename(self, brick, band, scale):
        #return os.path.join(settings.DATA_DIR, 'm31_full_scale%i.fits' % scale)
        return os.path.join(settings.DATA_DIR, 'm31_full_%s_scale%i.fits' % (band, scale))

    def render_into_wcs(self, wcs, zoom, x, y, bands=None, general_wcs=False,
                        scale=None, tempfiles=None):
        import numpy as np
        from astrometry.util.resample import resample_with_wcs, OverlapError

        if scale is None:
            scale = self.get_scale(zoom, x, y, wcs)

        #if bricks is None or len(bricks) == 0:
        #    print('No bricks touching WCS')
        #    return None

        if bands is None:
            bands = self.get_bands()

        W = int(wcs.get_width())
        H = int(wcs.get_height())
        r,d = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                                [1,H/2,H,H,H,H/2,1,1])[-2:]

        #print('Tile RA,Decs:', r,d)

        rimgs = []
        # scaled down.....
        # call get_filename to possibly generate scaled version
        for band in bands:
            brick = None
            fn = self.get_filename(brick, band, scale, tempfiles=tempfiles)
            print('scale', scale, 'band', band, 'fn', fn)

            try:
                bwcs = self.read_wcs(brick, band, scale, fn=fn)
                if bwcs is None:
                    print('No such file:', brick, band, scale, 'fn', fn)
                    continue
            except:
                print('Failed to read WCS:', brick, band, scale, 'fn', fn)
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

            #print('My WCS xx,yy', xx, yy, 'imW,H', imW, imH, 'xlohi', xlo,xhi, 'ylohi', ylo,yhi)

            if xlo >= xhi or ylo >= yhi:
                print('No pixel overlap')
                return

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

            #print('Read image slice', img.shape)

            try:
                Yo,Xo,Yi,Xi,nil = resample_with_wcs(wcs, subwcs, [], 3)
            except OverlapError:
                #debug('Resampling exception')
                return

            rimg = np.zeros((H,W), np.float32)
            rimg[Yo,Xo] = img[Yi,Xi]
            rimgs.append(rimg)

        return rimgs

    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        sz = imgs[0].shape
        #mapping = np.zeros(256, np.uint8)
        lo,hi = 0.15, 0.8
        mapping = np.clip(np.round((np.arange(256) - lo*255) / (hi - lo)), 0, 255).astype(np.uint8)
        rgb = np.zeros((sz[0],sz[1],3), np.uint8)
        for i,img in zip([2,1,0], imgs):
            rgb[:,:,i] = mapping[img.astype(int)]
        return rgb

class M33Layer(PhatLayer):
    '''
# Image files:
tifftopnm data/m33/M33_F814W_F475W_mosaic_181216_MJD.tif | ppmtorgb3 -
pamflip -tb -- -.red | an-pnmtofits -o data/m33/m33-R.fits -v &
pamflip -tb -- -.grn | an-pnmtofits -o data/m33/m33-G.fits -v &
pamflip -tb -- -.blu | an-pnmtofits -o data/m33/m33-B.fits -v &

# WCS header:
hdr = fitsio.read_header('/Users/dstn/Downloads/F475W_wcs.fits')
outhdr = fitsio.FITSHDR()
for key in ['SIMPLE', 'BITPIX', 'NAXIS', 'WCSAXES', 'CRPIX1', 'CRPIX2', 'CTYPE1', 'CTYPE2', 'CRVAL1', 'CRVAL2']:
    v = hdr[key]
    outhdr[key] = v
outhdr
outhdr['CD1_1'] = hdr['CDELT1'] * hdr['PC1_1']
outhdr['CD1_2'] = hdr['CDELT1'] * hdr['PC1_2']
outhdr['CD2_1'] = hdr['CDELT2'] * hdr['PC2_1']
outhdr['CD2_2'] = hdr['CDELT2'] * hdr['PC2_2']
outhdr['IMAGEW'] = 32073
outhdr['IMAGEH'] = 41147
fitsio.write('/tmp/m33-wcs.fits', None, header=outhdr)
'''

    def __init__(self, name, **kwargs):
        ## HACK -- don't call the PhatLayer constructor!
        #super(M33Layer, self).__init__(name, **kwargs)
        super(PhatLayer, self).__init__(name, **kwargs)
        self.nativescale = 17
        self.pixscale = 0.035
        #fn = self.get_base_filname(None, None)
        #self.fits = fitsio.FITS(fn)[0]
        #fn = os.path.join(settings.DATA_DIR, 'm33', 'F475W_wcs.fits')
        #fn = os.path.join(settings.DATA_DIR, 'm33', 'm33-wcs.fits')
        fn = os.path.join(settings.DATA_DIR, 'm33', 'm33-wcs814.fits')
        #self.wcs = anwcs_open_wcslib(fn, 0)
        from astrometry.util.util import Tan
        self.wcs = Tan(fn, 0)
        print('M33 WCS: center', self.wcs.radec_center())

    def read_wcs(self, brick, band, scale, fn=None):
        if scale == 0:
            return self.wcs
        return super(M33Layer, self).read_wcs(brick, band, scale, fn=fn)

    def get_bands(self):
        return 'RGB'

    def get_base_filename(self, brick, band, **kwargs):
        return os.path.join(settings.DATA_DIR, 'm33', 'm33-%s.fits' % band)

    def get_scaled_filename(self, brick, band, scale):
        return os.path.join(settings.DATA_DIR, 'm33', 'm33-%s-scale%i.fits' % (band, scale))

    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        #for img in imgs:
        #    print('Image', img.shape, img.dtype, img.min(), img.max())
        return np.dstack(imgs) / 255.
        # sz = imgs[0].shape
        # rgb = np.zeros((sz[0],sz[1],3), np.uint8)
        # for i,img in enumerate(imgs):
        #     rgb[:,:,i] = img
        # return rgb

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

    def get_base_filename(self, brick, band, invvar=False, **kwargs):
        brickname = brick.brickname
        if invvar:
            return self.survey.find_file('invvar', brick=brickname, band=band)
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

class DecalsInvvarLayer(DecalsLayer):
    def get_scale(self, zoom, x, y, wcs):
        return 0
    def create_scaled_image(self, *args, **kwargs):
        return None
    def get_scaled_filename(self, brick, band, scale):
        return None


class DecalsDr3Layer(DecalsLayer):
    '''The data model changed (added .fz compression) as of DR5; this
    class retrofits pre-DR5 filenames.
    '''
    def get_base_filename(self, brick, band, **kwargs):
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

        ro = settings.READ_ONLY_BASEDIR
        if ro:
            print('Read-only; not creating scaled', brick, band, scale)
            return None
        
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

    def get_filename(self, brick, band, scale, tempfiles=None):
        #print('RebrickedMixin.get_filename: brick', brick, 'band', band, 'scale', scale)
        if scale == 0:
            #return self.get_base_filename(brick, band)
            return super(RebrickedMixin, self).get_filename(brick, band, scale,
                                                            tempfiles=tempfiles)
        fn = self.get_scaled_filename(brick, band, scale)
        #print('Filename:', fn)
        if os.path.exists(fn):
            return fn
        fn = self.create_scaled_image(brick, band, scale, fn, tempfiles=tempfiles)
        if fn is None:
            return None
        if os.path.exists(fn):
            return fn
        return None

    def get_bricks_for_scale(self, scale):
        if scale in [0, None]:
            return self.get_bricks()
        scale = min(scale, 7)

        from astrometry.util.fits import fits_table
        import numpy as np
        from astrometry.libkd.spherematch import match_radec

        fn = os.path.join(self.basedir, 'survey-bricks-%i.fits.gz' % scale)
        print(self, 'Brick file:', fn, 'exists?', os.path.exists(fn))
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
        brickside = self.get_brick_size_for_scale(scale)
        brickside_small = self.get_brick_size_for_scale(scale-1)

        # Spherematch from smaller scale to larger scale bricks
        radius = (brickside + brickside_small) * np.sqrt(2.) / 2. * 1.01

        inds = match_radec(allbricks.ra, allbricks.dec, bsmall.ra, bsmall.dec, radius,
                           indexlist=True)

        haves = np.all(['has_%s' % band in bsmall.get_columns() for band in self.bands])
        print('Does bsmall have has_<band> columns:', haves)
        if haves:
            for b in self.bands:
                allbricks.set('has_%s' % b, np.zeros(len(allbricks), bool))

        keep = []
        for ia,I in enumerate(inds):
            #if (allbricks.dec[ia] > 80):
            #    print('Brick', allbricks.brickname[ia], ': matches', I)
            if I is None:
                continue

            # Check for actual RA,Dec box overlap, not spherematch possible overlap
            if haves:
                Igood = np.array(I)[(bsmall.dec2[I] >= allbricks.dec1[ia]) *
                                    (bsmall.dec1[I] <= allbricks.dec2[ia]) *
                                    (bsmall.ra2[I] >= allbricks.ra1[ia]) *
                                    (bsmall.ra1[I] <= allbricks.ra2[ia])]
                print('Brick', allbricks.brickname[ia], ':', len(I), 'spherematches', len(Igood), 'in box')
                if len(Igood) == 0:
                    continue
                hasany = False
                for b in self.bands:
                    hasband = np.any(bsmall.get('has_%s' % b)[Igood])
                    print('  has', b, '?', hasband)
                    if not hasband:
                        continue
                    hasany = True
                    allbricks.get('has_%s' % b)[ia] = True
                if not hasany:
                    continue
                keep.append(ia)

            else:
                good = np.any((bsmall.dec2[I] >= allbricks.dec1[ia]) *
                              (bsmall.dec1[I] <= allbricks.dec2[ia]) *
                              (bsmall.ra2[I] >= allbricks.ra1[ia]) *
                              (bsmall.ra1[I] <= allbricks.ra2[ia]))
                #if (allbricks.dec[ia] > 80):
                #    print('Keep?', good)
                if good:
                    keep.append(ia)
        keep = np.array(keep)
        allbricks.cut(keep)
        print('Cut generic bricks to', len(allbricks))
        allbricks.writeto(fn)
        print('Wrote', fn)
        return allbricks

    def get_brick_size_for_scale(self, scale):
        return 0.25 * 2**scale

    def bricks_touching_radec_box(self, ralo, rahi, declo, dechi, scale=None):
        import numpy as np
        bricks = self.get_bricks_for_scale(scale)

        print('Bricks touching RA,Dec box', ralo, rahi, 'Dec', declo, dechi, 'scale', scale)

        I, = np.nonzero((bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        ok = ra_ranges_overlap(ralo, rahi, bricks.ra1[I], bricks.ra2[I])
        I = I[ok]
        if len(I) == 0:
            return None
        return bricks[I]

        # # Hacky margin
        # m = { 7: 1. }.get(scale, 0.)
        # print(len(bricks), 'candidate bricks.  ra1,ra2 pairs:', listzip(bricks.ra1, bricks.ra2))
        # if rahi < ralo:
        #     I, = np.nonzero(np.logical_or(bricks.ra2 >= ralo,
        #                                   bricks.ra1 <= rahi) *
        #                     (bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        # else:
        #     I, = np.nonzero((bricks.ra1  <= rahi +m) * (bricks.ra2  >= ralo -m) *
        #                     (bricks.dec1 <= dechi+m) * (bricks.dec2 >= declo-m))
        # print('Returning', len(I), 'bricks')
        # #for i in I:
        # #    print('  Brick', bricks.brickname[i], 'RA', bricks.ra1[i], bricks.ra2[i], 'Dec', bricks.dec1[i], bricks.dec2[i])
        # if len(I) == 0:
        #     return None
        # return bricks[I]


        
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

class UniqueBrickMixin(object):
    '''For model and resid layers where only blobs within the brick's unique area
    are fit -- thus bricks should be masked to their unique area before coadding.
    '''
    def get_brick_mask(self, scale, bwcs, brick):
        if scale > 0:
            return None
        from legacypipe.utils import find_unique_pixels
        H,W = bwcs.shape
        U = find_unique_pixels(bwcs, W, H, None, 
                               brick.ra1, brick.ra2, brick.dec1, brick.dec2)
        return U

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
        print('SdssLayer.get_filename: brick', brickname, 'band', band, 'scale', scale, 'fn', fn)
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
    
### If we ever re-make the SDSS coadds, omit fields from this file:
## https://trac.sdss.org/browser/data/sdss/photolog/trunk/opfiles/opBadfields.par
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

class ReDecalsResidLayer(UniqueBrickMixin, ResidMixin, ReDecalsLayer):
    pass

class ReDecalsModelLayer(UniqueBrickMixin, ReDecalsLayer):
    pass



class LegacySurveySplitLayer(MapLayer):
    def __init__(self, name, top, bottom, decsplit):
        super(LegacySurveySplitLayer, self).__init__(name)
        self.layers = [top, bottom]
        self.top = top
        self.bottom = bottom
        self.decsplit = decsplit

        self.tilesplits = {}

        import numpy as np
        dec = decsplit
        fy = 1. - (np.log(np.tan(np.deg2rad(dec + 90)/2.)) - -np.pi) / (2.*np.pi)
        for zoom in range(0, 18):
            n = 2**zoom
            y = int(fy * n)
            print('Zoom', zoom, '-> y', y)
            X = get_tile_wcs(zoom, 0, y)
            wcs = X[0]
            ok,rr,dd = wcs.pixelxy2radec([1,1], [1,256])
            #print('Decs', dd)
            self.tilesplits[zoom] = y

    def get_bricks(self):
        BB = merge_tables([l.get_bricks() for l in self.layers])
        return BB

    def bricks_touching_radec_box(self, *args, **kwargs):
        BB = merge_tables([l.bricks_touching_radec_box(*args, **kwargs)
                           for l in self.layers])
        return BB

    # def get_filename(self, brick, band, scale, tempfiles=None):
    #     pass
    # 
    # def get_base_filename(self, brick, band, **kwargs):
    #     pass

    def render_into_wcs(self, wcs, zoom, x, y, general_wcs=False, **kwargs):
        
        ## FIXME -- generic WCS

        split = self.tilesplits[zoom]
        if y < split:
            return self.top.render_into_wcs(wcs, zoom, x, y,
                                            general_wcs=general_wcs, **kwargs)
        if y > split:
            return self.bottom.render_into_wcs(wcs, zoom, x, y,
                                               general_wcs=general_wcs, **kwargs)

        # both!
        topims = self.top.render_into_wcs(wcs, zoom, x, y,
                                          general_wcs=general_wcs, **kwargs)
        botims = self.bottom.render_into_wcs(wcs, zoom, x, y,
                                             general_wcs=general_wcs, **kwargs)

        if topims is None:
            return botims
        if botims is None:
            return topims

        import numpy as np
        x = np.empty(256)
        x[:] = 128.5
        y = np.arange(1, 256+1)
        ok,rr,dd = wcs.pixelxy2radec(x, y)
        I = np.flatnonzero(dd >= self.decsplit)
        for b,t in zip(botims, topims):
            b[I,:] = t[I,:]
        return botims

    def get_bands(self):
        return self.top.get_bands()
    def get_rgb(self, *args, **kwargs):
        return self.top.get_rgb(*args, **kwargs)
    def get_scale(self, *args):
        return self.top.get_scale(*args)

    def get_tile_filename(self, ver, zoom, x, y):
        '''Pre-rendered JPEG tile filename.'''
        print('SplitLayer.get_tile_filename: zoom', zoom, 'y', y)
        split = self.tilesplits[zoom]
        if y < split:
            fn = self.top.get_tile_filename(ver, zoom, x, y)
            print('Top fn', fn)
            return fn
            #return self.top.get_tile_filename(ver, zoom, x, y)
        if y > split:
            #return self.bottom.get_tile_filename(ver, zoom, x, y)
            fn = self.bottom.get_tile_filename(ver, zoom, x, y)
            print('Bottom fn', fn)
            return fn
            
        tilefn = os.path.join(self.tiledir,
                              '%i' % ver, '%i' % zoom, '%i' % x, '%i.jpg' % y)
        print('Middle:', tilefn)
        return tilefn



class DesLayer(ReDecalsLayer):

    def __init__(self, name):
        super(DesLayer, self).__init__(name, 'image', None)
        self.bricks = None
        self.dir = os.path.join(settings.DATA_DIR, name)

    def get_base_filename(self, brick, band, **kwargs):
        from glob import glob
        brickname = brick.brickname
        # DES filenames have a weird-ass string in them so glob
        # eg, "DES0000+0209_r2590p01_g.fits.fz"
        pat = os.path.join(self.dir, 'dr1_tiles', brickname,
                           '%s_*_%s.fits.fz' % (brickname, band))
        fns = glob(pat)
        print('Glob:', pat, '->', fns)
        assert(len(fns) <= 1)
        if len(fns) == 0:
            return None
        return fns[0]

    def get_bricks(self):
        if self.bricks is not None:
            return self.bricks
        from astrometry.util.fits import fits_table
        basedir = settings.DATA_DIR
        self.bricks = fits_table(os.path.join(basedir, self.name, 'des-dr1-tiles.fits'))
        self.bricks.rename('uramin', 'ra1')
        self.bricks.rename('uramax', 'ra2')
        self.bricks.rename('udecmin', 'dec1')
        self.bricks.rename('udecmax', 'dec2')
        self.bricks.rename('ra_cent', 'ra')
        self.bricks.rename('dec_cent', 'dec')
        self.bricks.rename('tilename', 'brickname')
        return self.bricks

    def bricks_touching_radec_box(self, ralo, rahi, declo, dechi, scale=None):
        import numpy as np
        bricks = self.get_bricks_for_scale(scale)
        I, = np.nonzero((bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        ok = ra_ranges_overlap(ralo, rahi, bricks.ra1[I], bricks.ra2[I])
        I = I[ok]
        if len(I) == 0:
            return None
        return bricks[I]

    def get_brick_size_for_scale(self, scale):
        if scale == 0:
            return 10000 * 0.263 / 3600.
        return 0.25 * 2**scale

    def populate_fits_cutout_header(self, hdr):
        hdr['SURVEY'] = 'DES'
        hdr['VERSION'] = 'DR1'
        hdr['IMAGETYP'] = 'image'

    def read_image(self, brick, band, scale, slc, fn=None):
        img = super(DesLayer,self).read_image(brick, band, scale, slc, fn=fn)
        if scale == 0:
            img /= 10.**((30. - 22.5) / 2.5)
        return img

    
class PS1Layer(MapLayer):
    def __init__(self, name):
        super(PS1Layer, self).__init__(name, nativescale=14, maxscale=6)
        self.pixscale = 0.25
        self.bricks = None
        self.rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)

    def get_bands(self):
        #return 'grz'
        return 'gri'

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

    def get_brick_mask(self, scale, bwcs, brick):
        if scale > 0:
            return None
        import numpy as np
        H,W = bwcs.shape
        print('Bwcs shape:', H,W)
        U = np.ones((H,W), bool)
        # Mask 10 pix at edges
        U[:10,:] = False
        U[-10:,:] = False
        U[:,:10] = False
        U[:,-10:] = False
        return U

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
        W = hdr['ZNAXIS1']
        H = hdr['ZNAXIS2']
        wcs = Tan(*[float(x) for x in [
                    hdr['CRVAL1'], hdr['CRVAL2'], hdr['CRPIX1'], hdr['CRPIX2'],
                    cd11, cd12, cd21, cd22, W, H]])
        return wcs
    
    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
            '%(scale)i%(band)s', '%(brickname).4s',
            'ps1' + '-%(brickname)s-%(band)s.fits')

    def get_rgb(self, imgs, bands, **kwargs):
        #return dr2_rgb(imgs, bands, **self.rgbkwargs)
        return sdss_rgb(imgs, bands)

    #def get_rgb(self, imgs, bands, **kwargs):
    #    return sdss_rgb(imgs, bands)

    def populate_fits_cutout_header(self, hdr):
        hdr['SURVEY'] = 'PS1'



class UnwiseLayer(MapLayer):
    def __init__(self, name, unwise_dir):
        super(UnwiseLayer, self).__init__(name, nativescale=13)
        self.bricks = None
        self.dir = unwise_dir
        self.pixscale = 2.75

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
        print('Unwise bricks touching RA,Dec box', ralo, rahi, declo, dechi)
        I, = np.nonzero((bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        ok = ra_ranges_overlap(ralo, rahi, bricks.ra1[I], bricks.ra2[I])
        I = I[ok]
        print('-> bricks', bricks.brickname[I])
        if len(I) == 0:
            return None
        return bricks[I]

    def get_base_filename(self, brick, band, **kwargs):
        brickname = brick.brickname
        brickpre = brickname[:3]
        fn = os.path.join(self.dir, brickpre, brickname,
                          'unwise-%s-w%s-img-u.fits' % (brickname, band))
        return fn
    
    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
            '%(scale)iw%(band)s',
            '%(brickname).3s', 'unwise-%(brickname)s-w%(band)s.fits')

    def get_rgb(self, imgs, bands, **kwargs):
        return _unwise_to_rgb(imgs, **kwargs)

    def populate_fits_cutout_header(self, hdr):
        print('unWISE populate FITS cutout header')
        hdr['SURVEY'] = 'unWISE'
        hdr['VERSION'] = self.name

'''
unWISE atlas: 18,240 tiles
desiutil.brick.Brick:
#B = Bricks(1.5)
#B.to_table().write('unwise-bricks-0.fits', format='fits')  # (18690 bricks)
Bricks(3.).to_table().write('unwise-bricks-1.fits', format='fits')  # (4750 bricks)
Bricks(6.).to_table().write('unwise-bricks-2.fits', format='fits')  # (1226)
Bricks(12.).to_table().write('unwise-bricks-3.fits', format='fits')  # (326)
Bricks(24.).to_table().write('unwise-bricks-4.fits', format='fits')  # (93)
'''

class RebrickedUnwise(RebrickedMixin, UnwiseLayer):

    def __init__(self, name, unwise_dir):
        super(RebrickedUnwise, self).__init__(name, unwise_dir)
        self.maxscale = 4
        self.pixelsize = 2048

    def get_fits_extension(self, scale, fn):
        if scale == 0:
            return 0
        return 1

    def get_scaled_wcs(self, brick, band, scale):
        #print('RebrickedUnwise: get_scaled_wcs')
        from astrometry.util.util import Tan
        size = self.pixelsize
        pixscale = self.pixscale * 2**scale
        cd = pixscale / 3600.
        crpix = size/2. + 0.5
        wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                  float(size), float(size))
        return wcs

    def bricks_within_range(self, ra, dec, radius, scale=None):
        from astrometry.libkd.spherematch import match_radec
        import numpy as np
        B = self.get_bricks_for_scale(scale)
        brad = self.pixelsize * self.pixscale/3600. * 2**scale * np.sqrt(2.)/2. * 1.01
        I,J,d = match_radec(ra, dec, B.ra, B.dec, radius + brad)
        return B[J]

    def get_bricks_for_scale(self, scale):
        if scale in [0, None]:
            return self.get_bricks()
        scale = min(scale, 4)
        from astrometry.util.fits import fits_table
        fn = os.path.join(settings.DATA_DIR, 'unwise-bricks-%i.fits' % scale)
        print('Unwise bricks for scale', scale, '->', fn)
        b = fits_table(fn)
        return b

    def bricks_touching_radec_box(self, ralo, rahi, declo, dechi, scale=None):
        '''
        Both RebrickedMixin and UnwiseLayer override this function -- here we have
        to merge the capabilities.
        '''
        import numpy as np
        bricks = self.get_bricks_for_scale(scale)
        print('(unwise) scale', scale, 'bricks touching RA,Dec box', ralo, rahi, declo, dechi)
        I, = np.nonzero((bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        ok = ra_ranges_overlap(ralo, rahi, bricks.ra1[I], bricks.ra2[I])
        I = I[ok]
        print('-> bricks', bricks.brickname[I])
        if len(I) == 0:
            return None
        return bricks[I]

class UnwiseCatalogModel(RebrickedUnwise):
    def __init__(self, name, basedir):
        super(UnwiseCatalogModel, self).__init__(name, basedir)
        self.basedir = basedir

    def get_base_filename(self, brick, band, **kwargs):
        brickname = brick.brickname
        brickpre = brickname[:3]
        fn = os.path.join(self.basedir, '%s.%s.mod.fits' % (brickname, band))
        return fn

    def get_fits_extension(self, scale, fn):
        return 1




class WssaLayer(RebrickedUnwise):
    def __init__(self, name):
        super(RebrickedUnwise, self).__init__(name, None)
        self.maxscale = 2
        self.pixelsize = 8000
        self.pixscale = 5.625

    def get_fits_extension(self, scale, fn):
        if scale == 0:
            return 0
        return 1

    def get_bricks(self):
        if self.bricks is not None:
            return self.bricks
        from astrometry.util.fits import fits_table
        basedir = settings.DATA_DIR
        self.bricks = fits_table(os.path.join(basedir, 'wssa', 'wssa-bricks.fits'))
        #'tiles','wisetile-index-allsky.fits.gz'))
        self.bricks.rename('fname','brickname')
        return self.bricks

    def get_bricks_for_scale(self, scale):
        if scale in [0, None]:
            return self.get_bricks()
        scale = min(scale, 2)
        from astrometry.util.fits import fits_table
        fn = os.path.join(settings.DATA_DIR, 'wssa', 'wssa-bricks-%i.fits' % scale)
        return fits_table(fn)

    def get_bands(self):
        return ['x']

    def get_base_filename(self, brick, band, **kwargs):
        basedir = settings.DATA_DIR
        #fn = os.path.join(basedir, 'wssa', 'tiles', brick.brickname + '.gz')
        fn = os.path.join(basedir, 'wssa', brick.brickname)
        return fn
    
    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
                            '%(scale)i', '%(brickname).3s', 'wssa-%(brickname)s.fits')

    def get_rgb(self, imgs, bands, **kwargs):
        return wssa_rgb(imgs, bands, **kwargs)

def wssa_rgb(imgs, bands, **kwargs):
    import numpy as np
    img = imgs[0]
    #print('Img pcts', np.percentile(img.ravel(), [25,50,75,90,95,99]))
    val = np.log10(np.maximum(img, 1.)) / 4.
    import matplotlib.cm
    rgb = matplotlib.cm.hot(val)
    return rgb

class GalexLayer(RebrickedUnwise):
    def __init__(self, name):
        super(GalexLayer, self).__init__(name, None)
        self.nativescale=12
        self.bricks = None
        self.pixscale = 1.5

    def create_coadd_image(self, brick, band, scale, fn, tempfiles=None):
        import numpy as np
        import fitsio
        import tempfile
        wcs = self.get_scaled_wcs(brick, band, scale)
        imgs = self.render_into_wcs(wcs, None, 0, 0, bands=[band], scale=scale-1,
                                    tempfiles=tempfiles)
        if imgs is None:
            return None
        img = imgs[0]
        img = img.astype(np.float32)
        hdr = fitsio.FITSHDR()
        wcs.add_to_header(hdr)
        trymakedirs(fn)
        dirnm = os.path.dirname(fn)
        f,tmpfn = tempfile.mkstemp(suffix='.fits.fz.tmp', dir=dirnm)
        os.close(f)
        os.unlink(tmpfn)
        compress = '[compress R 100,100; qz 4]'
        fitsio.write(tmpfn + compress, img, header=hdr, clobber=True)
        os.rename(tmpfn, fn)
        print('Wrote', fn)

    def create_scaled_image(self, brick, band, scale, fn, tempfiles=None):
        if scale == 0:
            print('Galex: create_scaled_image, scale', scale, '-> create_coadd')
            return self.create_coadd_image(brick, band, scale, fn, tempfiles=tempfiles)
        print('Galex: create_scaled_image, scale', scale, 'brick', brick.brickname)
        return super(GalexLayer, self).create_scaled_image(brick, band, scale, fn,
                                                           tempfiles=tempfiles)

    def get_galex_images(self):
        import numpy as np
        from astrometry.util.fits import fits_table
        basedir = settings.DATA_DIR
        bricks = fits_table(os.path.join(basedir, 'galex', 'galex-images.fits'))
        bricks.rename('ra_cent', 'ra')
        bricks.rename('dec_cent', 'dec')
        bricks.rename('have_n', 'has_n')
        bricks.rename('have_f', 'has_f')
        cosd = np.cos(np.deg2rad(bricks.dec))
        bricks.ra1 = bricks.ra - 3840*1.5/3600./2./cosd
        bricks.ra2 = bricks.ra + 3840*1.5/3600./2./cosd
        bricks.dec1 = bricks.dec - 3840*1.5/3600./2.
        bricks.dec2 = bricks.dec + 3840*1.5/3600./2.
        bricknames = []
        for tile,subvis in zip(bricks.tilename, bricks.subvis):
            if subvis == -999:
                bricknames.append(tile.strip())
            else:
                bricknames.append('%s_sg%02i' % (tile.strip(), subvis))
        bricks.brickname = np.array(bricknames)
        return bricks

    def get_filename(self, brick, band, scale, tempfiles=None):
        #print('galex get_filename: scale', scale, 'band', band, 'brick', brick.brickname)
        if scale == -1:
            return self.get_base_filename(brick, band)
        brickname = brick.brickname
        fnargs = dict(band=band, brickname=brickname, scale=scale)
        fn = self.get_scaled_pattern() % fnargs
        if not os.path.exists(fn):
            print('Creating', fn)
            self.create_scaled_image(brick, band, scale, fn, tempfiles=tempfiles)
            print('Created', fn)
        if not os.path.exists(fn):
            return None
        return fn

    def get_bricks(self):
        if self.bricks is not None:
            return self.bricks
        from astrometry.util.fits import fits_table
        basedir = settings.DATA_DIR
        # really just unwise-bricks-minus1.fits, if such a thing existed
        self.bricks = fits_table(os.path.join(basedir, 'galex-bricks.fits'))
        return self.bricks

    def get_bricks_for_scale(self, scale):
        if scale == -1:
            return self.get_galex_images()
        if scale in [0, None]:
            return self.get_bricks()
        scale = min(scale, 5)
        from astrometry.util.fits import fits_table
        ## Since GALEX has roughly twice the pixel resolution as WISE
        ## (1.5 vs 2.75), we'll just use the unwise bricks from scale-1.
        fn = os.path.join(settings.DATA_DIR, 'unwise-bricks-%i.fits' % (scale-1))
        print('Galex bricks for scale', scale, '->', fn)
        b = fits_table(fn)
        return b

    ###### hack
    # def bricks_touching_radec_box(self, ralo, rahi, declo, dechi, scale=None):
    #     '''
    #     Both RebrickedMixin and UnwiseLayer override this function -- here we have
    #     to merge the capabilities.
    #     '''
    #     import numpy as np
    #     bricks = self.get_bricks_for_scale(scale)
    #     print('Galex bricks scale', scale, 'touching RA,Dec box', ralo, rahi, declo, dechi)
    #     I, = np.nonzero((bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
    #     ok = ra_ranges_overlap(ralo, rahi, bricks.ra1[I], bricks.ra2[I])
    #     I = I[ok]
    #     print('-> bricks', bricks.brickname[I])
    #     if len(I) == 0:
    #         return None
    #     return bricks[I]

    def get_fits_extension(self, scale, fn):
        if scale == -1:
            return 0
        return 1

    def get_bands(self):
        return ['n','f']

    def filter_pixels(self, scale, img, wcs, sub_brick_wcs, Yo,Xo,Yi,Xi):
        #if scale > 0:
        if scale > -1:
            return None
        return (img[Yi,Xi] != 0.)

    def get_pixel_weights(self, band, brick, scale, **kwargs):
        #if scale == 0:
        if scale == -1:
            print('Image', brick.brickname, 'exptime', brick.nexptime, 'NUV', brick.fexptime, 'FUV')
            return brick.get(band + 'exptime')
        return 1.

    def read_wcs(self, brick, band, scale, fn=None):
        #if scale != 0:
        if scale != -1:
            return super(GalexLayer,self).read_wcs(brick, band, scale, fn=fn)
        #print('read_wcs: brick is', brick)
        from astrometry.util.util import Tan
        wcs = Tan(*[float(f) for f in
                    [brick.crval1, brick.crval2, brick.crpix1, brick.crpix2,
                     brick.cdelt1, 0., 0., brick.cdelt2, 3840., 3840.]])
        return wcs

    def get_base_filename(self, brick, band, **kwargs):
        basedir = settings.DATA_DIR
        fn = os.path.join(basedir, 'galex', brick.tilename.strip(),
                          '%s-%sd-intbgsub.fits.gz' % (brick.brickname, band))
        return fn
    
    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
            '%(scale)i%(band)s',
            '%(brickname).3s', 'galex-%(brickname)s-%(band)s.fits')

    def get_rgb(self, imgs, bands, **kwargs):
        return galex_rgb(imgs, bands, **kwargs)
        # myrgb = np.zeros((h,w,3), np.float32)
        # lo,hi = -0.005, 0.05
        # myrgb[:,:,0] = np.clip((nuv - lo) / (hi - lo), 0., 1.)
        # lo,hi = -0.0005, 0.005
        # myrgb[:,:,2] = np.clip((fuv - lo) / (hi - lo), 0., 1.)
        # myrgb[:,:,1] = np.clip((myrgb[:,:,0] + myrgb[:,:,2]*0.2), 0., 1.)
        # return myrgb

    def read_image(self, brick, band, scale, slc, fn=None):
        import fitsio
        if fn is None:
            fn = self.get_filename(brick, band, scale)
        print('Reading image from', fn)
        ext = self.get_fits_extension(scale, fn)
        f = fitsio.FITS(fn)[ext]
        if slc is None:
            img = f.read()
        else:
            img = f[slc]
        return img

def galex_rgb(imgs, bands, **kwargs):
    import numpy as np
    from scipy.ndimage.filters import uniform_filter, gaussian_filter
    nuv,fuv = imgs
    h,w = nuv.shape
    red = nuv * 0.206 * 2297
    blue = fuv * 1.4 * 1525
    #blue = uniform_filter(blue, 3)
    blue = gaussian_filter(blue, 1.)
    green = (0.2*blue + 0.8*red)

    red   *= 0.085
    green *= 0.095
    blue  *= 0.08
    nonlinearity = 2.5
    radius = red + green + blue
    val = np.arcsinh(radius * nonlinearity) / nonlinearity
    with np.errstate(divide='ignore', invalid='ignore'):
        red   = red   * val / radius
        green = green * val / radius
        blue  = blue  * val / radius
    mx = np.maximum(red, np.maximum(green, blue))
    mx = np.maximum(1., mx)
    red   /= mx
    green /= mx
    blue  /= mx
    rgb = np.clip(np.dstack((red, green, blue)), 0., 1.)
    return rgb


class TwoMassLayer(MapLayer):
    def __init__(self, name):
        super(TwoMassLayer, self).__init__(name, nativescale=12)
        self.bricks = None
        self.pixscale = 1.0

    def get_bricks(self):
        if self.bricks is not None:
            return self.bricks
        from astrometry.util.fits import fits_table
        basedir = settings.DATA_DIR
        self.bricks = fits_table(os.path.join(basedir, '2mass', '2mass-bricks.fits'))
        return self.bricks

    def get_bands(self):
        return ['j','h','k']

    def bricks_touching_radec_box(self, ralo, rahi, declo, dechi, scale=None):
        import numpy as np
        bricks = self.get_bricks()
        print('2MASS bricks touching RA,Dec box', ralo, rahi, declo, dechi)
        I, = np.nonzero((bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        ok = ra_ranges_overlap(ralo, rahi, bricks.ra1[I], bricks.ra2[I])
        I = I[ok]
        print('-> bricks', bricks.brickname[I])
        if len(I) == 0:
            return None
        return bricks[I]

    def get_base_filename(self, brick, band, **kwargs):
        brickname = brick.brickname
        basedir = settings.DATA_DIR
        fn = os.path.join(basedir, '2mass', '%si%s.fits' % (band, brickname))
        return fn
    
    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
            '%(scale)i%(band)s',
            '%(brickname).3s', '2mass-%(brickname)s-%(band)s.fits')

    def get_rgb(self, imgs, bands, **kwargs):
        rgb = sdss_rgb(imgs, bands,
                       scales=dict(j=0.0015,
                                   h=0.0009, #23,
                                   k=0.0009,))
        return rgb

    def read_image(self, brick, band, scale, slc, fn=None):
        import fitsio
        if fn is None:
            fn = self.get_filename(brick, band, scale)
        print('Reading image from', fn)
        ext = self.get_fits_extension(scale, fn)
        f = fitsio.FITS(fn)[ext]

        if band in ['h','k'] and scale == 0:
            import numpy as np
            from tractor.splinesky import SplineSky
            from scipy.ndimage.filters import uniform_filter
            from scipy.ndimage.morphology import binary_dilation

            # re-estimate sky
            img = f.read()
            hdr = f.read_header()
            sky = hdr['SKYVAL']
            zpscale = 10.**((hdr['MAGZP'] - 22.5) / 2.5)
            img = (img - sky) / zpscale
            skysig = hdr['SKYSIG']
            skysig /= zpscale

            boxsize = 128
            good = (np.abs(img) < 5.*skysig) * np.isfinite(img)
            skyobj = SplineSky.BlantonMethod(img, good, boxsize)
            skymod = np.zeros_like(img)
            skyobj.addTo(skymod)

            # Now mask bright objects in a boxcar-smoothed (image - initial sky model)
            # Smooth by a boxcar filter before cutting pixels above threshold --
            boxcar = 5
            # Sigma of boxcar-smoothed image
            bsig1 = skysig / boxcar
            masked = np.abs(uniform_filter(img-skymod, size=boxcar, mode='constant')
                            > (3.*bsig1))
            masked = binary_dilation(masked, iterations=3)
            good[masked] = False
            # Now find the final sky model using that more extensive mask
            skyobj = SplineSky.BlantonMethod(img, good, boxsize)
            skymod[:,:] = 0.
            skyobj.addTo(skymod)
            img -= skymod
            if slc is not None:
                img = img[slc]
            return img

        if slc is None:
            img = f.read()
        else:
            img = f[slc]
        if scale == 0:
            import numpy as np
            hdr = f.read_header()
            sky = hdr['SKYVAL']
            zpscale = 10.**((hdr['MAGZP'] - 22.5) / 2.5)
            img = (img - sky) / zpscale
            #img[np.logical_not(np.isfinite)] = 0.
        return img

    def read_wcs(self, brick, band, scale, fn=None):
        if scale != 0:
            return super(TwoMassLayer,self).read_wcs(brick, band, scale, fn=fn)
        #print('read_wcs: brick is', brick)
        from astrometry.util.util import Tan
        wcs = Tan(*[float(f) for f in
                    [brick.crval1, brick.crval2, brick.crpix1, brick.crpix2,
                     brick.cd11, brick.cd12, brick.cd21, brick.cd22, brick.width, brick.height]])
        wcs.sin = True
        return wcs



class VlassLayer(RebrickedMixin, MapLayer):
    # Native bricks ~ 1 deg ^ 2

    def __init__(self, name):
        super(VlassLayer, self).__init__(name, nativescale=12)
        self.pixscale = 1.0
        self.bands = self.get_bands()
        self.pixelsize = 3744 # 3600 * 1.04
        self.maxscale = 6

    def get_bricks(self):
        from astrometry.util.fits import fits_table
        return fits_table(os.path.join(self.basedir, 'vlass-tiles.fits'))

    def get_bands(self):
        return [1]

    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        assert(len(imgs) == 1)
        img = imgs[0]
        H,W = img.shape
        mn,mx = -0.0003, 0.003
        gray = np.clip(255. * ((img-mn) / (mx-mn)), 0., 255.).astype(np.uint8)
        rgb = np.zeros((H,W,3), np.uint8)
        rgb[:,:,:] = gray[:,:,np.newaxis]
        return rgb

    def get_base_filename(self, brick, band, **kwargs):
        return os.path.join(self.basedir, brick.filename)

    def get_fits_extension(self, scale, fn):
        if scale == 0:
            return 0
        return 1

    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
            '%(scale)i', '%(brickname).3s',
            'vlass-%(brickname)s.fits')

    def read_image(self, brick, band, scale, slc, fn=None):
        extend = (scale == 0 and slc is not None and len(slc) == 2)
        if extend:
            slc = (slice(0,1), slice(0,1)) + slc
        img = super(VlassLayer, self).read_image(brick, band, scale, slc, fn=fn)
        if extend:
            img = img[0,0,:,:]
        return img

    def get_bricks_for_scale(self, scale):
        if scale in [0, None]:
            return self.get_bricks()
        scale = min(scale, self.maxscale)
        from astrometry.util.fits import fits_table
        fn = os.path.join(self.basedir, 'vlass-bricks-%i.fits' % scale)
        print('VLASS bricks for scale', scale, '->', fn)
        b = fits_table(fn)
        return b

    def get_scaled_wcs(self, brick, band, scale):
        from astrometry.util.util import Tan
        size = self.pixelsize
        pixscale = self.pixscale * 2**scale
        cd = pixscale / 3600.
        crpix = size/2. + 0.5
        wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                  float(size), float(size))
        return wcs


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
            'mzls bass-dr4-model': 'mzls+bass-dr4-model',
            'mzls bass-dr4-resid': 'mzls+bass-dr4-resid',

            'mzls bass-dr6': 'mzls+bass-dr6',
            'mzls bass-dr6-model': 'mzls+bass-dr6-model',
            'mzls bass-dr6-resid': 'mzls+bass-dr6-resid',

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

def _unwise_to_rgb(imgs, bands=[1,2],
                   scale1=1.,
                   scale2=1.,
                   arcsinh=1./20.,
                   mn=-20.,
                   mx=10000., 
                   w1weight=9.):
    import numpy as np
    img = imgs[0]
    H,W = img.shape

    ## FIXME
    assert(bands == [1,2])
    w1,w2 = imgs
    
    rgb = np.zeros((H, W, 3), np.uint8)

    # Old:
    # scale1 = 50.
    # scale2 = 50.
    # mn,mx = -1.,100.
    # arcsinh = 1.

    img1 = w1 / scale1
    img2 = w2 / scale2

    if arcsinh is not None:
        def nlmap(x):
            return np.arcsinh(x * arcsinh) / np.sqrt(arcsinh)

        # intensity -- weight W1 more
        bright = (w1weight * img1 + img2) / (w1weight + 1.)
        I = nlmap(bright)

        # color -- abs here prevents weird effects when, eg, W1>0 and W2<0.
        mean = np.maximum(1e-6, (np.abs(img1)+np.abs(img2))/2.)
        img1 = np.abs(img1)/mean * I
        img2 = np.abs(img2)/mean * I

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
    def get_ccds(self, **kwargs):
        import numpy as np
        dirnm = self.survey_dir
        # plug in a cut version of the CCDs table, if it exists
        cutfn = os.path.join(dirnm, 'ccds-cut.fits')
        if os.path.exists(cutfn):
            from astrometry.util.fits import fits_table
            C = fits_table(cutfn, **kwargs)
        else:
            C = super(MyLegacySurveyData,self).get_ccds(**kwargs)
            # HACK -- cut to photometric & not-blacklisted CCDs.
            # (not necessary when reading from kd.fits files, which are pre-cut)
            # C.photometric = np.zeros(len(C), bool)
            # I = self.photometric_ccds(C)
            # C.photometric[I] = True
            # C.ccd_cuts = self.ccd_cuts(C)
            # from legacypipe.survey import LegacySurveyData
            # bits = LegacySurveyData.ccd_cut_bits
            # C.blacklist_ok = ((C.ccd_cuts & bits['BLACKLIST']) == 0)
            # C.good_ccd = C.photometric * (C.ccd_cuts == 0)

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
        C = self.cleanup_ccds_table(C)
        return C

    def find_ccds(self, expnum=None, ccdname=None, camera=None):
        '''
        Returns a table of CCDs matching the given *expnum* (exposure
        number, integer), *ccdname* (string), and *camera* (string),
        if given.
        '''
        if expnum is not None and self.ccds is None:
            dirnm = self.survey_dir
            # fitscopy data/decals-dr5/ccds-cut.fits"[col expnum]" data/decals-dr5/ccds-cut-expnum.fits
            efn = os.path.join(dirnm, 'ccds-cut-expnum.fits')
            if os.path.exists(efn):
                from astrometry.util.fits import fits_table
                import numpy as np
                E = fits_table(efn)
                I = np.flatnonzero(E.expnum == expnum)
                print('Found', len(I), 'rows with expnum ==', expnum)

                cfn = os.path.join(dirnm, 'ccds-cut.fits')
                C = fits_table(cfn, rows=I)
                C = self.cleanup_ccds_table(C)
                if ccdname is not None:
                    C = C[C.ccdname == ccdname]
                if camera is not None:
                    C = C[C.camera == camera]
                return C

        return super(MyLegacySurveyData, self).find_ccds(expnum=expnum, ccdname=ccdname,
                                                         camera=camera)

class SplitSurveyData(MyLegacySurveyData):
    def __init__(self, north, south):
        super(SplitSurveyData, self).__init__()
        self.north = north
        self.south = south

    def get_bricks_readonly(self):
        if self.bricks is None:
            from astrometry.util.fits import merge_tables
            self.bricks = merge_tables([self.north.get_bricks_readonly(),
                                        self.south.get_bricks_readonly()])
        return self.bricks

    def get_ccds(self, **kwargs):
        from astrometry.util.fits import merge_tables
        import numpy as np
        n = self.north.get_ccds(**kwargs)
        n.is_north = np.ones(len(n), bool)
        s = self.south.get_ccds(**kwargs)
        s.is_north = np.zeros(len(s), bool)
        ccds = merge_tables([n, s], columns='fillzero')
        return ccds

    def ccds_touching_wcs(self, wcs, **kwargs):
        from astrometry.util.fits import merge_tables
        import numpy as np
        ns = []
        n = self.north.ccds_touching_wcs(wcs, **kwargs)
        print('ccds_touching_wcs: north', n)
        if n is not None:
            n.is_north = np.ones(len(n), bool)
            ns.append(n)
        s = self.south.ccds_touching_wcs(wcs, **kwargs)
        print('ccds_touching_wcs: south', s)
        if s is not None:
            s.is_north = np.zeros(len(s), bool)
            ns.append(s)
        if len(ns) == 0:
            return None
        return merge_tables(ns, columns='fillzero')

    def get_image_object(self, ccd, **kwargs):
        if ccd.is_north:
            return self.north.get_image_object(ccd, **kwargs)
        return self.south.get_image_object(ccd, **kwargs)

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
def get_survey(name):
    import numpy as np
    global surveys
    name = layer_to_survey_name(name)
    print('Survey name', name)

    if name in surveys:
        print('Cache hit for survey', name)
        return surveys[name]

    #debug('Creating LegacySurveyData() object for "%s"' % name)
    
    basedir = settings.DATA_DIR

    if name in [ 'decals-dr2', 'decals-dr3', 'decals-dr5', 'decals-dr7',
                 'mzls+bass-dr4', 'mzls+bass-dr6',
                 'decaps', 'eboss', 'ls-dr56', 'ls-dr67']:
        dirnm = os.path.join(basedir, name)
        print('survey_dir', dirnm)

        if name == 'decals-dr2':
            d = MyLegacySurveyData(survey_dir=dirnm, version='dr2')
        elif name == 'decaps':
            d = Decaps2LegacySurveyData(survey_dir=dirnm)
        elif name in ['mzls+bass-dr6']:
            # CCDs table has no 'photometric' etc columns.
            d = LegacySurveyData(survey_dir=dirnm)
        elif name == 'decals-dr7':
            # testing 1 2 3
            d = LegacySurveyData(survey_dir=dirnm,
                                 cache_dir=os.path.join(dirnm, 'dr7images'))
        elif name == 'ls-dr56':
            north = get_survey('mzls+bass-dr6')
            south = get_survey('decals-dr5')
            d = SplitSurveyData(north, south)
            d.drname = 'LegacySurvey DR5+DR6'
        elif name == 'ls-dr67':
            north = get_survey('mzls+bass-dr6')
            south = get_survey('decals-dr7')
            d = SplitSurveyData(north, south)
            d.drname = 'LegacySurvey DR6+DR7'
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
        elif name == 'mzls+bass-dr6':
            d.drname = 'MzLS+BASS DR6'
            d.drurl = 'http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr6/'
        elif name == 'decals-dr7':
            d.drname = 'DECaLS DR7'
            d.drurl = 'http://portal.nersc.gov/project/cosmo/data/legacysurvey/dr7/'
        elif name == 'decaps':
            d.drname = 'DECaPS'
            d.drurl = 'http://legacysurvey.org/'
        elif name == 'eboss':
            d.drname = 'eBOSS'
            d.drurl = 'http://legacysurvey.org/'

        print('Caching survey', name)
        surveys[name] = d
        return d

 
    if '/' in name or '.' in name:
        return None
    dirnm = os.path.join(basedir, name)
    print('checking for survey_dir', dirnm)
    if os.path.exists(dirnm):
        d = LegacySurveyData(survey_dir=dirnm)
        # d.drname = 'eBOSS'
        # d.drurl = 'http://legacysurvey.org/'
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

    layer = request_layer_name(req)
    D = get_survey(layer)
    if B is None:
        B = D.get_bricks_readonly()

    I = D.bricks_touching_radec_box(B, east, west, south, north)
    # Limit result size...
    #if len(I) > 10000:
    #    return HttpResponse(json.dumps(dict(bricks=[])),
    #                        content_type='application/json')
    I = I[:400]
    
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
            survey = get_survey(name)

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
    if len(J) == 0:
        return []
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
        from astrometry.util.starutil import radectoxyz, xyztoradec, degrees_between
        x1,y1,z1 = radectoxyz(east, north)
        x2,y2,z2 = radectoxyz(west, south)
        rc,dc = xyztoradec((x1+x2)/2., (y1+y2)/2., (z1+z2)/2.)
        # 0.15: SDSS field radius is ~ 0.13
        radius = 0.15 + degrees_between(east, north, west, south)/2.
        T = sdss_ccds_near(rc, dc, radius)
        if T is None:
            return HttpResponse(json.dumps(dict(polys=[])),
                                content_type='application/json')
        ccds = [dict(name='SDSS R/C/F %i/%i/%i' % (t.run, t.camcol, t.field),
                     radecs=[[t.ra1,t.dec1],[t.ra2,t.dec2],
                             [t.ra3,t.dec3],[t.ra4,t.dec4]],)
                     #run=int(t.run), camcol=int(t.camcol), field=int(t.field))
                for t in T]
        return HttpResponse(json.dumps(dict(polys=ccds)), content_type='application/json')

    if name == 'unwise-tiles':
        from astrometry.util.starutil import radectoxyz, xyztoradec, degrees_between
        from astrometry.libkd.spherematch import tree_open, tree_search_radec
        from astrometry.util.fits import fits_table
        x1,y1,z1 = radectoxyz(east, north)
        x2,y2,z2 = radectoxyz(west, south)
        rc,dc = xyztoradec((x1+x2)/2., (y1+y2)/2., (z1+z2)/2.)
        # 0.8: unWISE tile radius, approx.
        radius = 0.8 + degrees_between(east, north, west, south)/2.
        fn = os.path.join(settings.DATA_DIR, 'unwise-tiles.kd.fits')
        kd = tree_open(fn)
        I = tree_search_radec(kd, rc, dc, radius)
        print(len(I), 'unwise tiles within', radius, 'deg of RA,Dec (%.3f, %.3f)' % (rc,dc))
        if len(I) == 0:
            return HttpResponse(json.dumps(dict(polys=[])), content_type='application/json')
        # Read only the tiles within range.
        T = fits_table(fn, rows=I)
        '''
        W = H = 2048
        pixscale = 2.75
        wcs = Tan(0., 0., (W + 1) / 2., (H + 1) / 2.,
           -pixscale / 3600., 0., 0., pixscale / 3600., W, H)
        dr,dd = wcs.pixelxy2radec([1,1024.5,2048,2048,2048,1024.5,1,1,1],
             [1,1,1,1024.5,2048,2048,2048,1024.5,1])
        dr + (-360*(dr>180)), dd
        '''
        d = 0.78179176
        dr = np.array([ d, 0., -d, -d, -d, 0, d, d,  d])
        dd = np.array([-d,-d , -d,  0,  d, d, d, 0.,-d])

        polys = [dict(name=t.coadd_id,
                      radecs=list(zip(t.ra  + dr/np.cos(np.deg2rad(t.dec + dd)),
                                      t.dec + dd)))
                 for t in T]
        return HttpResponse(json.dumps(dict(polys=polys)), content_type='application/json')

    CCDS = _ccds_touching_box(north, south, east, west, Nmax=10000, name=name)
    print('CCDs in box for', name, ':', len(CCDS))
    if len(CCDS) == 0:
        return HttpResponse(json.dumps(dict(polys=[])), content_type='application/json')
        
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

def sdss_ccds_near(rc, dc, radius):
    from astrometry.libkd.spherematch import tree_open, tree_search_radec
    from astrometry.util.fits import fits_table
    fn = os.path.join(settings.DATA_DIR, 'sdss', 'sdss-fields-trimmed.kd.fits')
    kd = tree_open(fn, 'ccds')
    I = tree_search_radec(kd, rc, dc, radius)
    print(len(I), 'CCDs within', radius, 'deg of RA,Dec (%.3f, %.3f)' % (rc,dc))
    if len(I) == 0:
        return None
    # Read only the CCD-table rows within range.
    T = fits_table(fn, rows=I)
    T.cut(T.rerun == 301)
    return T

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
    elif name in ['decals-dr5', 'decals-dr7']:
        fn = os.path.join(settings.DATA_DIR, name, 'exposures.fits')
        if not os.path.exists(fn):
            import numpy as np
            survey = get_survey(name)
            ccds = survey.get_ccds_readonly()
            e,I = np.unique(ccds.expnum, return_index=True)
            exps = ccds[I]
            exps = touchup_ccds(exps, survey)
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
    plate = req.GET.get('plate', None)

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
    if plate is not None:
        plate = int(plate, 10)
        # don't use T.cut -- it's in the shared cache
        T = T[T.plate == plate]

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
    survey = get_survey(survey)
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

def ccd_detail(req, layer, ccd):
    layer = layer_name_map(layer)
    survey, c = get_ccd_object(layer, ccd)

    cols = c.columns()
    if 'cpimage' in cols:
        about = ('CCD %s, image %s, hdu %i; exptime %.1f sec, seeing %.1f arcsec' %
                 (ccd, c.cpimage, c.cpimage_hdu, c.exptime, c.fwhm*0.262))
        return HttpResponse(about)

    imgurl = reverse('image_data', args=[layer, ccd])
    dqurl  = reverse('dq_data', args=[layer, ccd])
    ivurl  = reverse('iv_data', args=[layer, ccd])
    imgstamp = reverse('image_stamp', args=[layer, ccd])
    flags = ''
    cols = c.columns()
    if 'photometric' in cols and 'blacklist_ok' in cols:
        flags = 'Photometric: %s.  Not-blacklisted: %s<br />' % (c.photometric, c.blacklist_ok)
    ooitext = ''
    if '_oki_' in c.image_filename:
        imgooiurl = imgurl + '?type=ooi'
        ooitext = '<li>image (ooi): <a href="%s">%s</a>' % (imgooiurl, ccd)
    if not 'seeing' in cols:
        pixscale = {'decam':   0.262,
                    'mosaic':  0.262,
                    '90prime': 0.454}.get(c.camera.strip(), 0.262)
        c.seeing = pixscale * c.fwhm
    if not 'date_obs' in cols:
        from astrometry.util.starutil_numpy import mjdtodate
        # c.mjd_obs -> c.date_obs, c.ut
        date = mjdtodate(c.mjd_obs)
        iso = date.isoformat()
        date,time = iso.split('T')
        c.date_obs = date
        c.ut = time[:12]

    about = html_tag + '''
<body>
CCD %s, image %s, hdu %i; exptime %.1f sec, seeing %.1f arcsec, fwhm %.1f pix, band %s, RA,Dec <a href="%s/?ra=%.4f&dec=%.4f">%.4f, %.4f</a>
<br />
%s
Observed MJD %.3f, %s %s UT
<ul>
<li>image: <a href="%s">%s</a>
%s
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
            imgurl, ccd,
            ooitext, ivurl, ccd, dqurl, ccd, imgstamp)
    about = about % args

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

def brick_detail(req, brickname, get_html=False, brick=None):
    import numpy as np

    brickname = str(brickname)
    layer = request_layer_name(req)
    layer = layer_to_survey_name(layer)
    survey = get_survey(layer)
    if brick is None:
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
            html.extend(ccds_overlapping_html(ccds, layer))

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

def format_jpl_url(ra, dec, ccd):
    jpl_url = reverse(jpl_lookup)
    return ('%s?ra=%.4f&dec=%.4f&date=%s&camera=%s' %
            (jpl_url, ra, dec, ccd.date_obs + ' ' + ccd.ut, ccd.camera.strip()))


def ccds_overlapping_html(ccds, layer, ra=None, dec=None):
    jplstr = ''
    if ra is not None:
        jplstr = '<th>JPL</th>'
    html = ['<table class="ccds"><thead><tr><th>name</th><th>exptime</th><th>seeing</th><th>propid</th><th>date</th><th>image</th><th>image (ooi)</th><th>weight map</th><th>data quality map</th>%s</tr></thead><tbody>' % jplstr]
    for ccd in ccds:
        ccdname = '%s %i %s %s' % (ccd.camera.strip(), ccd.expnum,
                                   ccd.ccdname.strip(), ccd.filter.strip())
        ccdtag = ccdname.replace(' ','-')
        imgurl = reverse('image_data', args=(layer, ccdtag))
        dqurl  = reverse('dq_data', args=(layer, ccdtag))
        ivurl  = reverse('iv_data', args=(layer, ccdtag))
        imgooiurl = imgurl + '?type=ooi'
        ooitext = ''
        if '_oki_' in ccd.image_filename:
            ooitext = '<a href="%s">ooi</a>' % imgooiurl
        jplstr = ''
        if ra is not None:
            jplstr = '<td><a href="%s">JPL</a></td>' % format_jpl_url(ra, dec, ccd)
        html.append(('<tr><td><a href="%s">%s</a></td><td>%.1f</td><td>%.2f</td>' +
                     '<td>%s</td><td>%s</td><td><a href="%s">%s</a></td><td>%s</td><td><a href="%s">oow</a></td><td><a href="%s">ood</a></td>%s</tr>') % (
                         reverse(ccd_detail, args=(layer, ccdtag)), ccdname,
                         ccd.exptime, ccd.seeing, ccd.propid, ccd.date_obs + ' ' + ccd.ut[:8],
                         imgurl, ccd.image_filename.strip(), ooitext, ivurl, dqurl,
                         jplstr))
    html.append('</tbody></table>')
    return html

def cutouts_coadd_psf(req):
    return cutouts_common(req, False, True)

def cutouts_tgz(req):
    return cutouts_common(req, True, False)

def cutouts(req):
    return cutouts_common(req, False, False)

def cutouts_common(req, tgz, copsf):
    from astrometry.util.util import Tan
    from astrometry.util.starutil_numpy import degrees_between
    import numpy as np
    from legacypipe.survey import wcs_for_brick

    ra = float(req.GET['ra'])
    dec = float(req.GET['dec'])

    # half-size in DECam pixels
    if copsf:
        size = 32
        bands = req.GET.get('bands', 'grz')
        bands = ''.join([b for b in bands if b in 'grz'])
    else:
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
    
    layer = request_layer_name(req)
    layer = layer_to_survey_name(layer)
    survey = get_survey(layer)
    CCDs = survey.ccds_touching_wcs(wcs)
    debug(len(CCDs), 'CCDs')
    CCDs = touchup_ccds(CCDs, survey)

    print('CCDs:', CCDs.columns())

    CCDs = CCDs[np.lexsort((CCDs.ccdname, CCDs.expnum, CCDs.filter))]

    if tgz or copsf:
        if tgz:
            import tempfile
            import fitsio
            tempdir = tempfile.TemporaryDirectory()
            datadir = 'data_%.4f_%.4f' % (ra, dec)
            subdir = os.path.join(tempdir.name, datadir)
            os.mkdir(subdir)
            print('Writing to', subdir)
            CCDs.ccd_x0 = np.zeros(len(CCDs), np.int16)
            CCDs.ccd_x1 = np.zeros(len(CCDs), np.int16)
            CCDs.ccd_y0 = np.zeros(len(CCDs), np.int16)
            CCDs.ccd_y1 = np.zeros(len(CCDs), np.int16)
            imgfns = []
            keepccds = np.zeros(len(CCDs), bool)
        else:
            sumpsf = dict([(b,0.) for b in bands])
            sumiv  = dict([(b,0.) for b in bands])
            CCDs = CCDs[np.array([f in bands for f in CCDs.filter])]

        for iccd,ccd in enumerate(CCDs):
            im = survey.get_image_object(ccd)
            print('Got', im)
            imwcs = im.get_wcs()
            ok,cx,cy = imwcs.radec2pixelxy([east,  west,  west,  east ],
                                           [north, north, south, south])
            H,W = im.shape
            x0 = int(np.clip(np.floor(min(cx)), 0, W-1))
            x1 = int(np.clip(np.ceil (max(cx)), 0, W-1))
            y0 = int(np.clip(np.floor(min(cy)), 0, H-1))
            y1 = int(np.clip(np.ceil (max(cy)), 0, H-1))
            if x0 == x1 or y0 == y1:
                continue

            slc = (slice(y0, y1+1), slice(x0, x1+1))
            tim = im.get_tractor_image(slc, pixPsf=True, splinesky=True,
                                       subsky=True, nanomaggies=False,
                                       pixels=tgz, dq=tgz, normalizePsf=copsf)
            if tim is None:
                continue
            psf = tim.getPsf()
            th,tw = tim.shape
            psfimg = psf.getImage(tw/2, th/2)
            ivdata = tim.getInvvar()

            if copsf:
                if np.all(ivdata == 0):
                    continue
                iv = np.median(ivdata[ivdata > 0])
                sumpsf[tim.band] += psfimg * iv
                sumiv [tim.band] += iv
                continue

            keepccds[iccd] = True
            CCDs.ccd_x0[iccd] = x0
            CCDs.ccd_y0[iccd] = y0
            CCDs.ccd_x1[iccd] = x1+1
            CCDs.ccd_y1[iccd] = y1+1

            psfex = psf.psfex
            imgdata = tim.getImage()
            dqdata = tim.dq
            # Adjust the header WCS by x0,y0
            crpix1 = tim.hdr['CRPIX1']
            crpix2 = tim.hdr['CRPIX2']
            tim.hdr['CRPIX1'] = crpix1 - x0
            tim.hdr['CRPIX2'] = crpix2 - y0

            outfn = '%s-%08i-%s-image.fits' % (ccd.camera, ccd.expnum, ccd.ccdname)
            imgfns.append(outfn)
            ofn = os.path.join(subdir, outfn)
            fitsio.write(ofn, None, header=tim.primhdr, clobber=True)
            fitsio.write(ofn, imgdata, header=tim.hdr, extname=ccd.ccdname)

            outfn = '%s-%08i-%s-weight.fits' % (ccd.camera, ccd.expnum, ccd.ccdname)
            ofn = os.path.join(subdir, outfn)
            fitsio.write(ofn, None, header=tim.primhdr, clobber=True)
            fitsio.write(ofn, ivdata, header=tim.hdr, extname=ccd.ccdname)

            outfn = '%s-%08i-%s-dq.fits' % (ccd.camera, ccd.expnum, ccd.ccdname)
            ofn = os.path.join(subdir, outfn)
            fitsio.write(ofn, None, header=tim.primhdr, clobber=True)
            fitsio.write(ofn, dqdata, header=tim.hdr, extname=ccd.ccdname)

            outfn = '%s-%08i-%s-psfex.fits' % (ccd.camera, ccd.expnum, ccd.ccdname)
            ofn = os.path.join(subdir, outfn)
            psfex.fwhm = tim.psf_fwhm
            psfex.writeto(ofn)

            outfn = '%s-%08i-%s-psfimg.fits' % (ccd.camera, ccd.expnum, ccd.ccdname)
            ofn = os.path.join(subdir, outfn)
            fitsio.write(ofn, psfimg, header=tim.primhdr, clobber=True)


        if copsf:
            keepbands = []
            psf = []
            for b in bands:
                if sumiv[b] == 0:
                    continue
                keepbands.append(b)
                psf.append(sumpsf[b] / sumiv[b])
            bands = keepbands
            if len(bands) == 0:
                return HttpResponse('no CCDs overlapping')

            # if len(bands) == 1:
            #     cube = psf[0]
            # else:
            #     h,w = psf[0].shape
            #     cube = np.empty((len(bands), h, w), np.float32)
            #     for i,im in enumerate(psf):
            #         cube[i,:,:] = im
            import tempfile
            import fitsio
            f,fn = tempfile.mkstemp(suffix='.fits')
            os.close(f)
            hdr = fitsio.FITSHDR()
            # Primary header
            hdr['BANDS'] = ''.join(bands)
            for i,b in enumerate(bands):
                hdr['BAND%i' % i] = b
            # Clobber first hdu; append subsequent ones
            clobber = True
            for i,(band,bandpsf) in enumerate(zip(bands, psf)):
                hdr['BAND'] = band
                fitsio.write(fn, bandpsf, header=hdr, clobber=clobber)
                clobber=False
                hdr = fitsio.FITSHDR()

            return send_file(fn, 'image/fits', unlink=True,
                             filename='copsf_%.4f_%.4f.fits' % (ra,dec))
            
        CCDs.cut(keepccds)
        CCDs.image_filename = np.array(imgfns)
        ccdfn = os.path.join(subdir, 'ccds.fits')
        CCDs.writeto(ccdfn)

        cmd = ('cd %s && tar czf %s.tgz %s' % (tempdir.name, datadir, datadir))
        print(cmd)
        os.system(cmd)
        fn = os.path.join(tempdir.name, '%s.tgz' % datadir)

        return send_file(fn, 'application/gzip', filename='%s.tgz' % datadir)

    ccds = []
    for i in range(len(CCDs)):
        c = CCDs[i]
        try:
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

    url = req.build_absolute_uri('/') + settings.ROOT_URL + '/cutout_panels/%s/%i/%s/'
    # Deployment: http://{s}.DOMAIN/...
    url = url.replace('://www.', '://')
    url = url.replace('://', '://%s.')
    domains = settings.SUBDOMAINS

    ccdsx = []
    for i,(ccd,x,y) in enumerate(ccds):
        fn = ccd.image_filename.replace(settings.DATA_DIR + '/', '')
        theurl = url % (domains[i%len(domains)], layer, int(ccd.expnum), ccd.ccdname.strip()) + '?x=%i&y=%i&size=%i' % (x, y, size*2)
        print('CCD columns:', ccd.columns())
        ccdsx.append(('<br/>'.join(['CCD %s %i %s, %.1f sec (x,y = %i,%i)' % (ccd.filter, ccd.expnum, ccd.ccdname, ccd.exptime, x, y),
                                    '<small>(%s [%i])</small>' % (fn, ccd.image_hdu),
                                    '<small>(observed %s @ %s)</small>' % (ccd.date_obs, ccd.ut),
                                    '<small><a href="%s">Look up in JPL Small Bodies database</a></small>' % format_jpl_url(ra, dec, ccd),]),
                      theurl))
    return render(req, 'cutouts.html',
                  dict(ra=ra, dec=dec, ccds=ccdsx, name=layer, layer=layer,
                       drname=survey.drname,
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

    latlongs = dict(decam=dict(lon='70.81489', lon_u='W',
                               lat='30.16606', lat_u='S',
                               alt='2215.0', alt_u='m'),
                    mosaic=dict(lon='111.6003', lon_u='W',
                                lat = '31.9634', lat_u='N',
                                alt='2120.0', alt_u='m'))
    latlongs.update({'90prime': dict(lon='111.6', lon_u='W',
                                     lat='31.98', lat_u='N',
                                     alt='2120.0', alt_u='m')})

    latlongargs = latlongs[camera]

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
        survey = get_survey(name)
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

def cutout_psf(req, layer=None, expnum=None, extname=None):
    x = int(req.GET['x'], 10)
    y = int(req.GET['y'], 10)
    # half-size in DECam pixels
    size = int(req.GET.get('size', '100'), 10)
    size = min(200, size)
    size = size // 2

    layer = clean_layer_name(layer)
    layer = layer_to_survey_name(layer)
    survey = get_survey(layer)
    ccd = _get_ccd(expnum, extname, survey=survey)
    print('CCD:', ccd)
    im = survey.get_image_object(ccd)
    print('Image object:', im)

    psf = read_psf_model(0, 0, pixPsf=True)
    print('Got PSF', psf)
    psfimg = psf.getImage(x, y)
    print('PSF img', psfimg.shape)
    ### FIXME



def cutout_panels(req, layer=None, expnum=None, extname=None):
    import pylab as plt
    import numpy as np

    x = int(req.GET['x'], 10)
    y = int(req.GET['y'], 10)

    # half-size in DECam pixels
    size = int(req.GET.get('size', '100'), 10)
    size = min(200, size)
    size = size // 2

    layer = clean_layer_name(layer)
    layer = layer_to_survey_name(layer)
    survey = get_survey(layer)
    ccd = _get_ccd(expnum, extname, survey=survey)
    print('CCD:', ccd)
    im = survey.get_image_object(ccd)
    print('Image object:', im)


    H,W = im.shape
    slc = (slice(max(0, y-size), min(H, y+size+1)),
           slice(max(0, x-size), min(W, x+size+1)))
    tim = im.get_tractor_image(slc=slc, gaussPsf=True, splinesky=True,
                               dq=False, invvar=False)
    #thelayer = get_layer(layer)
    #rgb = thelayer.get_rgb([tim.data], [tim.band])
    from legacypipe.survey import get_rgb
    rgb = get_rgb([tim.data], [tim.band], mnmx=(-1,100.), arcsinh=1.)

    index = dict(g=2, r=1, z=0)[tim.band]
    bw = rgb[:,:,index]
    print('BW', bw.shape, bw.dtype)

    import tempfile
    f,jpegfn = tempfile.mkstemp(suffix='.jpg')
    os.close(f)
    plt.imsave(jpegfn, bw, vmin=0, vmax=1, cmap='gray', origin='lower')
    #mn,mx = np.percentile(img.ravel(), [25, 99])
    #save_jpeg(jpegfn, destimg, origin='lower', cmap='gray',
    #          vmin=mn, vmax=mx)
    return send_file(jpegfn, 'image/jpeg', unlink=True)


    ############################

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
    # D = get_survey(name=name)
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

    imgtype = req.GET.get('type', None)
    print('imgtype: "%s"' % imgtype)
    if imgtype == 'ooi':
        fn = fn.replace('_oki_', '_ooi_')

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
    H,W = pix.shape
    if H > W:
        pix = pix.T
    #if 'decals' in surveyname:
    #    # rotate image
    #    pix = pix.T

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

    elif name == 'ls-dr56':
        dr5 = get_layer('decals-dr5')
        dr6 = get_layer('mzls+bass-dr6')
        layer = LegacySurveySplitLayer(name, dr6, dr5, 32.)

    elif name == 'ls-dr67':
        dr7 = get_layer('decals-dr7')
        dr6 = get_layer('mzls+bass-dr6')
        layer = LegacySurveySplitLayer(name, dr6, dr7, 32.)

    elif name == 'phat':
        layer = PhatLayer('phat')

    elif name == 'm33':
        layer = M33Layer('m33')

    elif name == 'eboss':
        survey = get_survey('eboss')
        layer = ReDecalsLayer('eboss', 'image', survey)

    elif name == 'des-dr1':
        layer = DesLayer('des-dr1')

    elif name in ['decals-dr7', 'decals-dr7-model', 'decals-dr7-resid']:
        survey = get_survey('decals-dr7')
        image = ReDecalsLayer('decals-dr7', 'image', survey)
        model = ReDecalsModelLayer('decals-dr7-model', 'model', survey, drname='decals-dr7')
        resid = ReDecalsResidLayer(image, model, 'decals-dr7-resid', 'resid', survey,
                                   drname='decals-dr7')
        layers['decals-dr7'] = image
        layers['decals-dr7-model'] = model
        layers['decals-dr7-resid'] = resid
        layer = layers[name]

    elif name == 'decals-dr7-invvar':
        survey = get_survey('decals-dr7')
        layer = DecalsInvvarLayer(name, 'invvar', survey)

    elif name in ['mzls+bass-dr6', 'mzls+bass-dr6-model', 'mzls+bass-dr6-resid']:
        survey = get_survey('mzls+bass-dr6')
        image = ReDecalsLayer('mzls+bass-dr6', 'image', survey)
        model = ReDecalsModelLayer('mzls+bass-dr6-model', 'model', survey, drname='mzls+bass-dr6')
        resid = ReDecalsResidLayer(image, model, 'mzls+bass-dr6-resid', 'resid', survey,
                                   drname='mzls+bass-dr6')
        layers['mzls+bass-dr6'] = image
        layers['mzls+bass-dr6-model'] = model
        layers['mzls+bass-dr6-resid'] = resid
        layer = layers[name]

    elif name in ['decals-dr5', 'decals-dr5-model', 'decals-dr5-resid']:
        survey = get_survey('decals-dr5')
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

    elif name == 'vlass':
        layer = VlassLayer('vlass')

    elif name in ['decaps', 'decaps-model', 'decaps-resid']:
        survey = get_survey('decaps')
        image = Decaps2Layer('decaps', 'image', survey)
        model = Decaps2Layer('decaps-model', 'model', survey)
        resid = Decaps2ResidLayer(image, model,
                                  'decaps-resid', 'resid', survey, drname='decaps')
        layers['decaps'] = image
        layers['decaps-model'] = model
        layers['decaps-resid'] = resid
        layer = layers[name]

    elif name in ['mzls+bass-dr4', 'mzls+bass-dr4-model', 'mzls+bass-dr4-resid']:
        survey = get_survey('mzls+bass-dr4')
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
        survey = get_survey('decals-dr3')
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
        survey = get_survey('decals-dr2')
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
    elif name == 'unwise-neo3':
        layer = RebrickedUnwise('unwise-neo3',
                                settings.UNWISE_NEO3_DIR)
    elif name == 'unwise-neo4':
        layer = RebrickedUnwise('unwise-neo4',
                                settings.UNWISE_NEO4_DIR)

    elif name == '2mass':
        layer = TwoMassLayer('2mass')

    elif name == 'galex':
        layer = GalexLayer('galex')

    elif name == 'wssa':
        layer = WssaLayer('wssa')

    elif name == 'unwise-cat-model':
        layer = UnwiseCatalogModel('unwise-cat-model',
                                   os.path.join(settings.DATA_DIR, 'unwise-catalog', 'models'))

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
        # Try generic
        print('get_layer:', name, '-- generic')
        basename = name
        if name.endswith('-model'):
            basename = name[:-6]
        if name.endswith('-resid'):
            basename = name[:-6]
        survey = get_survey(basename)
        if survey is not None:
            image = ReDecalsLayer(basename, 'image', survey)
            model = ReDecalsModelLayer(basename + '-model', 'model', survey,
                                       drname=basename)
            resid = ReDecalsResidLayer(image, model, basename + '-resid', 'resid', survey,
                                       drname=basename)
            layers[basename] = image
            layers[basename + '-model'] = model
            layers[basename + '-resid'] = resid
            layer = layers[name]


    if layer is None:
        return default
    layers[name] = layer
    return layer

def get_tile_view(name):
    name = layer_name_map(name)
    def view(request, ver, zoom, x, y, **kwargs):
        layer = get_layer(name)
        #print('tile view: name', name, 'layer', layer)
        return layer.get_tile(request, ver, zoom, x, y, **kwargs)
    return view

def any_tile_view(request, name, ver, zoom, x, y, **kwargs):
    print('any_tile_view(', name, ver, zoom, x, y, ')')
    name = layer_name_map(name)
    layer = get_layer(name)
    if layer is None:
        return HttpResponse('no such layer: ' + name)
    return layer.get_tile(request, ver, zoom, x, y, **kwargs)

def cutout_wcs(req, default_layer='decals-dr7'):
    from astrometry.util.util import Tan
    import numpy as np
    args = []
    for k in ['crval1','crval2','crpix1','crpix2',
              'cd11','cd12','cd21','cd22','imagew','imageh']:
        v = req.GET.get(k)
        fv = float(v)
        args.append(fv)
    wcs = Tan(*args)
    #print('wcs:', wcs)
    pixscale = wcs.pixel_scale()
    x = y = 0

    name = req.GET.get('layer', default_layer)
    name = layer_name_map(name)
    layer = get_layer(name)

    #sdss = get_layer('sdssco')

    scale = int(np.floor(np.log2(pixscale / layer.pixscale)))
    scale = np.clip(scale, 0, layer.maxscale)
    #zoom = layer.nativescale - int(np.round(np.log2(pixscale/layer.native_pixscale)))
    zoom = 0

    rimgs = layer.render_into_wcs(wcs, zoom, x, y, general_wcs=True, scale=scale)
    if rimgs is None:
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(settings.STATIC_URL + 'blank.jpg')

    # FLIP VERTICAL AXIS?!
    flipimgs = []
    for img in rimgs:
        if img is not None:
            flipimgs.append(np.flipud(img))
        else:
            flipimgs.append(img)

    bands = layer.get_bands()
    rgb = layer.get_rgb(flipimgs, bands)
    
    import tempfile
    f,tilefn = tempfile.mkstemp(suffix='.jpg')
    os.close(f)
    layer.write_jpeg(tilefn, rgb)
    return send_file(tilefn, 'image/jpeg', unlink=True)

def sdss_wcs(req):
    return cutout_wcs(req, default_layer='sdssco')

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

    settings.READ_ONLY_BASEDIR = False

    from astrometry.util.util import Sip
    import matplotlib
    matplotlib.use('Agg')
    import pylab as plt

    # dr5 = get_layer('decals-dr5')
    # dr6 = get_layer('mzls+bass-dr6')
    # split = LegacySurveySplitLayer('ls56', dr5, dr6, 32.)
    # sys.exit(0)
    # 
    # #layer = get_layer('galex')
    # #layer = get_layer('unwise-neo3')
    # layer = get_layer('wssa')
    # wcs = Sip('tess.wcs')
    # imgs = layer.render_into_wcs(wcs, 8, None, None, general_wcs=True)
    # rgb = layer.get_rgb(imgs, layer.get_bands())
    # #plt.imsave('tess-galex.png', rgb)
    # #plt.imsave('tess-unwise.png', rgb)
    # plt.imsave('tess-wssa.png', rgb)
    # sys.exit(0)

    from django.test import Client
    c = Client()
    #response = c.get('/viewer/image-data/decals-dr5/decam-335137-N24-g')
    #response = c.get('/image-data/decals-dr5/decam-335137-N24-g')
    #response = c.get('/phat/1/13/7934/3050.jpg')
    #response = c.get('/phat/1/8/248/95.jpg')
    #response = c.get('/mzls+bass-dr6-model/1/12/4008/2040.jpg')
    #response = c.get('/mzls+bass-dr6/1/10/451/230.jpg')
    #response = c.get('/mzls+bass-dr6/1/11/902/461.jpg')
    #response = c.get('/mzls+bass-dr6-model/1/6/37/20.jpg')
    #c.get('/jpl_lookup/?ra=218.6086&dec=-1.0385&date=2015-04-11%2005:58:36.111660&camera=decam')
    #c.get('/unwise-neo3/1/9/255/255.jpg')
    #c.get('/unwise-neo3/1/8/127/127.jpg')
    #c.get('/unwise-neo3/1/7/63/63.jpg')
    #c.get('/unwise-neo3/1/6/31/31.jpg')
    #c.get('/unwise-neo3/1/11/0/1023.jpg')
    #c.get('/unwise-neo3/1/5/0/14.jpg')
    #c.get('/decals-dr5/1/14/5702/7566.jpg')
    #c.get('/ccds/?ralo=234.6575&rahi=234.7425&declo=13.5630&dechi=13.6370&id=decals-dr5')
    #c.get('/data-for-radec/?ra=234.7048&dec=13.5972&layer=decals-dr5')
    #c.get('/cutouts/?ra=234.7048&dec=13.5972&layer=decals-dr5')
    #c.get('/ccd/decals-dr5/decam-431280-S13-z')
    #c.get('/2mass/1/12/2331/1504.jpg')
    #c.get('/2mass/1/11/1167/754.jpg')
    #c.get('/2mass/1/11/1164/755.jpg')
    #c.get('/jpeg-cutout?ra=155.0034&dec=42.4534&zoom=11&layer=2mass')
    #c.get('/galex/1/11/0/1024.jpg')
    #c.get('/sdss2/1/14/7716/6485.jpg')
    #c.get('/exps/?ralo=234.6278&rahi=234.7722&declo=13.5357&dechi=13.6643&id=decals-dr7')
    #c.get('/wssa/1/10/358/474.jpg')
    #c.get('/cutout_panels/decals-dr7/722712/N13/?x=1123&y=3636&size=100')
    #c.get('/decals-dr7/1/13/4150/4129.jpg')
    #c.get('/decals-dr7/1/13/4159/4119.jpg')
    #c.get('/decals-dr7/1/12/2074/2064.jpg')
    #c.get('/decals-dr7/1/11/1037/1032.jpg')
    #c.get('/decals-dr7/1/8/129/128.jpg')
    #c.get('/decals-dr5/1/6/31/32.jpg')
    #c.get('/ls-dr56/1/13/3861/3126.jpg')
    #c.get('/des-dr1/1/13/7399/5035.jpg')
    #c.get('/des-dr1/1/12/3699/2517.jpg')
    #r = c.get('/fits-cutout?ra=175.8650&dec=52.7103&pixscale=0.5&layer=unwise-neo4')
    #r = c.get('/cutouts/?ra=43.9347&dec=-14.2082&layer=ls-dr67')
    #r = c.get('/cutout_panels/ls-dr67/372648/N23/?x=1673&y=3396&size=100')
    # r = c.get('/vlass/1/12/3352/779.jpg')
    # r = c.get('/vlass/1/9/414/94.jpg')
    # r = c.get('/vlass/1/8/207/47.jpg')
    # r = c.get('/vlass/1/7/103/23.jpg')
    # r = c.get('/vlass/1/6/51/11.jpg')
    # r = c.get('/vlass/1/5/25/5.jpg')
    #r = c.get('/vlass/1/9/508/114.jpg')
    r = c.get('/vlass/1/10/1015/228.jpg')
    #r = c.get('/vlass/1/10/1016/228.jpg')
    #r = c.get('/vlass/1/7/127/29.jpg')
    #r = c.get('/unwise-cat-model/1/12/3077/1624.jpg')
    #r = c.get('/unwise-cat-model/1/3/1/1.jpg')
    #r = c.get('/unwise-cat-model/1/6/47/44.jpg')
    #r = c.get('/unwise-cat-model/1/4/11/0.jpg')
    #r = c.get('/m33/1/16/61257/26897.jpg')
    #r = c.get('/m33/1/15/30627/13432.jpg')
    #r = c.get('/m33/1/14/15320/6716.jpg')
    #r = c.get('/m33/1/13/7660/3358.jpg')
    #r = c.get('/m33/1/12/3830/1679.jpg')
    #r = c.get('/m33/1/11/1915/840.jpg')
    #r = c.get('/m33/1/10/957/420.jpg')
    #r = c.get('/m33/1/9/478/210.jpg')
    #r = c.get('/m33/1/8/239/105.jpg')
    #r = c.get('/m33/1/7/120/52.jpg')
    #r = c.get('/unwise-neo4/1/5/27/7.jpg')
    #r = c.get('/jpeg-cutout?ra=0&dec=88.75&pixscale=11&layer=unwise-cat-model')
    #r = c.get('/jpeg-cutout?ra=0&dec=89.75&pixscale=6&layer=unwise-cat-model')
    #r = c.get('/jpeg-cutout?ra=180&dec=89.7&pixscale=6&layer=unwise-cat-model')
    #r = c.get('/cutout_panels/ls-dr67/372648/N23/?x=1673&y=3396&size=100')
    #r = c.get('/cutouts/?ra=148.2641&dec=-1.7679&layer=decals-dr7')
    #r = c.get('/sdss-wcs/?crval1=195.00000&crval2=60.00000&crpix1=384.4&crpix2=256.4&cd11=1.4810e-4&cd12=0&cd21=0&cd22=-1.4810e-4&imagew=768&imageh=512')
    #r = c.get('/cutout-wcs/?crval1=195.00000&crval2=60.00000&crpix1=384.4&crpix2=256.4&cd11=1.4810e-4&cd12=0&cd21=0&cd22=-1.4810e-4&imagew=768&imageh=512')
    #r = c.get('/lslga/1/cat.json?ralo=23.3077&rahi=23.4725&declo=30.6267&dechi=30.7573')
    #r = c.get('/phat-clusters/1/cat.json?ralo=10.8751&rahi=11.2047&declo=41.3660&dechi=41.5936')
    #r = c.get('/data-for-radec/?ra=35.8889&dec=-2.7425&layer=dr8-test6')
    #r = c.get('/ccd/dr8-test6/decam-262575-N12-z')
    print('r:', type(r))

    f = open('out.jpg', 'wb')
    for x in r:
        #print('Got', type(x), len(x))
        f.write(x)
    f.close()

    #c.get('/jpl_lookup/?ra=218.6086&dec=-1.0385&date=2015-04-11%2005:58:36.111660&camera=decam')
    sys.exit(0)
    # http://a.legacysurvey.org/viewer-dev/mzls+bass-dr6/1/12/4008/2040.jpg
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
    os.environ['DJANGO_SETTINGS_MODULE'] = 'viewer.settings'
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
