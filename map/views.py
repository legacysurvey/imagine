from __future__ import print_function
if __name__ == '__main__':
    import sys
    sys.path.insert(0, 'django-2.2.4')
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'viewer.settings'
    import django
    django.setup()

import os
import sys
import re
from django.http import HttpResponse, StreamingHttpResponse
try:
    from django.core.urlresolvers import reverse, get_script_prefix
except:
    # django 2.0
    from django.urls import reverse, get_script_prefix

from django import forms
from viewer import settings
from map.utils import (get_tile_wcs, trymakedirs, save_jpeg, ra2long, ra2long_B,
                       send_file, oneyear)
from map.coadds import get_scaled
from map.cats import get_random_galaxy, get_desi_tile_radec

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
    'ps1': [1],
    'hsc-dr2': [1],
    'vlass1.2': [1],
    '2mass': [1],
    'galex': [1],
    'des-dr1': [1],
    'ztf': [1],
    
    'eboss': [1,],

    'phat': [1,],
    'm33': [1,],

    'dr9sv-north': [1],
    'dr9sv-north-model': [1],
    'dr9sv-north-resid': [1],

    'dr9sv-south': [1],
    'dr9sv-south-model': [1],
    'dr9sv-south-resid': [1],

    'dr9sv': [1],
    'dr9sv-model': [1],
    'dr9sv-resid': [1],

    'ls-dr8-north': [1],
    'ls-dr8-north-model': [1],
    'ls-dr8-north-resid': [1],

    'ls-dr8-south': [1],
    'ls-dr8-south-model': [1],
    'ls-dr8-south-resid': [1],

    'ls-dr8': [1],
    'ls-dr8-model': [1],
    'ls-dr8-resid': [1],

    'ls-dr67': [1],

    'decals-dr7': [1],
    'decals-dr7-model': [1],
    'decals-dr7-resid': [1],

    'mzls+bass-dr6': [1],
    'mzls+bass-dr6-model': [1],
    'mzls+bass-dr6-resid': [1],

    'decals-dr5': [1],
    'decals-dr5-model': [1],
    'decals-dr5-resid': [1],

    'decaps': [1, 2],
    'decaps-model': [1, 2],
    'decaps-resid': [1, 2],

    'unwise-w1w2': [1],
    'unwise-neo2': [1],
    'unwise-neo3': [1],
    'unwise-neo4': [1],
    'unwise-neo6': [1],

    'unwise-cat-model': [1],

    'cutouts': [1],

    'dr9k-north': [1, 2],
    'dr9k-north-model': [1, 2],
    'dr9k-north-resid': [1, 2],

    'dr9k-south': [1, 2],
    'dr9k-south-model': [1, 2],
    'dr9k-south-resid': [1, 2],

    'ls-dr9-north': [1],
    'ls-dr9-north-model': [1],
    'ls-dr9-north-resid': [1],
}

test_layers = []
try:
    from map.test_layers import test_layers as tl
    for key,pretty in tl:
        if not key in tileversions:
            tileversions[key] = [1,]
except:
    pass

# tileversions['dr9m-north'].append(2)
# tileversions['dr9m-north-model'].append(2)
# tileversions['dr9m-north-resid'].append(2)

def tst(req):
    from django.shortcuts import render
    return render(req, 'tst.html')

def tst(req):
    from django.shortcuts import render
    return render(req, 'tst.html')

def cat(req):
    from django.shortcuts import render
    return render(req, 'cat.html')

def my_reverse(req, *args, **kwargs):
    ### FIXME -- does this work for decaps.legacysurvey.org ??
    # Or need something like:
    # path = settings.ROOT_URL
    # if is_decaps(req):
    #     path = '/'
    return reverse(*args, **kwargs)

def fix_hostname(req, url):
    host = req.META.get('HTTP_HOST', None)
    url = url.replace(settings.HOSTNAME, host)
    return url

def urls(req):
    from django.shortcuts import render
    script_prefix = get_script_prefix()
    this_url = reverse('urls')
    return render(req, 'urls.html', dict(script_prefix=script_prefix, this_url=this_url,
                                         enable_desi_targets=settings.ENABLE_DESI_TARGETS,
    ))

def gfas(req):
    from django.shortcuts import render
    return render(req, 'desi-gfas.html')

def ci(req):
    from django.shortcuts import render
    return render(req, 'desi-ci.html')

def request_layer_name(req, default_layer='ls-dr8'):
    name = req.GET.get('layer', default_layer)
    return clean_layer_name(name)

def clean_layer_name(name):
    name = str(name)
    name = name.replace(' ', '+')
    return {
        'sdss2': 'sdss',
        'sdssco': 'sdss',

        'hsc2': 'hsc-dr2',
        'hsc': 'hsc-dr2',
        
        'vlass': 'vlass1.2',
        
        'mzls bass-dr6': 'mzls+bass-dr6',
        'mzls bass-dr6-model': 'mzls+bass-dr6-model',
        'mzls bass-dr6-resid': 'mzls+bass-dr6-resid',

        'decaps2': 'decaps',
        'decaps2-model': 'decaps-model',
        'decaps2-resid': 'decaps-resid',

        'dr8': 'ls-dr8',
        'dr8-model': 'ls-dr8-model',
        'dr8-resid': 'ls-dr8-resid',
        'dr8-north': 'ls-dr8-north',
        'dr8-north-model': 'ls-dr8-north-model',
        'dr8-north-resid': 'ls-dr8-north-resid',
        'dr8-south': 'ls-dr8-south',
        'dr8-south-model': 'ls-dr8-south-model',
        'dr8-south-resid': 'ls-dr8-south-resid',
    }.get(name, name)

def layer_to_survey_name(layer):
    layer = layer.replace('-model', '')
    layer = layer.replace('-resid', '')
    return layer

# @needs_layer decorator.  Sets:
#  req.layer_name
#  req.survey_name
#  req.layer (MapLayer subclass)
def needs_layer(default_layer='ls-dr8', doctype='html', badjson=None):
    def decorate(func):
        def wrapped_req(req, *args, **kwargs):
            layername = request_layer_name(req, default_layer=default_layer)
            layername = clean_layer_name(layername)
            req.layer_name = layername
            req.survey_name = layer_to_survey_name(layername)
            req.layer = get_layer(layername)
            if req.layer is None:
                if doctype == 'json':
                    return HttpResponse(json.dumps(badjson), content_type='application/json')
                return HttpResponse('no such layer')
            return func(req, *args, **kwargs)
        return wrapped_req
    return decorate



def is_decaps(req):
    host = req.META.get('HTTP_HOST', None)
    #print('Host:', host)
    return (host == 'decaps.legacysurvey.org')

def is_m33(req):
    host = req.META.get('HTTP_HOST', None)
    return (host == 'm33.legacysurvey.org')

def index(req, **kwargs):
    print('Host is', req.META.get('HTTP_HOST', None))
    if is_decaps(req):
        return decaps(req)
    if is_m33(req):
        return m33(req)
    return _index(req, **kwargs)

def _index(req,
           default_layer = 'ls-dr9',
           default_radec = (None,None),
           default_zoom = 12,
           rooturl=settings.ROOT_URL,
           maxZoom = 16,
           **kwargs):
    kwkeys = dict(
        science = settings.ENABLE_SCIENCE,
        enable_older = settings.ENABLE_OLDER,
        enable_unwise = settings.ENABLE_UNWISE,
        enable_vlass = settings.ENABLE_VLASS,
        enable_dev = settings.ENABLE_DEV,
        enable_m33 = False,
        enable_cutouts = settings.ENABLE_CUTOUTS,
        enable_dr67 = settings.ENABLE_DR67,
        enable_dr56 = settings.ENABLE_DR56,
        enable_dr5 = settings.ENABLE_DR5,
        enable_dr6 = settings.ENABLE_DR6,
        enable_dr7 = settings.ENABLE_DR7,
        enable_dr8 = settings.ENABLE_DR8,
        enable_dr8_overlays = settings.ENABLE_DR8,
        enable_dr8_models = settings.ENABLE_DR8_MODELS,
        enable_dr8_resids = settings.ENABLE_DR8_RESIDS,
        enable_dr8_north = settings.ENABLE_DR8,
        enable_dr8_north_models = settings.ENABLE_DR8_MODELS,
        enable_dr8_north_resids = settings.ENABLE_DR8_RESIDS,
        enable_dr8_north_overlays = settings.ENABLE_DR8,
        enable_dr8_south = settings.ENABLE_DR8,
        enable_dr8_south_models = settings.ENABLE_DR8_MODELS,
        enable_dr8_south_resids = settings.ENABLE_DR8_RESIDS,
        enable_dr8_south_overlays = settings.ENABLE_DR8,
        enable_dr9sv = settings.ENABLE_DR9SV,
        enable_dr9sv_overlays = settings.ENABLE_DR9SV,
        enable_dr9sv_models = settings.ENABLE_DR9SV,
        enable_dr9sv_resids = settings.ENABLE_DR9SV,
        enable_dr9sv_north = settings.ENABLE_DR9SV,
        enable_dr9sv_north_models = settings.ENABLE_DR9SV,
        enable_dr9sv_north_resids = settings.ENABLE_DR9SV,
        enable_dr9sv_north_overlays = settings.ENABLE_DR9SV,
        enable_dr9sv_south = settings.ENABLE_DR9SV,
        enable_dr9sv_south_models = settings.ENABLE_DR9SV,
        enable_dr9sv_south_resids = settings.ENABLE_DR9SV,
        enable_dr9sv_south_overlays = settings.ENABLE_DR9SV,

        enable_dr9 = settings.ENABLE_DR9,
        enable_dr9_overlays = settings.ENABLE_DR9,
        enable_dr9_models = settings.ENABLE_DR9_MODELS,
        enable_dr9_resids = settings.ENABLE_DR9_RESIDS,
        enable_dr9_north = settings.ENABLE_DR9_NORTH,
        enable_dr9_north_models = settings.ENABLE_DR9_NORTH_MODELS,
        enable_dr9_north_resids = settings.ENABLE_DR9_NORTH_RESIDS,
        enable_dr9_north_overlays = settings.ENABLE_DR9_NORTH,
        enable_dr9_south = settings.ENABLE_DR9_SOUTH,
        enable_dr9_south_models = settings.ENABLE_DR9_SOUTH_MODELS,
        enable_dr9_south_resids = settings.ENABLE_DR9_SOUTH_RESIDS,
        enable_dr9_south_overlays = settings.ENABLE_DR9_SOUTH,

        enable_decaps = settings.ENABLE_DECAPS,
        enable_ps1 = settings.ENABLE_PS1,
        enable_des_dr1 = settings.ENABLE_DES_DR1,
        enable_ztf = settings.ENABLE_ZTF,
        enable_dr5_models = settings.ENABLE_DR5,
        enable_dr5_resids = settings.ENABLE_DR5,
        enable_dr6_models = settings.ENABLE_DR6,
        enable_dr6_resids = settings.ENABLE_DR6,
        enable_dr7_models = settings.ENABLE_DR7,
        enable_dr7_resids = settings.ENABLE_DR7,
        enable_dr5_overlays = settings.ENABLE_DR5,
        enable_dr6_overlays = settings.ENABLE_DR6,
        enable_dr7_overlays = settings.ENABLE_DR7,
        enable_eboss = settings.ENABLE_EBOSS,
        enable_hsc_dr2 = settings.ENABLE_HSC_DR2,
        enable_desi_targets = settings.ENABLE_DESI_TARGETS,
        enable_desi_footprint = True,
        enable_spectra = settings.ENABLE_SPECTRA,
        maxNativeZoom = settings.MAX_NATIVE_ZOOM,
        enable_phat = False,
        discuss_cutout_url=settings.DISCUSS_CUTOUT_URL,
    )

    for k in kwargs.keys():
        if not k in kwkeys:
            raise RuntimeError('unknown kwarg "%s" in map.index()' % k)
    for k,v in kwkeys.items():
        if not k in kwargs:
            kwargs[k] = v
    
    from map.cats import cat_user, cat_desi_tile

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
        layer = 'sdss'

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

    # Process desi_tile parameter
    try:
        tileid = req.GET.get('desi_tile')
        # Set ra and dec
        ra, dec = get_desi_tile_radec(int(tileid))
    except:
        pass

    from urllib.parse import unquote
    caturl = unquote(my_reverse(req, 'cat-json-tiled-pattern'))
    smallcaturl = unquote(my_reverse(req, 'cat-json-pattern'))

    #print('Small catalog URL:', smallcaturl)

    # includes a leaflet pattern for subdomains
    tileurl = settings.TILE_URL

    subdomains = settings.SUBDOMAINS
    # convert to javascript
    subdomains = '[' + ','.join(["'%s'" % s for s in subdomains]) + '];'

    #static_tile_url = fix_hostname(req, settings.STATIC_TILE_URL)
    static_tile_url = settings.STATIC_TILE_URL
    
    # includes subdomain pattern
    static_tile_url_B = settings.STATIC_TILE_URL_B
    subdomains_B = settings.SUBDOMAINS_B
    subdomains_B = '[' + ','.join(["'%s'" % s for s in subdomains_B]) + '];'

    # these are all relative paths
    ccdsurl = my_reverse(req, 'ccd-list') + '?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&layer={id}'
    bricksurl = my_reverse(req, 'brick-list') + '?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&layer={layer}'
    expsurl = my_reverse(req, 'exposure-list') + '?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&layer={id}'
    platesurl = my_reverse(req, 'sdss-plate-list') + '?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}'
    namequeryurl = my_reverse(req, 'object-query') + '?obj={obj}'
    uploadurl = my_reverse(req, 'upload-cat')
    usercatalogurl = my_reverse(req, cat_user, args=(1,)) + '?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&cat={cat}'
    usercatalogurl2 = my_reverse(req, cat_user, args=(1,)) + '?start={start}&N={N}&cat={cat}'

    desitile_url = my_reverse(req, cat_desi_tile, args=(1,)) + '?ralo={ralo}&rahi={rahi}&declo={declo}&dechi={dechi}&tile={tile}'

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

    desitiles = [int(x,10) for x in req.GET.get('tile', '').split(',') if len(x)]
    if len(desitiles):
        tile = desitiles[0]
        fiberid = None
        print('Looking up DESI tile', tile)
        if 'fiber' in req.GET:
            try:
                fiberid = int(req.GET.get('fiber'), 10)
            except:
                pass
        try:
            ra,dec = get_desi_tile_radec(tile, fiberid=fiberid)
            print('Tile RA,Dec', ra,dec)
        except:
            pass

    if 'targetid' in req.GET:
        try:
            targetid = int(req.GET['targetid'], 10)
            # 22 bits
            objid = targetid & 0x3fffff
            # 20 bits
            brickid = (targetid >> 22) & 0xfffff
            # 16 bits
            release = (targetid >> 42) & 0xffff
            print('Release', release, 'brickid', brickid, 'objid', objid)
        except:
            pass
        
    galname = None
    if ra is None or dec is None:
        ra,dec,galname = get_random_galaxy(layer=layer)
    
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

    test_cats = []
    try:
        from map.test_layers import test_cats as tc
        for la in tc:
            if not la in test_cats:
                test_cats.append(la)
    except:
        import traceback
        traceback.print_exc()

    test_ccds = []
    try:
        from map.test_layers import test_ccds as tc
        for la in tc:
            if not la in test_ccds:
                test_ccds.append(la)
    except:
        import traceback
        traceback.print_exc()


    args = dict(ra=ra, dec=dec,
                maxZoom=maxZoom,
                galname=galname,
                layer=layer, tileurl=tileurl,
                hostname_url=hostname_url,
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

                desitiles = desitiles,
                desitile_url = desitile_url,

                test_layers = test_layers,
                test_cats = test_cats,
                test_ccds = test_ccds,
    )

    args.update(kwargs)
    
    from django.shortcuts import render
    # (it's not supposed to be **args, trust me)
    return render(req, 'index.html', args)


def decaps(req):
    return _index(req,
                  enable_decaps=True,
                  enable_dr5_models=False,
                  enable_dr5_resids=False,
                  enable_dr5=True,
                  enable_ps1=False,
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

def dr6(req):
    return _index(req, enable_decaps=True,
                  enable_ps1=False,
                  enable_desi_targets=True,
                  default_layer='mzls+bass-dr6',
                  default_radec=(175.32, 47.69),
                  rooturl=settings.ROOT_URL + '/dr6',
              )

def m33(req):
    return _index(req,
                  enable_m33=True,
                  enable_decaps=True,
                  enable_dev=False,
                  enable_dr7=False,
                  enable_dr6=False,
                  enable_dr5=False,
                  enable_dr56=False,
                  enable_dr5_models=False,
                  enable_dr5_resids=False,
                  enable_ps1=False,
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

def phat(req):
    return _index(req,
                  enable_ps1=False,
                  enable_phat=True,
                  default_layer='phat',
                  default_radec=(11.04, 41.48),
                  rooturl=settings.ROOT_URL + '/phat',
                  maxZoom=18,
              )

def query_simbad(q):
    # py3
    from urllib.request import urlopen
    from urllib.parse import urlencode

    url = 'http://simbad.u-strasbg.fr/simbad/sim-id?output.format=votable&output.params=coo(d)&output.max=1&Ident='
    url += urlencode(dict(q=q)).replace('q=','')
    print('URL', url)
    f = urlopen(url)
    code = f.getcode()
    print('Code', code)
    # txt = f.read()
    # print('Got:', txt)
    # txt = txt.decode()
    # print('Got:', txt)
    from astrometry.util.siap import siap_parse_result
    #T = siap_parse_result(txt=txt)
    # file handle works for fn
    T = siap_parse_result(fn=f)
    T.about()
    if len(T) == 0:
        return False, 'Not found'
    t = T[0]
    return True, (t.ra_d, t.dec_d)

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
    # Check for TILE <desi_tile_id>
    words = obj.strip().split()
    if len(words) == 2 and words[0].lower() == 'tile':
        from map.cats import get_desi_tile_radec
        tileid = int(words[1])
        try:
            ra,dec = get_desi_tile_radec(tileid)
        except RuntimeError as e:
            return HttpResponse(json.dumps(dict(error='DESI tile %i not found' % tileid)))
        return HttpResponse(json.dumps(dict(ra=ra, dec=dec, name='DESI Tile %i' % tileid)))

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
        #result,val = query_ned(obj)
        result,val = query_simbad(obj)
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
<head>
<link rel="icon" type="image/png" href="%s/favicon.png" />
<link rel="shortcut icon" href="%s/favicon.ico" />
''' % (settings.STATIC_URL, settings.STATIC_URL)

def data_for_radec(req):
    ra  = float(req.GET['ra'])
    dec = float(req.GET['dec'])
    layername = request_layer_name(req)
    layer = get_layer(layername)
    print('data_for_radec: layer', layer)
    return layer.data_for_radec(req, ra, dec)

class NoOverlapError(RuntimeError):
    pass


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

    def has_cutouts(self):
        return False

    def data_for_radec(self, req, ra, dec):
        pass

    def get_catalog(self, req, ralo, rahi, declo, dechi):
        return HttpResponse('no catalog for layer ' + self.name)

    def ccds_touching_box(self, north, south, east, west, Nmax=None):
        return None

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
            #print('RA,Dec bounds of WCS:', rlo,rhi,dlo,dhi)
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

        # print('Looking for bricks touching WCS', wcs)
        # # DEBUG
        # if True:
        #     rlo,d = wcs.pixelxy2radec(W, H/2)[-2:]
        #     rhi,d = wcs.pixelxy2radec(1, H/2)[-2:]
        #     r,d1 = wcs.pixelxy2radec(W/2, 1)[-2:]
        #     r,d2 = wcs.pixelxy2radec(W/2, H)[-2:]
        #     #print('Approx RA,Dec range', rlo,rhi, 'Dec', d1,d2)

        #print('Bricks within range:', B.brickname)
        if len(keep) == 0:
            return None
        #print('Bricks touching:', B.brickname[np.array(keep)])
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
            print('create_scaled_image: brick', brick.brickname, 'band', band, 'scale', scale, ': Image source file', sourcefn, 'not found')
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
            info('Wrote', fn)
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
        debug('Reading image from', fn)
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

    def get_pixel_coord_type(self, scale):
        import numpy as np
        return np.int16

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

        coordtype = self.get_pixel_coord_type(scale)

        rimgs = []
        for band in bands:
            rimg = np.zeros((H,W), np.float32)
            rw   = np.zeros((H,W), np.float32)
            bandbricks = self.bricks_for_band(bricks, band)
            for brick in bandbricks:
                brickname = brick.brickname
                #print('Reading', brickname, 'band', band, 'scale', scale)
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
                ih,iw = subwcs.shape
                assert(np.iinfo(coordtype).max > max(ih,iw))
                oh,ow = wcs.shape
                assert(np.iinfo(coordtype).max > max(oh,ow))

                #print('Resampling', img.shape)
                try:
                    Yo,Xo,Yi,Xi,[resamp] = resample_with_wcs(wcs, subwcs, [img],
                                                             intType=coordtype)
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
                    resamp = resamp[I]

                    #print('get_brick_mask:', len(Yo), 'pixels')

                # print('xlo xhi', xlo,xhi, 'ylo yhi', ylo,yhi,
                #       'image shape', img.shape,
                #       'Xi range', Xi.min(), Xi.max(),
                #       'Yi range', Yi.min(), Yi.max(),
                #       'subwcs shape', subwcs.shape)

                #if not np.all(np.isfinite(img[Yi,Xi])):
                if not np.all(np.isfinite(resamp)):
                    ok, = np.nonzero(np.isfinite(resamp))
                    Yo = Yo[ok]
                    Xo = Xo[ok]
                    Yi = Yi[ok]
                    Xi = Xi[ok]
                    resamp = resamp[ok]

                ok = self.filter_pixels(scale, img, wcs, subwcs, Yo,Xo,Yi,Xi)
                if ok is not None:
                    Yo = Yo[ok]
                    Xo = Xo[ok]
                    Yi = Yi[ok]
                    Xi = Xi[ok]
                    resamp = resamp[ok]

                wt = self.get_pixel_weights(band, brick, scale)

                #rimg[Yo,Xo] += img[Yi,Xi] * wt
                rimg[Yo,Xo] += resamp * wt
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
        if zoom < 0 or x < -1 or y < -1 or x >= zoomscale or y >= zoomscale:
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
            print('Tile image filename:', tilefn, 'exists?', os.path.exists(tilefn))
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

        if ("lslga" in req.GET or "lslga-model" in req.GET
            or 'sga' in req.GET or 'sga-parent' in req.GET):

            from PIL import Image, ImageDraw
            img = Image.open(tilefn)

            ra, dec = wcs.radec_center()
            img_cx = img.size[0] / 2
            img_cy = img.size[1] / 2
            pixscale = wcs.pixel_scale()

            ralo = ra - (img_cx * pixscale / 3600 / np.cos(np.deg2rad(dec)))
            rahi = ra + (img_cx * pixscale / 3600 / np.cos(np.deg2rad(dec)))
            declo = dec - (img_cy * pixscale / 3600)
            dechi = dec + (img_cy * pixscale / 3600)

            from map.cats import query_lslga_radecbox, query_lslga_model_radecbox
            galaxies = None
            if req.GET.get('lslga', None) == '':
                lslgacolor_default = '#3388ff'
                galaxies = query_lslga_radecbox(ralo, rahi, declo, dechi)
            elif req.GET.get('lslga-model', None) == '':
                lslgacolor_default = '#ffaa33'
                galaxies = query_lslga_model_radecbox(ralo, rahi, declo, dechi)
            elif req.GET.get('sga', None) == '':
                lslgacolor_default = '#3388ff'
                fn = os.path.join(settings.DATA_DIR, 'sga', 'SGA-ellipse-v3.0.kd.fits')
                galaxies = query_lslga_radecbox(ralo, rahi, declo, dechi, fn=fn)
            elif req.GET.get('sga-parent', None) == '':
                lslgacolor_default = '#ffaa33'
                fn = os.path.join(settings.DATA_DIR, 'sga', 'SGA-parent-v3.0.kd.fits')
                galaxies = query_lslga_radecbox(ralo, rahi, declo, dechi, fn=fn)
            else:
                galaxies, lslgacolor_default = None, None

            for r in galaxies if galaxies is not None else []:

                RA, DEC = r.ra, r.dec
                if (req.GET.get('lslga', None) == '' or
                    req.GET.get('sga', None) == '' or
                    req.GET.get('sga-parent', None) == ''):
                    RAD = r.radius_arcsec
                    AB = r.ba
                    PA = r.pa
                elif req.GET.get('lslga-model', None) == '':
                    RAD = r.radius_model_arcsec
                    AB = r.ba_model
                    PA = r.pa_model

                if np.isnan(AB):
                    AB = 1
                if np.isnan(PA):
                    PA = 90

                major_axis_arcsec = RAD * 2
                minor_axis_arcsec = major_axis_arcsec * AB

                overlay_height = int(np.abs(major_axis_arcsec / pixscale))
                overlay_width = int(np.abs(minor_axis_arcsec / pixscale))

                overlay = Image.new('RGBA', (overlay_width, overlay_height))
                draw = ImageDraw.ImageDraw(overlay)
                box_corners = (0, 0, overlay_width, overlay_height)
                ellipse_color = '#' + req.GET.get('lslgacolor', lslgacolor_default).lstrip('#')
                ellipse_width = int(np.round(float(req.GET.get('lslgawidth', 3)), 0))
                draw.ellipse(box_corners, fill=None, outline=ellipse_color, width=ellipse_width)

                rotated = overlay.rotate(PA, expand=True)
                rotated_width, rotated_height = rotated.size

                ok, ellipse_x, ellipse_y = wcs.radec2pixelxy(RA, DEC)

                if ok:

                    paste_shift_x = int(ellipse_x - rotated_width / 2)
                    paste_shift_y = int(ellipse_y - rotated_height / 2)

                    img.paste(rotated, (paste_shift_x, paste_shift_y), rotated)

            img.save(tilefn)
    
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

    def write_cutout(self, ra, dec, pixscale, width, height, out_fn,
                     bands=None,
                     fits=False, jpeg=False,
                     subimage=False,
                     tempfiles=None):
        import numpy as np
        import fitsio
        native_pixscale = self.pixscale
        native_zoom = self.nativescale
        hdr = None
        if fits:
            import fitsio
            hdr = fitsio.FITSHDR()
            self.populate_fits_cutout_header(hdr)

        if subimage:
            from astrometry.libkd.spherematch import match_radec
            bricks = self.get_bricks()
            # HACK
            #brickrad = 3600. * 0.262 / 2 * np.sqrt(2.) / 3600.
            I,J,d = match_radec(ra, dec, bricks.ra, bricks.dec, 1., nearest=True)
            if len(I) == 0:
                raise RuntimeError('no overlap')
            brick = bricks[J[0]]
            print('RA,Dec', ra,dec, 'in brick', brick.brickname)
            scale = 0

            fitsio.write(out_fn, None, header=hdr, clobber=True)
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
                hdr['IMAGETYP'] = 'image'
                subwcs.add_to_header(hdr)
                # Append image to FITS file
                fitsio.write(out_fn, img, header=hdr)
                # Add invvar
                hdr['IMAGETYP'] = 'invvar'
                fitsio.write(out_fn, iv, header=hdr)
            return

        from astrometry.util.util import Tan
    
        ps = pixscale / 3600.
        raps = -ps
        decps = ps
        if jpeg:
            decps *= -1.
        wcs = Tan(*[float(x) for x in [ra, dec, (width+1)/2., (height+1)/2.,
                                       raps, 0., 0., decps, width, height]])
    
        zoom = native_zoom - int(np.round(np.log2(pixscale / native_pixscale)))
        zoom = max(0, min(zoom, 16))

        xtile = ytile = -1

        #rtn = self.get_tile(req, None, zoom, xtile, ytile, wcs=wcs, get_images=fits,
        #                     savecache=False, bands=bands, tempfiles=tempfiles)

        ims = self.render_into_wcs(wcs, zoom, xtile, ytile, bands=bands, tempfiles=tempfiles)
        if ims is None:
            raise NoOverlapError('No overlap')
        
        if jpeg:
            rgb = self.get_rgb(ims, bands)
            self.write_jpeg(out_fn, rgb)
            return

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
        fitsio.write(out_fn, cube, clobber=True, header=hdr)

    def get_cutout(self, req, fits=False, jpeg=False, outtag=None, tempfiles=None):
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

        subimage = ('subimage' in req.GET)

        if fits:
            suff = '.fits'
            filetype = 'image/fits'
        else:
            suff = '.jpg'
            filetype = 'image/jpeg'

        nice_fn = None
        if fits:
            if outtag is None:
                nice_fn = 'cutout_%.4f_%.4f%s' % (ra, dec, suff)
            else:
                nice_fn = 'cutout_%s_%.4f_%.4f%s' % (outtag, ra, dec, suff)

        import tempfile
        f,out_fn = tempfile.mkstemp(suffix=suff)
        os.close(f)
        os.unlink(out_fn)
        
        self.write_cutout(ra, dec, pixscale, width, height, out_fn, bands=bands,
                          fits=fits, jpeg=jpeg, subimage=subimage, tempfiles=tempfiles)

        return send_file(out_fn, filetype, unlink=True, filename=nice_fn)

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

    def has_cutouts(self):
        return True

    def data_for_radec(self, req, ra, dec):
        import numpy as np
        survey = self.survey
        bricks = survey.get_bricks()
        I = np.flatnonzero((ra >= bricks.ra1) * (ra < bricks.ra2) *
                           (dec >= bricks.dec1) * (dec < bricks.dec2))
        if len(I) == 0:
            return HttpResponse('No DECaLS data overlaps RA,Dec = %.4f, %.4f for version %s' % (ra, dec, name))
        I = I[0]
        brick = bricks[I]
        brickname = brick.brickname

        html = [
            html_tag,
            '<title>%s data for RA,Dec (%.4f, %.4f)</title></head>' %
                    (self.drname, ra, dec),
            ccds_table_css + '<body>',
        ]

        bb = get_radec_bbox(req)
        print('DecalsLayer.data_for_radec: bb', bb)
        if bb is not None:
            ralo,rahi,declo,dechi = bb
            print('RA,Dec bb:', bb)
            caturl = (my_reverse(req, 'cat-fits', args=(self.name,)) +
                      '?ralo=%f&rahi=%f&declo=%f&dechi=%f' % (ralo, rahi, declo, dechi))
            html.extend(['<h1>%s Data for RA,Dec box:</h1>' % self.drname,
                         '<p><a href="%s">Catalog</a></p>' % caturl])

        brick_html = self.brick_details_body(brick)
        html.extend(brick_html)

        ccdsfn = survey.find_file('ccds-table', brick=brickname)
        if os.path.exists(ccdsfn):
            from astrometry.util.fits import fits_table
            ccds = fits_table(ccdsfn)
            ccds = touchup_ccds(ccds, survey)
            if len(ccds):
                html.extend(self.ccds_overlapping_html(req, ccds, brick=brickname, ra=ra, dec=dec))
            from legacypipe.survey import wcs_for_brick
            brickwcs = wcs_for_brick(brick)
            ok,bx,by = brickwcs.radec2pixelxy(ra, dec)
            print('Brick x,y:', bx,by)
            ccds.cut((bx >= ccds.brick_x0) * (bx <= ccds.brick_x1) *
                     (by >= ccds.brick_y0) * (by <= ccds.brick_y1))
            print('Cut to', len(ccds), 'CCDs containing RA,Dec point')
            if len(ccds):
                html.extend(self.ccds_overlapping_html(req, ccds, ra=ra, dec=dec))

        html.extend(['</body></html>',])
        return HttpResponse('\n'.join(html))

    def brick_details_body(self, brick):
        survey = self.survey
        brickname = brick.brickname
        html = [
            '<h1>%s data for brick %s:</h1>' % (survey.drname, brickname),
            '<p>Brick bounds: RA [%.4f to %.4f], Dec [%.4f to %.4f]</p>' % (brick.ra1, brick.ra2, brick.dec1, brick.dec2),
            '<ul>',
            '<li><a href="%s/coadd/%s/%s/legacysurvey-%s-image.jpg">JPEG image</a></li>' % (survey.drurl, brickname[:3], brickname, brickname),
            '<li><a href="%s/coadd/%s/%s/">Coadded images</a></li>' % (survey.drurl, brickname[:3], brickname),
            '<li><a href="%s/tractor/%s/tractor-%s.fits">Catalog (FITS table)</a></li>' % (survey.drurl, brickname[:3], brickname),
            '</ul>',
            ]
        return html

    def ccds_overlapping_html(self, req, ccds, ra=None, dec=None, brick=None):
        if brick is not None:
            html = ['<h1>CCDs overlapping brick:</h1>']
        elif ra is not None and dec is not None:
            html = ['<h1>CCDs overlapping RA,Dec:</h1>']
        html.extend(ccds_overlapping_html(req, ccds, self.name, ra=ra, dec=dec))
        return html
    
    def ccds_touching_box(self, north, south, east, west, Nmax=None):
        from astrometry.util.starutil import radectoxyz, xyztoradec, degrees_between
        from astrometry.util.fits import fits_table
        from astrometry.util.util import Tan
        import numpy as np
        x1,y1,z1 = radectoxyz(east, north)
        x2,y2,z2 = radectoxyz(west, south)
        rc,dc = xyztoradec((x1+x2)/2., (y1+y2)/2., (z1+z2)/2.)
        # 0.4: ~ 90prime radius
        #radius = 0.4 + degrees_between(east, north, west, south)/2.
        pixscale = 1./3600.
        width = max(degrees_between(east, north, west, north),
                    degrees_between(east, south, west, south)) / pixscale * 1.1;
        height = np.abs(north - south) / pixscale * 1.1;
        fakewcs = Tan(rc, dc, width/2. + 0.5, height/2. + 0.5,
                      -pixscale, 0., 0., pixscale, width, height)
        ccds = self.survey.ccds_touching_wcs(fakewcs)
        if ccds is None:
            return None
        print(len(ccds), 'CCDs from survey')
        if 'good_ccd' in ccds.columns():
            ccds.cut(ccds.good_ccd)
        if Nmax:
            ccds = ccds[:Nmax]
        return ccds

    def get_catalog_in_wcs(self, wcs):
        from astrometry.util.fits import fits_table, merge_tables
        # returns cat,hdr

        H,W = wcs.shape
        X = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                              [1,H/2,H,H,H,H/2,1,1])
        r,d = X[-2:]

        B = self.bricks_touching_aa_wcs(wcs)
        if B is None:
            return None, None
        cat = []
        hdr = None
        for brickname in B.brickname:
            catfn = self.survey.find_file('tractor', brick=brickname)
            if not os.path.exists(catfn):
                print('Does not exist:', catfn)
                continue
            debug('Reading catalog', catfn)
            T = fits_table(catfn)
            T.cut(T.brick_primary)
            print('File', catfn, 'cut to', len(T), 'primary')
            if len(T) == 0:
                continue
            ok,xx,yy = wcs.radec2pixelxy(T.ra, T.dec)
            T.cut((xx > 0) * (yy > 0) * (xx < W) * (yy < H))
            cat.append(T)
            if hdr is None:
                hdr = T.get_header()
        if len(cat) == 0:
            cat = None
        else:
            cat = merge_tables(cat, columns='fillzero')
        return cat,hdr

    def get_catalog(self, req, ralo, rahi, declo, dechi):
        from map.cats import radecbox_to_wcs
        wcs = radecbox_to_wcs(ralo, rahi, declo, dechi)
        cat,hdr = self.get_catalog_in_wcs(wcs)
        fn = 'cat-%s.fits' % (self.name)
        import tempfile
        f,outfn = tempfile.mkstemp(suffix='.fits')
        os.close(f)
        os.unlink(outfn)
        cat.writeto(outfn, header=hdr)
        return send_file(outfn, 'image/fits', unlink=True, filename=fn)

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
        #return 1
        # ... except for images where fitsio (1.0.5) screwed up the fpack...
        if not os.path.exists(fn):
            return 1
        import fitsio
        F = fitsio.FITS(fn)
        debug('File', fn, 'has', len(F), 'hdus')
        if len(F) == 1:
            return 0
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
            print('Read-only; not creating scaled', brick.brickname, band, scale)
            return None
        
        # Create scaled-down image (recursively).
        #print('Creating scaled-down image for', brick.brickname, band, 'scale', scale)
        # This is a little strange -- we resample into a WCS twice
        # as big but with half the scale of the image we need, then
        # smooth & bin the image and scale the WCS.
        finalwcs = self.get_scaled_wcs(brick, band, scale)
        #print('Scaled WCS:', finalwcs)
        wcs = finalwcs.scale(2.)
        #print('Double-size WCS:', wcs)
        imgs = self.render_into_wcs(wcs, None, 0, 0, bands=[band], scale=scale-1,
                                    tempfiles=tempfiles)
        if imgs is None:
            return None
        img = imgs[0]
        del imgs

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
        return fn

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
        #print(self, 'Brick file:', fn, 'exists?', os.path.exists(fn))
        if os.path.exists(fn):
            return fits_table(fn)
        bsmall = self.get_bricks_for_scale(scale - 1)
        # Find generic bricks for scale...
        afn = os.path.join(settings.DATA_DIR, 'bricks-%i.fits' % scale)
        #print('Generic brick file:', afn)
        assert(os.path.exists(afn))
        allbricks = fits_table(afn)
        #print('Generic bricks:', len(allbricks))
        
        # Brick side lengths
        brickside = self.get_brick_size_for_scale(scale)
        brickside_small = self.get_brick_size_for_scale(scale-1)

        # Spherematch from smaller scale to larger scale bricks
        radius = (brickside + brickside_small) * np.sqrt(2.) / 2. * 1.01

        inds = match_radec(allbricks.ra, allbricks.dec, bsmall.ra, bsmall.dec, radius,
                           indexlist=True)

        haves = np.all(['has_%s' % band in bsmall.get_columns() for band in self.bands])
        #print('Does bsmall have has_<band> columns:', haves)
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
                #print('Brick', allbricks.brickname[ia], ':', len(I), 'spherematches', len(Igood), 'in box')
                if len(Igood) == 0:
                    continue
                hasany = False
                for b in self.bands:
                    hasband = np.any(bsmall.get('has_%s' % b)[Igood])
                    #print('  has', b, '?', hasband)
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

    def bricks_touching_radec_box(self, ralo, rahi, declo, dechi, scale=None,
                                  bricks=None):
        import numpy as np
        if bricks is None:
            bricks = self.get_bricks_for_scale(scale)
        #print('scale', scale, ':', len(bricks), 'total bricks')
        I, = np.nonzero((bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        #print(len(I), 'bricks overlap Dec range')
        ok = ra_ranges_overlap(ralo, rahi, bricks.ra1[I], bricks.ra2[I])
        I = I[ok]
        #print(len(I), 'bricks overlap Dec and RA range')
        if len(I) == 0:
            #print('Bricks touching RA,Dec box', ralo, rahi, 'Dec', declo, dechi, 'scale', scale,
            #      ': none')
            return None
        #print('Bricks touching RA,Dec box', ralo, rahi, 'Dec', declo, dechi, 'scale', scale, ': ',
        #      ', '.join(bricks.brickname[I]))
        return bricks[I]

        
class Decaps2Layer(DecalsDr3Layer):

    def brick_details_body(self, brick):
        survey = self.survey
        brickname = brick.brickname
        html = [
            '<h1>%s data for brick %s:</h1>' % (survey.drname, brickname),
            '<p>Brick bounds: RA [%.4f to %.4f], Dec [%.4f to %.4f]</p>' % (brick.ra1, brick.ra2, brick.dec1, brick.dec2),
            '<ul>',
            '<li><a href="%s/coadd/%s/%s/legacysurvey-%s-image.jpg">JPEG image</a></li>' % (survey.drurl, brickname[:3], brickname, brickname),
            '<li><a href="%s/coadd/%s/%s/">Coadded images</a></li>' % (survey.drurl, brickname[:3], brickname),
            '</ul>',
            ]
        return html


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

class DecalsResidLayer(ResidMixin, UniqueBrickMixin, DecalsLayer):
    pass

class DecalsModelLayer(UniqueBrickMixin, DecalsLayer):
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

    def data_for_radec(self, req, ra, dec):
        import numpy as np
        # from ccd_list...
        # 0.15: SDSS field radius is ~ 0.13
        radius = 0.15
        T = sdss_ccds_near(ra, dec, radius)
        if T is None:
            return HttpResponse('No SDSS data near RA,Dec = (%.3f, %.3f)' % (ra,dec))
        
        html = [html_tag + '<title>%s data for RA,Dec (%.4f, %.4f)</title></head>' %
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

        # Work around issue where the largest-scale bricks don't quite
        # meet up due to TAN projection effects.
        if scale >= 6:
            size = 3800
        else:
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

class HscLayer(RebrickedMixin, MapLayer):
    def __init__(self, name):
        super(HscLayer, self).__init__(name)
        self.bands = 'grz'
        self.basedir = os.path.join(settings.DATA_DIR, self.name)
        self.scaleddir = os.path.join(settings.DATA_DIR, 'scaled', self.name)
        self.rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)
        self.bricks = None
        self.pixscale = 0.168

    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
            '%(scale)i%(band)s', '%(brickname).4s',
            'hsc' + '-%(brickname)s-%(band)s.fits')

    def get_scaled_wcs(self, brick, band, scale):
        from astrometry.util.util import Tan
        # Scaled tiles (which are 0.5-degree on a side for scale=1) need to be:
        # 0.25 * 3600 / 0.168 ~ 5360 pix
        if scale >= 7:
            size = 6200
        elif scale == 6:
            size = 5600
        else:
            size = 5360
        pixscale = self.pixscale * 2**scale
        cd = pixscale / 3600.
        crpix = size/2. + 0.5
        wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                  float(size), float(size))
        return wcs

    def get_rgb(self, imgs, bands, **kwargs):
        from tractor.brightness import NanoMaggies
        zpscale = NanoMaggies.zeropointToScale(27.0)
        rgb = sdss_rgb([im/zpscale for im in imgs], bands,
                       scales=dict(g=(2,6.0*5.), r=(1,3.4*5.), z=(0,2.2*5.)), m=0.03)
        return rgb

    def get_base_filename(self, brick, band, **kwargs):
        path = os.path.join(self.basedir, brick.filename.strip().replace('-Z', '-'+band.upper()))
        return path

    def get_bricks(self):
        if self.bricks is not None:
            return self.bricks
        from astrometry.util.fits import fits_table
        self.bricks = fits_table(os.path.join(self.basedir, 'hsc-bricks.fits'))
        return self.bricks

    def get_brick_size_for_scale(self, scale):
        if scale == 0:
            return 4200 * self.pixscale / 3600.
        return 0.25 * 2**scale

    def get_bands(self):
        return self.bands
    
    def read_wcs(self, brick, band, scale, fn=None):
        from map.coadds import read_tan_from_header
        if fn is None:
            fn = self.get_filename(brick, band, scale)
        if fn is None:
            return None
        ext = self.get_fits_extension(scale, fn)
        return read_tan_from_header(fn, ext)


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
            #print('Zoom', zoom, '-> y', y)
            X = get_tile_wcs(zoom, 0, y)
            wcs = X[0]
            ok,rr,dd = wcs.pixelxy2radec([1,1], [1,256])
            #print('Decs', dd)
            self.tilesplits[zoom] = y

    def get_layer_for_radec(self, ra, dec):
        if dec < self.decsplit:
            return self.bottom
        from astrometry.util.starutil_numpy import radectolb
        l,b = radectolb(ra, dec)
        ngc = (b > 0.)
        if ngc and dec > self.decsplit:
            return self.top
        return self.bottom

    def brick_details_body(self, brick):
        layer = self.get_layer_for_radec(brick.ra, brick.dec)
        return layer.brick_details_body(brick)

    def has_cutouts(self):
        return True

    def data_for_radec(self, req, ra, dec):
        import numpy as np
        html = [
            html_tag,
            '<title>%s data for RA,Dec (%.4f, %.4f)</title></head>' %
                    (self.drname, ra, dec),
            ccds_table_css + '<body>',
        ]

        bb = get_radec_bbox(req)
        if bb is not None:
            ralo,rahi,declo,dechi = bb
            print('RA,Dec bb:', bb)
            caturl = (my_reverse(req, 'cat-fits', args=(self.name,)) +
                      '?ralo=%f&rahi=%f&declo=%f&dechi=%f' % (ralo, rahi, declo, dechi))
            html.extend(['<h1>%s Data for RA,Dec box:</h1>' % self.drname,
                         '<p><a href="%s">Catalog</a></p>' % caturl])

        for layer in [self.top, self.bottom]:
            survey = layer.survey
            bricks = survey.get_bricks()
            I = np.flatnonzero((ra >= bricks.ra1) * (ra < bricks.ra2) *
                               (dec >= bricks.dec1) * (dec < bricks.dec2))
            if len(I) == 0:
                continue
            I = I[0]
            brick = bricks[I]
            brickname = brick.brickname
            brick_html = layer.brick_details_body(brick)
            html.extend(brick_html)

            ccdsfn = survey.find_file('ccds-table', brick=brickname)
            if not os.path.exists(ccdsfn):
                continue
            from astrometry.util.fits import fits_table
            ccds = fits_table(ccdsfn)
            ccds = touchup_ccds(ccds, survey)
            if len(ccds) == 0:
                continue
            html.extend(layer.ccds_overlapping_html(req, ccds, ra=ra, dec=dec, brick=brickname))
            from legacypipe.survey import wcs_for_brick
            brickwcs = wcs_for_brick(brick)
            ok,bx,by = brickwcs.radec2pixelxy(ra, dec)
            print('Brick x,y:', bx,by)
            ccds.cut((bx >= ccds.brick_x0) * (bx <= ccds.brick_x1) *
                     (by >= ccds.brick_y0) * (by <= ccds.brick_y1))
            print('Cut to', len(ccds), 'CCDs containing RA,Dec point')
            if len(ccds):
                html.extend(layer.ccds_overlapping_html(req, ccds, ra=ra, dec=dec))

        html.extend(['</body></html>',])
        return HttpResponse('\n'.join(html))

    def ccds_touching_box(self, north, south, east, west, Nmax=None):
        from astrometry.util.fits import merge_tables
        ccds_n = self.top.ccds_touching_box(north, south, east, west, Nmax=Nmax)
        ccds_s = self.bottom.ccds_touching_box(north, south, east, west, Nmax=Nmax)
        ccds = []
        if ccds_n is not None:
            ccds.append(ccds_n)
        if ccds_s is not None:
            ccds.append(ccds_s)
        if not len(ccds):
            return None
        return merge_tables(ccds, columns='fillzero')

    # copied from DecalsLayer
    def get_catalog(self, req, ralo, rahi, declo, dechi):
        from map.cats import radecbox_to_wcs
        wcs = radecbox_to_wcs(ralo, rahi, declo, dechi)
        cat,hdr = self.get_catalog_in_wcs(wcs)
        fn = 'cat-%s.fits' % (self.name)
        import tempfile
        f,outfn = tempfile.mkstemp(suffix='.fits')
        os.close(f)
        os.unlink(outfn)
        cat.writeto(outfn, header=hdr)
        return send_file(outfn, 'image/fits', unlink=True, filename=fn)

    def get_catalog_in_wcs(self, wcs):
        from astrometry.util.fits import merge_tables
        allcats = []
        hdr = None
        for layer,above in [(self.top,True), (self.bottom,False)]:
            cat,h = layer.get_catalog_in_wcs(wcs)
            if cat is not None and len(cat)>0:
                if above:
                    cat.cut(cat.dec >= self.decsplit)
                else:
                    from astrometry.util.starutil_numpy import radectolb
                    import numpy as np
                    l,b = radectolb(cat.ra, cat.dec)
                    sgc = (b < 0.)
                    cat.cut(np.logical_or(cat.dec < self.decsplit, sgc))
                allcats.append(cat)
            if h is not None:
                hdr = h
        if len(allcats) == 0:
            allcats = None
        else:
            allcats = merge_tables(allcats, columns='fillzero')
        return allcats,hdr

    def get_bricks(self):
        from astrometry.util.fits import merge_tables
        BB = merge_tables([l.get_bricks() for l in self.layers], columns='fillzero')
        return BB

    def bricks_touching_radec_box(self, *args, **kwargs):
        from astrometry.util.fits import merge_tables
        BB = merge_tables([l.bricks_touching_radec_box(*args, **kwargs)
                           for l in self.layers])
        return BB

    def get_filename(self, brick, band, scale, tempfiles=None):
        layer = self.get_layer_for_radec(brick.ra, brick.dec)
        return layer.get_filename(brick, band, scale, tempfiles=tempfiles)

    def get_base_filename(self, brick, band, **kwargs):
        layer = self.get_layer_for_radec(brick.ra, brick.dec)
        return layer.get_base_filename(brick, band, **kwargs)

    def get_fits_extension(self, scale, fn):
        if fn.endswith('.fz'):
            return 1
        return 0

    def render_into_wcs(self, wcs, zoom, x, y, general_wcs=False, **kwargs):
        
        ## FIXME -- generic WCS
        #print('render_into_wcs zoom,x,y', zoom,x,y, 'wcs', wcs)
        if y != -1:
            ## FIXME -- this is not the correct cut -- only listen to split for NGC --
            ## but this doesn't get called anyway because the JavaScript layer has the smarts.
            split = self.tilesplits[zoom]
            if y < split:
                #print('y below split -- north')
                return self.top.render_into_wcs(wcs, zoom, x, y,
                                                general_wcs=general_wcs, **kwargs)
            if y > split:
                #print('y above split -- south')
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
        from astrometry.util.starutil_numpy import radectolb
        # Compute Decs for each Y in the WCS -- this is assuming that the WCS is axis-aligned!!
        H,W = wcs.shape
        x = np.empty(H)
        x[:] = W//2 + 0.5
        y = np.arange(1, H+1)
        rr,dd = wcs.pixelxy2radec(x, y)[-2:]
        ll,bb = radectolb(rr, dd)
        ngc = (bb > 0.)
        I = np.flatnonzero((dd >= self.decsplit) * ngc)
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
        ## FIXME -- this is not the correct cut -- ignores NGC/SGC difference
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

    def has_cutouts(self):
        return False

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

    def data_for_radec(self, req, ra, dec):
        bricks = self.bricks_touching_radec_box(ra, ra, dec, dec, scale=0)
        print('Bricks:', bricks)
        html = ['<html>',
                '<head><title>Data for DES-DR1 (%.4f, %.4f)</title>' % (ra, dec),
                ccds_table_css, '</head><body>']

        html.append('<h1>Data for DES-DR1 RA,Dec (%.4f, %.4f)</h1>' % (ra, dec))
        html.append('<p>Note, we only have the coadded images, not the individual exposures.</p>')

        html.append('<table class="ccds"><tr><th>Tile</th>')
        bands = 'grizY'
        for band in bands:
            html.append('<th>FITS: %s</th>' % band)
        html.append('<th>TIFF</th>')
        for brick in bricks:
            html.append('<tr><td>%s</td>' % brick.brickname)
            for band in bands:
                url = brick.get('fits_image_%s' % band.lower())
                urlfile = url.strip().split('/')[-1]
                html.append('<td><a href="%s">%s</a></td>' % (url, urlfile))
            url = brick.tiff_color_image
            urlfile = url.strip().split('/')[-1]
            html.append('<td><a href="%s">%s</a></td></tr>' % (url, urlfile))
        html.append('</table>')
        
        html.extend(['</body>', '</html>'])
        return HttpResponse('\n'.join(html))

    
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

            origimg = img

            img = boff + bsoft * 2. * np.sinh(img / alpha)


            # print('After linearitity: image 90th pctile:', np.percentile(img.ravel(), 90))

            # Zeropoint of 25 = factor of 10 vs nanomaggies
            img *= 0.1 / exptime

            #img[np.logical_not(np.isfinite(img))] = 0.
            #img[origimg == bad] = 0.

            bad = hdr['BLANK']
            bzero = hdr['BZERO']
            bscale = hdr['BSCALE']
            badval = bzero + bscale * (bad - 0.5)
            img[origimg > badval] = 0.



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

    def get_bricks_for_scale(self, scale):
        if scale in [0, None]:
            return self.get_bricks()
        scale = min(scale, self.maxscale)
        from astrometry.util.fits import fits_table
        fn = os.path.join(self.basedir, 'vlass-bricks-%i.fits' % scale)
        print('vlass bricks for scale', scale, '->', fn)
        b = fits_table(fn)
        return b

    def get_scaled_wcs(self, brick, band, scale):
        from astrometry.util.util import Tan
        if scale < 5:
            size = self.pixelsize
        elif scale == 5:
            size = 4000
        elif scale >= 6:
            size = 4400

        pixscale = self.pixscale * 2**scale
        cd = pixscale / 3600.
        crpix = size/2. + 0.5
        wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                  float(size), float(size))
        return wcs

    def get_bands(self):
        return [1]

    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        assert(len(imgs) == 1)
        img = imgs[0]
        H,W = img.shape
        #mn,mx = -0.0003, 0.003
        mn,mx = -0.0001, 0.001
        gray = np.clip(255. * ((img-mn) / (mx-mn)), 0., 255.).astype(np.uint8)
        gray[img == 0] = 64
        #mn,mx = -0.0003, 0.01
        #gray = (255. * np.sqrt(np.clip((img-mn) / (mx-mn), 0., 1.))).astype(np.uint8)
        rgb = np.zeros((H,W,3), np.uint8)
        rgb[:,:,:] = gray[:,:,np.newaxis]
        return rgb

    def get_base_filename(self, brick, band, **kwargs):
        return os.path.join(self.basedir, brick.filename.strip())

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

    def data_for_radec(self, req, ra, dec):
        bricks = self.bricks_touching_radec_box(ra, ra, dec, dec, scale=0)
        print('Bricks:', bricks)
        html = ['<html>',
                '<head><title>Data for VLASS (%.4f, %.4f)</title>' % (ra, dec),
                ccds_table_css, '</head><body>']
        html.append('<h1>Data for VLASS RA,Dec (%.4f, %.4f)</h1>' % (ra, dec))
        html.append('<table class="ccds"><tr><th>Tile</th><th>Field</th>')
        for brick in bricks:
            html.append('<tr><td>%s</td>' % brick.tile)
            #url = settings.STATIC_URL_PATH + '/data/' + brick.filename.strip()
            dirname = '/'.join(brick.filename.strip().split('/')[:-1])
            url = 'https://archive-new.nrao.edu/vlass/quicklook/' + dirname
            html.append('<td><a href="%s">%s</a></td>' % (url, brick.brickname))
        html.append('</table>')
        html.extend(['</body>', '</html>'])
        return HttpResponse('\n'.join(html))

class ZtfLayer(RebrickedMixin, MapLayer):
    def __init__(self, name):
        super(ZtfLayer, self).__init__(name, nativescale=12)
        self.pixscale = 1.0
        self.bands = self.get_bands()
        self.pixelsize = 3744 # 3600 * 1.04
        self.maxscale = 6

    def get_bricks(self):
        from astrometry.util.fits import fits_table
        import numpy as np
        T = fits_table(os.path.join(self.basedir, 'ztf-tiles.kd.fits'))
        T.brickname = np.array(['%06i-%02i-%02i' % (f,c,q)
                                for f,c,q in zip(T.field, T.chip, T.quad)])
        T.ra  = T.crval1
        T.dec = T.crval2
        return T

    def get_bricks_for_scale(self, scale):
        if scale in [0, None]:
            return self.get_bricks()
        scale = min(scale, self.maxscale)
        from astrometry.util.fits import fits_table
        # just copied vlass bricks
        fn = os.path.join(self.basedir, 'ztf-bricks-%i.fits' % scale)
        #print('ZTF bricks for scale', scale, '->', fn)
        b = fits_table(fn)
        return b

    def bricks_for_band(self, bricks, band):
        #print('ZTF bricks for band: bricks', len(bricks), 'band', band)
        if not 'filter' in bricks.get_columns():
            return bricks
        bb = bricks[bricks.filter == ('z'+band)]
        return bb

    def bricks_within_range(self, ra, dec, radius, scale=None):
        from astrometry.libkd.spherematch import match_radec, tree_open, tree_search_radec
        from astrometry.util.fits import fits_table
        import numpy as np
        if scale > 0:
            return None
        fn = os.path.join(self.basedir, 'ztf-tiles.kd.fits')
        kd = tree_open(fn)
        # 0.65 ~ 3200/2 * sqrt(2) * 1"/pix
        I = tree_search_radec(kd, ra, dec, radius + 0.65)
        #print('Bricks_within_range: radius=', radius, 'RA,Dec', ra,dec, '=', len(I))
        T = fits_table(fn, rows=I)
        T.brickname = np.array(['%06i-%02i-%02i' % (f,c,q)
                                for f,c,q in zip(T.field, T.chip, T.quad)])
        T.ra  = T.crval1
        T.dec = T.crval2
        return T

    def get_scaled_wcs(self, brick, band, scale):
        from astrometry.util.util import Tan
        if scale < 5:
            size = self.pixelsize
        elif scale == 5:
            size = 4000
        elif scale >= 6:
            size = 4400
        pixscale = self.pixscale * 2**scale
        cd = pixscale / 3600.
        crpix = size/2. + 0.5
        wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                  float(size), float(size))
        return wcs

    def get_bands(self):
        return 'gri'

    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        #print('ZTF get_rgb: bands', bands)
        scales = dict(g=(2,3.0), r=(1,2.0), i=(0,0.8))
        #for im,band in zip(imgs,bands):
        #    print('band', band, ': pcts', np.percentile(im[np.isfinite(im)], [0,25,50,75,100]))
        rgb = sdss_rgb(imgs, bands, scales=scales)
        return rgb

    def get_base_filename(self, brick, band, **kwargs):
        return os.path.join(self.basedir, 'ref-images', brick.filename.strip())

    def get_fits_extension(self, scale, fn):
        if scale == 0:
            return 0
        return 1

    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
                            '%(scale)i%(band)s', '%(brickname).3s',
                            'ztf-%(brickname)s-%(band)s.fits')

    def read_image(self, brick, band, scale, slc, fn=None):
        #print('ZTF read_image: brick filter:', brick.filter)
        img = super(ZtfLayer, self).read_image(brick, band, scale, slc, fn=fn)
        if scale > 0:
            return img
        # Subtract & scale
        zpscale = 10.**((brick.magzp - 22.5) / 2.5)
        img = (img - brick.globmed) / zpscale
        return img
    
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

def sdss_rgb(imgs, bands, scales=None,
             m = 0.02):
    import numpy as np
    rgbscales = {'u': (2,1.5), #1.0,
                 'g': (2,2.5),
                 'r': (1,1.5),
                 'i': (0,1.0),
                 'z': (0,0.4), #0.3
                 }
    if scales is not None:
        rgbscales.update(scales)

    I = 0
    for img,band in zip(imgs, bands):
        plane,scale = rgbscales[band]
        img = np.maximum(0, img * scale + m)
        I = I + img
    I /= len(bands)
        
    # b,g,r = [rimg * rgbscales[b] for rimg,b in zip(imgs, bands)]
    # r = np.maximum(0, r + m)
    # g = np.maximum(0, g + m)
    # b = np.maximum(0, b + m)
    # I = (r+g+b)/3.
    Q = 20
    fI = np.arcsinh(Q * I) / np.sqrt(Q)
    I += (I == 0.) * 1e-6
    H,W = I.shape
    rgb = np.zeros((H,W,3), np.float32)
    for img,band in zip(imgs, bands):
        plane,scale = rgbscales[band]
        rgb[:,:,plane] = (img * scale + m) * fI / I

    # R = fI * r / I
    # G = fI * g / I
    # B = fI * b / I
    # # maxrgb = reduce(np.maximum, [R,G,B])
    # # J = (maxrgb > 1.)
    # # R[J] = R[J]/maxrgb[J]
    # # G[J] = G[J]/maxrgb[J]
    # # B[J] = B[J]/maxrgb[J]
    # rgb = np.dstack((R,G,B))
    rgb = np.clip(rgb, 0, 1)
    return rgb

def dr2_rgb(rimgs, bands, **ignored):
    return sdss_rgb(rimgs, bands, scales=dict(g=(2,6.0), r=(1,3.4), z=(0,2.2)), m=0.03)

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

class SplitSurveyData(LegacySurveyData):
    def __init__(self, north, south):
        super(SplitSurveyData, self).__init__()
        self.north = north
        self.south = south

    def get_bricks_readonly(self):
        if self.bricks is None:
            from astrometry.util.fits import merge_tables
            self.bricks = merge_tables([self.north.get_bricks_readonly(),
                                        self.south.get_bricks_readonly()], columns='fillzero')
        return self.bricks

    def find_ccds(self, expnum=None, ccdname=None, camera=None):
        import numpy as np
        from astrometry.util.fits import merge_tables
        ccds = []
        ccds_n = self.north.find_ccds(expnum=expnum, ccdname=ccdname, camera=camera)
        if ccds_n is not None:
            ccds_n.is_north = np.ones(len(ccds_n), bool)
            ccds.append(ccds_n)
        print('north CCDs:', ccds_n)
        ccds_s = self.south.find_ccds(expnum=expnum, ccdname=ccdname, camera=camera)
        print('south CCDs:', ccds_s)
        if ccds_s is not None:
            ccds_s.is_north = np.zeros(len(ccds_s), bool)
            ccds.append(ccds_s)
        if len(ccds) == 0:
            return None
        ccds = merge_tables(ccds)
        return ccds
    
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
            n.layer = np.array([self.north.layer] * len(n))
            ns.append(n)
        s = self.south.ccds_touching_wcs(wcs, **kwargs)
        print('ccds_touching_wcs: south', s)
        if s is not None:
            s.is_north = np.zeros(len(s), bool)
            s.layer = np.array([self.south.layer] * len(s))
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

class DR8LegacySurveyData(LegacySurveyData):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.image_typemap.update({
            'decam': DR8DecamImage,
            'mosaic': DR8MosaicImage,
            '90prime': DR8BokImage,
            })

from legacypipe.decam import DecamImage
class DR8DecamImage(DecamImage):
    def __init__(self, *args):
        super().__init__(*args)
        calibdir = self.survey.get_calib_dir()
        # calib/decam/splinesky-merged/00154/decam-00154069.fits
        estr = '%08i' % self.expnum
        self.old_merged_skyfns = [
            os.path.join(calibdir, self.camera, 'splinesky-merged',
                         estr[:5], '%s-%s.fits' % (self.camera, estr)),
            os.path.join(calibdir, self.camera, 'splinesky',
                         estr[:5], '%s-%s.fits' % (self.camera, estr))]
        self.old_merged_psffns = [
            os.path.join(calibdir, self.camera, 'psfex-merged',
                         estr[:5], '%s-%s.fits' % (self.camera, estr)),
            os.path.join(calibdir, self.camera, 'psfex',
                         estr[:5], '%s-%s.fits' % (self.camera, estr))]
    def get_fwhm(self, primhdr, imghdr):
        if self.fwhm > 0:
            return self.fwhm
        return imghdr['FWHM']

from legacypipe.mosaic import MosaicImage
class DR8MosaicImage(MosaicImage):
    def __init__(self, *args):
        super().__init__(*args)
        calibdir = self.survey.get_calib_dir()
        estr = '%08i' % self.expnum
        self.old_merged_skyfns = [os.path.join(calibdir, self.camera, 'splinesky-merged',
                                              estr[:5], '%s-%s.fits' % (self.camera, estr)),
                                 os.path.join(calibdir, self.camera, 'splinesky',
                                             estr[:5], '%s-%s.fits' % (self.camera, estr))]
        self.old_merged_psffns = [
            os.path.join(calibdir, self.camera, 'psfex-merged',
                         estr[:5], '%s-%s.fits' % (self.camera, estr)),
            os.path.join(calibdir, self.camera, 'psfex',
                         estr[:5], '%s-%s.fits' % (self.camera, estr))]

from legacypipe.bok import BokImage
class DR8BokImage(BokImage):
    def __init__(self, *args):
        super().__init__(*args)
        calibdir = self.survey.get_calib_dir()
        estr = '%08i' % self.expnum
        self.old_merged_skyfns = [os.path.join(calibdir, self.camera, 'splinesky-merged',
                                              estr[:5], '%s-%s.fits' % (self.camera, estr)),
                                 os.path.join(calibdir, self.camera, 'splinesky',
                                              estr[:5], '%s-%s.fits' % (self.camera, estr))]
        self.old_merged_psffns = [
            os.path.join(calibdir, self.camera, 'psfex-merged',
                         estr[:5], '%s-%s.fits' % (self.camera, estr)),
            os.path.join(calibdir, self.camera, 'psfex',
                         estr[:5], '%s-%s.fits' % (self.camera, estr))]

surveys = {}
def get_survey(name):
    global surveys
    import numpy as np
    name = clean_layer_name(name)
    name = layer_to_survey_name(name)
    #print('Survey name', name)

    if name in surveys:
        #print('Cache hit for survey', name)
        return surveys[name]

    if '/' in name or '..' in name:
        return None

    #debug('Creating LegacySurveyData() object for "%s"' % name)
    
    basedir = settings.DATA_DIR
    dirnm = os.path.join(basedir, name)

    survey = None

    cachedir = None
    if 'dr8' in name or 'dr7' in name or 'dr9' in name:
        cachedir = os.path.join(dirnm, 'extra-images')

    if name == 'decaps':
        survey = Decaps2LegacySurveyData(survey_dir=dirnm)
        survey.drname = 'DECaPS'
        survey.drurl = 'https://portal.nersc.gov/cfs/cosmo/data/decaps/dr1'

    elif name == 'ls-dr67':
        north = get_survey('mzls+bass-dr6')
        north.layer = 'mzls+bass-dr6'
        south = get_survey('decals-dr7')
        south.layer = 'decals-dr7'
        survey = SplitSurveyData(north, south)

    elif name == 'ls-dr8':
        north = get_survey('ls-dr8-north')
        north.layer = 'ls-dr8-north'
        south = get_survey('ls-dr8-south')
        south.layer = 'ls-dr8-south'
        survey = SplitSurveyData(north, south)

    elif name == 'ls-dr9':
        north = get_survey('ls-dr9-north')
        north.layer = 'ls-dr9-north'
        south = get_survey('ls-dr9-south')
        south.layer = 'ls-dr9-south'
        survey = SplitSurveyData(north, south)

    elif name in ['ls-dr8-south', 'ls-dr8-north', 'decals-dr5',
                  'decals-dr7', 'mzls+bass-dr6']:
        survey = DR8LegacySurveyData(survey_dir=dirnm, cache_dir=cachedir)
        # DR5 CCDs table:
        # - pull in "photometric = annotated has_zeropoint * photometric * blacklist_ok"
        # python legacypipe/create_kdtrees.py --no-cut $CSCRATCH/dr5x.fits data/decals-dr5/survey-ccds-decam-dr5-newlocs4-ext2.kd.fits
        # (not startree! -- need expnum tree too)

    elif name in ['ls-dr9-north', 'ls-dr9-south']:
        survey = DR8LegacySurveyData(survey_dir=dirnm, cache_dir=cachedir)

    elif name in ['ls-dr9-south-B']:
        survey = DR8LegacySurveyData(survey_dir=dirnm, cache_dir=cachedir)

    elif name == 'dr9sv':
        north = get_survey('dr9sv-north')
        north.layer = 'dr9sv-north'
        south = get_survey('dr9sv-south')
        south.layer = 'dr9sv-south'
        survey = SplitSurveyData(north, south)

    #print('dirnm', dirnm, 'exists?', os.path.exists(dirnm))

    if survey is None and not os.path.exists(dirnm):
        return None

    if survey is None:
        survey = LegacySurveyData(survey_dir=dirnm, cache_dir=cachedir)
        print('Creating LegacySurveyData for', name, 'with survey', survey, 'dir', dirnm)

    names_urls = {
        'mzls+bass-dr6': ('MzLS+BASS DR6', 'http://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr6/'),
        'decals-dr5': ('DECaLS DR5', 'http://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr5/'),
        'decals-dr7': ('DECaLS DR7', 'http://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr7/'),
        'eboss': ('eBOSS', 'http://legacysurvey.org/'),
        'decals': ('DECaPS', 'http://legacysurvey.org/'),
        'ls-dr67': ('Legacy Surveys DR6+DR7', 'http://portal.nersc.gov/cfs/cosmo/data/legacysurvey/'),
        'ls-dr8-north': ('Legacy Surveys DR8-north', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr8/north'),
        'ls-dr8-south': ('Legacy Surveys DR8-south', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr8/south'),
        'ls-dr8': ('Legacy Surveys DR8', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr8/'),

        'ls-dr9-north': ('Legacy Surveys DR9-north', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr9/north'),
        'ls-dr9-south': ('Legacy Surveys DR9-south', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr9/south'),
        'ls-dr9': ('Legacy Surveys DR9', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr9/'),
        }

    n,u = names_urls.get(name, ('',''))
    if not hasattr(survey, 'drname'):
        survey.drname = n
    if not hasattr(survey, 'drurl'):
        survey.drurl = u

    surveys[name] = survey
    return survey

def brick_list(req):
    import json
    north = float(req.GET['dechi'])
    south = float(req.GET['declo'])
    east  = float(req.GET['ralo'])
    west  = float(req.GET['rahi'])
    if east < 0:
        east += 360.
        west += 360.

    layername = request_layer_name(req)
    survey = get_survey(layername)
    B = None
    if survey is not None:
        try:
            B = survey.get_bricks_readonly()
        except:
            pass
    if B is None:
        # Generic all-sky legacy surveys bricks
        survey = LegacySurveyData(survey_dir=settings.DATA_DIR)
        B = survey.get_bricks_readonly()
        #B = fits_table(os.path.join(settings.DATA_DIR, 'bricks-0.fits'),
        #columns=['brickname', 'ra1', 'ra2', 'dec1', 'dec2', 'ra', 'dec'])

    I = survey.bricks_touching_radec_box(B, east, west, south, north)
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

def ccd_list(req):
    import json
    from astrometry.util.util import Tan
    import numpy as np
    north = float(req.GET['dechi'])
    south = float(req.GET['declo'])
    east  = float(req.GET['ralo'])
    west  = float(req.GET['rahi'])

    name = request_layer_name(req)
    print('Name:', name)
    name = clean_layer_name(name)
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

    layer = get_layer(name)
    if layer is None:
        return HttpResponse(json.dumps(dict(polys=[])), content_type='application/json')
                            
    CCDs = layer.ccds_touching_box(north, south, east, west, Nmax=10000)
    print('No CCDs touching box from layer', layer)
    if CCDs is None:
        return HttpResponse(json.dumps(dict(polys=[])), content_type='application/json')

    CCDs.cut(np.lexsort((CCDs.expnum, CCDs.filter)))
    ccds = []
    for c in CCDs:
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
    name = clean_layer_name(name)
    if name in ['decals-dr5', 'decals-dr7', 'ls-dr8-south', 'ls-dr9-south']:
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
        T = fits_table()
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
    name = request_layer_name(req)
    print('Name:', name)
    name = clean_layer_name(name)
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
    
def get_ccd_object(surveyname, ccd):
    expnum,ccdname = parse_ccd_name(ccd)
    survey = get_survey(surveyname)
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

def ccd_detail(req, layer_name, ccd):
    layer_name = clean_layer_name(layer_name)
    survey, c = get_ccd_object(layer_name, ccd)

    cols = c.columns()
    if 'cpimage' in cols:
        about = ('CCD %s, image %s, hdu %i; exptime %.1f sec, seeing %.1f arcsec' %
                 (ccd, c.cpimage, c.cpimage_hdu, c.exptime, c.fwhm*0.262))
        return HttpResponse(about)

    rect = req.GET.get('rect', None)
    if rect is not None:
        words = rect.split(',')
        if len(words) == 4:
            try:
                x = int(words[0], 10)
                y = int(words[1], 10)
                w = int(words[2], 10)
                h = int(words[3], 10)
                rect = (x,y,w,h)
            except:
                pass

    imgurl   = my_reverse(req, 'image_data', args=[layer_name, ccd])
    dqurl    = my_reverse(req, 'dq_data', args=[layer_name, ccd])
    ivurl    = my_reverse(req, 'iv_data', args=[layer_name, ccd])
    imgstamp = my_reverse(req, 'image_stamp', args=[layer_name, ccd])
    ivstamp = my_reverse(req, 'iv_stamp', args=[layer_name, ccd])
    dqstamp = my_reverse(req, 'dq_stamp', args=[layer_name, ccd])
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

    image_stamp_scale = 4
    sw = c.width  // image_stamp_scale
    sh = c.height // image_stamp_scale
    rectsvg = ''
    rectsvg2 = ''
    if rect is not None:
        x,y,w,h = rect
        s = image_stamp_scale
        rectsvg = (('<rect x="%i" y="%i" width="%i" height="%i" stroke="orange" ' +
                   'fill="transparent" stroke-width="2" />')
                   % (x//s, y//s, w//s, h//s))
        rectsvg2 = (('<rect x="%i" y="%i" width="%i" height="%i" stroke="blue" ' +
                   'fill="transparent" stroke-width="2" />')
                   % (x//s, y//s, w//s, h//s))
    from urllib.parse import quote
    viewer_url = settings.ROOT_URL + quote('/?ra=%.4f&dec=%.4f&layer=%s' % (c.ra, c.dec, layer_name))

    dtd_tag = '''<!DOCTYPE html
PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"DTD/xhtml1-transitional.dtd">
'''
    axspace = 50
    axis1 = '<polyline points="0,{sw} 0,0 {sh},0" stroke="gray" fill="transparent" stroke-width="2" />'.format(sw=sw, sh=sh)
    axstep = 500
    for x in range(axstep, c.width, axstep):
        axis1 += '<polyline points="{sx},0 {sx},-20" stroke="gray" fill="transparent" stroke-width="1" />'.format(sx=x//image_stamp_scale)
    for y in range(axstep, c.height, axstep):
        axis1 += '<polyline points="0,{sy} -20,{sy}" stroke="gray" fill="transparent" stroke-width="1" />'.format(sy=y//image_stamp_scale)

    axis2 = '<g transform="translate({axspace} {sh})">'.format(axspace=axspace, sh=sh)
    for x in range(axstep, c.width, axstep):
      axis2 += '<text x="{sx}" y="40" text-anchor="middle" dominant-baseline="bottom">{x}</text>'.format(
          sx=x//image_stamp_scale, x=x)
    for y in range(axstep, c.height, axstep):
        axis2 += '<text x="-20" y="-{sy}" text-anchor="end" dominant-baseline="middle">{y}</text>'.format(
            sy=y//image_stamp_scale, y=y)
    axis2 += '</g>'
    
    about = dtd_tag + html_tag + '''<title>CCD details for {ccd}</title>
<script src="{static}/jquery-3.5.1.min.js"></script>
</head>
<body>
CCD {ccd}, image {c.image_filename}, hdu {c.image_hdu}; exptime {c.exptime:.1f} sec, seeing {c.seeing:.1f} arcsec, fwhm {c.fwhm:.1f} pix, band {c.filter}, RA,Dec <a href="{viewer_url}">{c.ra:.4f}, {c.dec:.4f}</a>
<br />
{flags}
Observed MJD {c.mjd_obs:.3f}, {c.date_obs} {c.ut} UT
<ul>
<li>image: <a href="{imgurl}">{ccd}</a>
{ooitext}</li>
<li>weight or inverse-variance: <a href="{ivurl}">{ccd}</a></li>
<li>data quality (flags): <a href="{dqurl}">{ccd}</a></li>
</ul>
<div>Mouse: <span id="image_coords"></span>  Click: <span id="image_click"></span></div><br/>
<svg version="1.1" baseProfile="full" xmlns="http://www.w3.org/2000/svg"
  width="{swa}" height="{sha}">
  <g transform="translate({axspace} 0)">
    <image x="0" y="0" width="{sw}" height="{sh}" href="{imgstamp}" id="image_stamp" />
    <g transform="translate(0 {sh}) scale(1 -1)">
    {rectsvg}
    {axis1}
    </g>
  </g>
  {axis2}
</svg>
<br />
<div>Mouse: <span id="iv_coords"></span>  Click: <span id="iv_click"></span></div><br/>
<svg version="1.1" baseProfile="full" xmlns="http://www.w3.org/2000/svg"
  width="{swa}" height="{sha}">
  <g transform="translate({axspace} 0)">
    <image x="0" y="0" width="{sw}" height="{sh}" href="{ivstamp}" id="iv_stamp" />
    <g transform="translate(0 {sh}) scale(1 -1)">
      {rectsvg2}
      {axis1}
    </g>
  </g>
  {axis2}
</svg>
<br />
<div>Mouse: <span id="dq_coords"></span>  Click: <span id="dq_click"></span></div><br/>
<svg version="1.1" baseProfile="full" xmlns="http://www.w3.org/2000/svg"
  width="{swa}" height="{sha}">
  <g transform="translate({axspace} 0)">
    <image x="0" y="0" width="{sw}" height="{sh}" href="{dqstamp}" id="dq_stamp" />
    <g transform="translate(0 {sh}) scale(1 -1)">
      {rectsvg}
      {axis1}
    </g>
  </g>
  {axis2}
</svg>
<script>
  function mouse(e, target) {{
    imx = e.offsetX * {scale};
    imy = ({sh} - e.offsetY) * {scale};
    $(target).html('(' + imx + ', ' + imy + ')');
  }}

  $(document).ready(function() {{
    $("#image_stamp").on('mousemove', function(e) {{ return mouse(e, "#image_coords"); }});
    $("#image_stamp").on('click', function(e) {{ return mouse(e, "#image_click"); }});
    $("#iv_stamp").on('mousemove', function(e) {{ return mouse(e, "#iv_coords"); }});
    $("#iv_stamp").on('click', function(e) {{ return mouse(e, "#iv_click"); }});
    $("#dq_stamp").on('mousemove', function(e) {{ return mouse(e, "#dq_coords"); }});
    $("#dq_stamp").on('click', function(e) {{ return mouse(e, "#dq_click"); }});
  }});
</script>
</body>
</html>
'''.format(ccd=ccd, c=c, sw=sw, sh=sh, swa=sw+axspace, sha=sh+axspace,
           axspace=axspace, axis1=axis1, axis2=axis2,
           rectsvg=rectsvg, rectsvg2=rectsvg2, viewer_url=viewer_url,
           flags=flags, imgurl=imgurl, ooitext=ooitext, ivurl=ivurl, dqurl=dqurl,
           imgstamp=imgstamp, ivstamp=ivstamp, dqstamp=dqstamp,
           static=settings.STATIC_URL, scale=image_stamp_scale)

    return HttpResponse(about, content_type='application/xhtml+xml')

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
    layername = request_layer_name(req)
    sname = layer_to_survey_name(layername)
    layer = get_layer(layername)
    survey = get_survey(sname)
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
        ]
    brick_html = layer.brick_details_body(brick)
    html.extend(brick_html)
    
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
            html.extend(ccds_overlapping_html(req, ccds, layer))

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

    if 'photometric' in cols:
        print('Cut', len(ccds), 'to', np.sum(ccds.photometric), 'CCDs on photometric column')
        ccds.cut(ccds.photometric)

    return ccds

def format_jpl_url(req, ra, dec, ccd):
    jpl_url = my_reverse(req, jpl_lookup)
    return ('%s?ra=%.4f&dec=%.4f&date=%s&camera=%s' %
            (jpl_url, ra, dec, ccd.date_obs + ' ' + ccd.ut, ccd.camera.strip()))


def ccds_overlapping_html(req, ccds, layer, ra=None, dec=None):
    jplstr = ''
    if ra is not None:
        jplstr = '<th>JPL</th>'
    html = ['<table class="ccds"><thead><tr><th>name</th><th>exptime</th><th>seeing</th><th>propid</th><th>date</th><th>image</th><th>image (ooi)</th><th>weight map</th><th>data quality map</th>%s</tr></thead><tbody>' % jplstr]
    for ccd in ccds:
        ccdname = '%s %i %s %s' % (ccd.camera.strip(), ccd.expnum,
                                   ccd.ccdname.strip(), ccd.filter.strip())
        ccdtag = ccdname.replace(' ','-')
        imgurl = my_reverse(req, 'image_data', args=(layer, ccdtag))
        dqurl  = my_reverse(req, 'dq_data', args=(layer, ccdtag))
        ivurl  = my_reverse(req, 'iv_data', args=(layer, ccdtag))
        imgooiurl = imgurl + '?type=ooi'
        ooitext = ''
        if '_oki_' in ccd.image_filename:
            ooitext = '<a href="%s">ooi</a>' % imgooiurl
        jplstr = ''
        if ra is not None:
            jplstr = '<td><a href="%s">JPL</a></td>' % format_jpl_url(req, ra, dec, ccd)
        html.append(('<tr><td><a href="%s">%s</a></td><td>%.1f</td><td>%.2f</td>' +
                     '<td>%s</td><td>%s</td><td><a href="%s">%s</a></td><td>%s</td><td><a href="%s">oow</a></td><td><a href="%s">ood</a></td>%s</tr>') % (
                         my_reverse(req, ccd_detail, args=(layer, ccdtag)), ccdname,
                         ccd.exptime, ccd.seeing, ccd.propid, ccd.date_obs + ' ' + ccd.ut[:8],
                         imgurl, ccd.image_filename.strip(), ooitext, ivurl, dqurl,
                         jplstr))
    html.append('</tbody></table>')
    return html

def coadd_psf(req):
    return exposures_common(req, False, True)

def exposures_tgz(req):
    return exposures_common(req, True, False)

def exposures(req):
    return exposures_common(req, False, False)

def exposures_common(req, tgz, copsf):
    from astrometry.util.util import Tan
    from astrometry.util.starutil_numpy import degrees_between
    import numpy as np
    from legacypipe.survey import wcs_for_brick

    layername = request_layer_name(req)
    layername = layer_to_survey_name(layername)
    survey = get_survey(layername)
    layer = get_layer(layername)

    if not layer.has_cutouts():
        return HttpResponse('No cutouts for layer ' + layername)

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
            tim = im.get_tractor_image(slc, pixPsf=True,
                                       subsky=True, nanomaggies=False,
                                       pixels=tgz, dq=tgz, normalizePsf=copsf,
                                       old_calibs_ok=True)
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

            # Work-around for fitsio error:
            # FITSIO status = 402: bad float to string conversion
            # Warning: the following keyword does not conform to the HIERARCH convention
            # HIERARCH TIME_RECORDED = '2017-03-02T07:57:12.149236'
            # Error in ffd2e: double value is a NaN or INDEF
            #     http://legacysurvey.org/viewer-dev/cutouts-tgz/?ra=211.7082&dec=0.9631&size=100&layer=dr9i-south

            def filter_header(inhdr):
                # Go through each card in the header and try to write it...?
                import fitsio
                hdr = fitsio.FITSHDR()
                for r in inhdr.records():
                    try:
                        temphdr = fitsio.FITSHDR()
                        temphdr.add_record(r)
                        tempfits = fitsio.FITS('mem://', 'rw')
                        tempfits.write(None, header=temphdr)
                    except:
                        print('Failed to write header card (skipping):', r)
                        continue
                    #rawdata = self.fits.read_raw()
                    ## close the fitsio file
                    #self.fits.close()
                    hdr.add_record(r)
                return hdr

            phdr = filter_header(tim.primhdr)
            hdr = filter_header(tim.hdr)
            
            outfn = '%s-%08i-%s-image.fits' % (ccd.camera, ccd.expnum, ccd.ccdname)
            imgfns.append(outfn)
            ofn = os.path.join(subdir, outfn)
            fitsio.write(ofn, None, header=phdr, clobber=True)
            fitsio.write(ofn, imgdata, header=hdr, extname=ccd.ccdname)

            outfn = '%s-%08i-%s-weight.fits' % (ccd.camera, ccd.expnum, ccd.ccdname)
            ofn = os.path.join(subdir, outfn)
            fitsio.write(ofn, None, header=phdr, clobber=True)
            fitsio.write(ofn, ivdata, header=hdr, extname=ccd.ccdname)

            outfn = '%s-%08i-%s-dq.fits' % (ccd.camera, ccd.expnum, ccd.ccdname)
            ofn = os.path.join(subdir, outfn)
            fitsio.write(ofn, None, header=phdr, clobber=True)
            fitsio.write(ofn, dqdata, header=hdr, extname=ccd.ccdname)

            outfn = '%s-%08i-%s-psfex.fits' % (ccd.camera, ccd.expnum, ccd.ccdname)
            ofn = os.path.join(subdir, outfn)
            psfex.fwhm = tim.psf_fwhm
            psfex.writeto(ofn)

            outfn = '%s-%08i-%s-psfimg.fits' % (ccd.camera, ccd.expnum, ccd.ccdname)
            ofn = os.path.join(subdir, outfn)
            fitsio.write(ofn, psfimg, header=phdr, clobber=True)


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

        dim = survey.get_image_object(c)
        print('Image object:', dim)
        print('Filename:', dim.imgfn)
        #wcs = dim.get_wcs()
        awcs = survey.get_approx_wcs(c)

        ok,x,y = awcs.radec2pixelxy(ra, dec)
        x = int(np.round(x-1))
        y = int(np.round(y-1))
        if x < -size or x >= c.width+size or y < -size or y >= c.height+size:
            continue
        ccds.append((c, x, y))

    B = survey.get_bricks_readonly()
    I = np.flatnonzero((B.ra1  <= ra)  * (B.ra2  >= ra) *
                       (B.dec1 <= dec) * (B.dec2 >= dec))
    if len(I):
        brick = B[I[0]]
        bwcs = wcs_for_brick(brick)
        ok,brickx,bricky = bwcs.radec2pixelxy(ra, dec)
        brick = brick.to_dict()
    else:
        brick = None
        brickx = bricky = []

    from django.shortcuts import render

    url = my_reverse(req, 'exposure_panels', args=('LAYER', '12345', 'EXTNAME'))
    url = url.replace('LAYER', '%s').replace('12345', '%i').replace('EXTNAME', '%s')
    url = req.build_absolute_uri(url)
    # Deployment: http://{s}.DOMAIN/...
    url = url.replace('://www.', '://')
    url = url.replace('://', '://%s.')
    domains = settings.SUBDOMAINS

    ccdsx = []
    for i,(ccd,x,y) in enumerate(ccds):
        fn = ccd.image_filename.replace(settings.DATA_DIR + '/', '')
        ccdlayer = getattr(ccd, 'layer', layername)
        theurl = url % (domains[i%len(domains)], ccdlayer, int(ccd.expnum), ccd.ccdname.strip()) + '?ra=%.4f&dec=%.4f&size=%i' % (ra, dec, size*2)
        expurl = my_reverse(req, 'ccd_detail_xhtml', args=(layername, '%s-%i-%s' % (ccd.camera.strip(), int(ccd.expnum), ccd.ccdname.strip())))
        expurl += '?rect=%i,%i,%i,%i' % (x-size, y-size, W, H)
        ccdsx.append(('<br/>'.join(['CCD <a href="%s">%s %s %i %s</a>, %.1f sec (x,y ~ %i,%i)' % (expurl, ccd.camera, ccd.filter, ccd.expnum, ccd.ccdname, ccd.exptime, x, y),
                                    '<small>(%s [%i])</small>' % (fn, ccd.image_hdu),
                                    '<small>(observed %s @ %s = MJD %.6f)</small>' % (ccd.date_obs, ccd.ut, ccd.mjd_obs),
                                    '<small><a href="%s">Look up in JPL Small Bodies database</a></small>' % format_jpl_url(req, ra, dec, ccd),]),
                      theurl))
    return render(req, 'exposures.html',
                  dict(ra=ra, dec=dec, ccds=ccdsx, name=layername, layer=layername,
                       drname=getattr(survey, 'drname', layername),
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
    txt = txt.replace('<head>', '<head><base href="https://ssd.jpl.nasa.gov/">')
    return HttpResponse(txt)

def jpl_redirect(req, jpl_url):
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect('https://ssd.jpl.nasa.gov/' + jpl_url + '?' + req.META['QUERY_STRING'])

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



def exposure_panels(req, layer=None, expnum=None, extname=None):
    import pylab as plt
    import numpy as np

    ra = float(req.GET['ra'])
    dec = float(req.GET['dec'])

    kind = req.GET.get('kind', 'image')

    # half-size in DECam pixels
    size = int(req.GET.get('size', '100'), 10)
    size = min(200, size)
    #size = size // 2

    layer = clean_layer_name(layer)
    layer = layer_to_survey_name(layer)
    survey = get_survey(layer)
    print('cutout_panels: survey is', survey)
    ccd = _get_ccd(expnum, extname, survey=survey)
    print('CCD:', ccd)
    print('CCD table: expnum,ccdname', ccd.expnum, ccd.ccdname)
    im = survey.get_image_object(ccd)
    print('Image object:', im)
    print('CCD center: RA,Dec', ccd.ra, ccd.dec, 'and query RA,Dec', ra, dec)
    print('File:', ccd.image_filename, 'HDU:', ccd.image_hdu, 'CCDname:', ccd.ccdname)
    
    wcs = im.get_wcs()
    ok,x,y = wcs.radec2pixelxy(ra, dec)
    x = int(x-1)
    y = int(y-1)
    if not ok:
        print('RA,Dec', ra,dec, 'not in image')

    H,W = im.shape
    x0 = x - size//2
    y0 = y - size//2
    x1 = x0 + size
    y1 = y0 + size

    # Compute padding to add to left/right/top/bottom
    padleft   = max(0, -x0)
    padbottom = max(0, -y0)
    padright  = max(0, x1-W)
    padtop    = max(0, y1-H)

    slc = (slice(max(0, y0), min(H, y1)),
           slice(max(0, x0), min(W, x1)))

    import tempfile
    f,jpegfn = tempfile.mkstemp(suffix='.jpg')
    os.close(f)

    if x1 < 0 or y1 < 0 or x0 >= W or y0 >= H:
        # no overlap
        print('No overlap: x,y [', x0, x1, '], [', y0, y1, ']')
        img = np.zeros((size,size), np.float32)
        kwa = dict(cmap='gray', origin='lower', vmin=0, vmax=1)
        plt.imsave(jpegfn, img, **kwa)
        return send_file(jpegfn, 'image/jpeg', unlink=True)
    
    kwa = dict(cmap='gray', origin='lower')

    trargs = dict(slc=slc, gaussPsf=True, old_calibs_ok=True, tiny=1,
                  trim_edges=False)
                  #readsky=False)
    
    if kind == 'image':
        tim = im.get_tractor_image(invvar=False, dq=False, **trargs)
        from legacypipe.survey import get_rgb
        print('im=',im)
        print('tim=',tim)
        # hack a sky sub
        #tim.data -= np.median(tim.data)
        rgb = get_rgb([tim.data], [tim.band]) #, mnmx=(-1,100.), arcsinh=1.)
        index = dict(g=2, r=1, z=0)[tim.band]
        img = rgb[:,:,index]
        kwa.update(vmin=0, vmax=1)

    elif kind == 'weight':
        tim = im.get_tractor_image(pixels=False, dq=False, invvar=True, **trargs)
        img = tim.getInvvar()
        kwa.update(vmin=0)

    elif kind == 'weightedimage':
        tim = im.get_tractor_image(dq=False, invvar=True, **trargs)
        from legacypipe.survey import get_rgb
        rgb = get_rgb([tim.data * (tim.inverr > 0)], [tim.band]) #, mnmx=(-1,100.), arcsinh=1.)
        index = dict(g=2, r=1, z=0)[tim.band]
        img = rgb[:,:,index]
        kwa.update(vmin=0, vmax=1)

    elif kind == 'dq':
        tim = im.get_tractor_image(pixels=False, dq=True, invvar=False, **trargs)
        img = tim.dq
        # remap bitmasks...
        img = np.log2(1 + img.astype(np.float32))
        img[img == 0.] -= 5.
        kwa.update(vmin=-5)

    #print('slc', slc)
    #print('img', img.shape)
    #print('pad left', padleft, 'right', padright, 'top', padtop, 'bottom', padbottom)

    H,W = img.shape
    if padleft:
        img = np.hstack((np.zeros((H, padleft), img.dtype), img))
        H,W = img.shape
    if padright:
        img = np.hstack((img, np.zeros((H, padright), img.dtype)))
        H,W = img.shape
    if padtop:
        img = np.vstack((img, np.zeros((padtop, W), img.dtype)))
        H,W = img.shape
    if padbottom:
        img = np.vstack((np.zeros((padbottom, W), img.dtype), img))
        H,W = img.shape

    plt.imsave(jpegfn, img, **kwa)
    return send_file(jpegfn, 'image/jpeg', unlink=True)

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

def image_stamp(req, surveyname, ccd, iv=False, dq=False):
    import fitsio
    import tempfile
    import pylab as plt
    import numpy as np
    survey, c = get_ccd_object(surveyname, ccd)
    im = survey.get_image_object(c) #, makeNewWeightMap=False)
    fn = im.imgfn
    ff,tmpfn = tempfile.mkstemp(suffix='.jpg')
    os.close(ff)
    os.unlink(tmpfn)

    kwa = dict(origin='lower')

    cmap = 'gray'
    if iv:
        fn = fn.replace('_ooi_', '_oow_')
        cmap = 'hot'
    elif dq:
        fn = fn.replace('_ooi_', '_ood_')
        cmap = 'tab10'
    print('Reading', fn)

    pix = fitsio.read(fn, ext=c.image_hdu)
    H,W = pix.shape

    # BIN
    scale = 4
    sw,sh = W//scale, H//scale

    if dq:
        # Assume DQ codes (not bitmask)
        out = np.zeros((sh,sw), np.uint8)
        for i in range(scale):
            for j in range(scale):
                out = np.maximum(out, pix[i::scale, j::scale][:sh,:sw])
    else:
        out = np.zeros((sh,sw), np.float32)
        for i in range(scale):
            for j in range(scale):
                out += pix[i::scale, j::scale][:sh,:sw]
        out /= scale**2
        if iv:
            mn,mx = 0,np.percentile(out.ravel(), 99)
        else:
            mn,mx = np.percentile(out.ravel(), [25, 99])
        kwa.update(vmin=mn, vmax=mx)

    #print('imsave: cmap', cmap, 'range', out.min(), out.max())
    plt.imsave(tmpfn, out, cmap=cmap, **kwa)
    return send_file(tmpfn, 'image/jpeg', unlink=True)

def iv_stamp(req, surveyname, ccd):
    return image_stamp(req, surveyname, ccd, iv=True)
def dq_stamp(req, surveyname, ccd):
    return image_stamp(req, surveyname, ccd, dq=True)

layers = {}
def get_layer(name, default=None):
    global layers

    name = clean_layer_name(name)
    if name in layers:
        return layers[name]
    layer = None

    from map.phat import PhatLayer, M33Layer

    if '/' in name or '..' in name:
        pass

    if name == 'ztf':
        layer = ZtfLayer('ztf')

    elif name == 'sdss':
        '''
        "Rebricked" SDSS images.
        - top-level tiles are from sdss2
        - tile levels 6-13 are from sdssco
        (all on sanjaya)

        '''
        layer = ReSdssLayer('sdss')

    elif name == 'ls-dr67':
        dr7 = get_layer('decals-dr7')
        dr6 = get_layer('mzls+bass-dr6')
        layer = LegacySurveySplitLayer(name, dr6, dr7, 32.)
        layer.drname = 'Legacy Surveys DR6+DR7'

    elif name in ['ls-dr8', 'ls-dr8-model', 'ls-dr8-resid']:
        suff = name.replace('ls-dr8', '')
        north = get_layer('ls-dr8-north' + suff)
        south = get_layer('ls-dr8-south' + suff)
        ### NOTE, must also change the javascript in template/index.html !
        layer = LegacySurveySplitLayer(name, north, south, 32.375)
        layer.drname = 'Legacy Surveys DR8'

    elif name in ['ls-dr9', 'ls-dr9-model', 'ls-dr9-resid']:
        suff = name.replace('ls-dr9', '')
        north = get_layer('ls-dr9-north' + suff)
        south = get_layer('ls-dr9-south' + suff)
        ### NOTE, must also change the javascript in template/index.html !
        layer = LegacySurveySplitLayer(name, north, south, 32.375)
        layer.drname = 'Legacy Surveys DR9'

    elif name in ['dr9sv', 'dr9sv-model', 'dr9sv-resid']:
        suff = name[5:]
        north = get_layer('dr9sv-north' + suff)
        south = get_layer('dr9sv-south' + suff)
        ### NOTE, must also change the javascript in template/index.html !
        layer = LegacySurveySplitLayer(name, north, south, 32.375)
        layer.drname = 'Legacy Surveys DR9-SV'

    elif name == 'phat':
        layer = PhatLayer('phat')

    elif name == 'm33':
        layer = M33Layer('m33')

    elif name == 'eboss':
        survey = get_survey('eboss')
        layer = ReDecalsLayer('eboss', 'image', survey)

    elif name == 'des-dr1':
        layer = DesLayer('des-dr1')

    elif name == 'ps1':
        layer = PS1Layer('ps1')

    elif name == 'vlass1.2':
        layer = VlassLayer('vlass1.2')

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

    elif name == 'unwise-w1w2':
        layer = UnwiseLayer('unwise-w1w2',
                            os.path.join(settings.DATA_DIR, 'unwise-w1w2'))
    elif name == 'unwise-neo2':
        layer = UnwiseLayer('unwise-neo2',
                            os.path.join(settings.DATA_DIR, 'unwise-neo2'))
    elif name == 'unwise-neo3':
        layer = RebrickedUnwise('unwise-neo3',
                            os.path.join(settings.DATA_DIR, 'unwise-neo3'))
    elif name == 'unwise-neo4':
        layer = RebrickedUnwise('unwise-neo4',
                            os.path.join(settings.DATA_DIR, 'unwise-neo4'))
    elif name == 'unwise-neo6':
        layer = RebrickedUnwise('unwise-neo6',
                                os.path.join(settings.DATA_DIR, 'unwise-neo6'))

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
            ngp_filename=os.path.join(settings.DATA_DIR, 'halpha', 'Halpha_4096_ngp.fits'),
            sgp_filename=os.path.join(settings.DATA_DIR, 'halpha', 'Halpha_4096_sgp.fits'))
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


    # elif 'dr8b' in name or 'dr8c' in name or 'dr8i' in name:
    #     # Generic NON-rebricked
    #     print('get_layer:', name, '-- generic')
    #     basename = name
    #     if name.endswith('-model'):
    #         basename = name[:-6]
    #     if name.endswith('-resid'):
    #         basename = name[:-6]
    #     survey = get_survey(basename)
    #     if survey is not None:
    #         image = DecalsLayer(basename, 'image', survey)
    #         model = DecalsModelLayer(basename + '-model', 'model', survey,
    #                                  drname=basename)
    #         resid = DecalsResidLayer(image, model, basename + '-resid', 'resid', survey,
    #                                    drname=basename)
    #         layers[basename] = image
    #         layers[basename + '-model'] = model
    #         layers[basename + '-resid'] = resid
    #         layer = layers[name]

    elif name == 'hsc-dr2':
        layer = HscLayer('hsc-dr2')
    
    if layer is None:
        # Try generic rebricked
        #print('get_layer:', name, '-- generic')
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
    name = clean_layer_name(name)
    def view(request, ver, zoom, x, y, **kwargs):
        layer = get_layer(name)
        return layer.get_tile(request, ver, zoom, x, y, **kwargs)
    return view

def any_tile_view(request, name, ver, zoom, x, y, **kwargs):
    name = clean_layer_name(name)
    layer = get_layer(name)
    if layer is None:
        return HttpResponse('no such layer')
    return layer.get_tile(request, ver, zoom, x, y, **kwargs)

def any_fits_cat(req, name, **kwargs):
    #print('any_fits_cat(', name, ')')
    name = clean_layer_name(name)
    layer = get_layer(name)
    if layer is None:
        return HttpResponse('no such layer')
    bb = get_radec_bbox(req)
    if bb is None:
        return HttpResponse('no ra,dec bbox')
    ralo,rahi,declo,dechi = bb
    return layer.get_catalog(req, ralo, rahi, declo, dechi)

def get_radec_bbox(req):
    print('get_radec_bbox()')
    try:
        ralo = float(req.GET.get('ralo'))
        rahi = float(req.GET.get('rahi'))
        declo = float(req.GET.get('declo'))
        dechi = float(req.GET.get('dechi'))
        print('get_radec_bbox() ->', ralo,rahi,declo,dechi)
        return ralo,rahi,declo,dechi
    except:
        print('Failed to parse RA,Dec bbox:')
        import traceback
        traceback.print_exc()
        return None

@needs_layer()
def cutout_wcs(req):
    from astrometry.util.util import Tan
    import numpy as np
    args = []
    for k in ['crval1','crval2','crpix1','crpix2',
              'cd11','cd12','cd21','cd22','imagew','imageh']:
        v = req.GET.get(k)
        fv = float(v)
        args.append(fv)
    wcs = Tan(*args)
    pixscale = wcs.pixel_scale()
    x = y = 0

    layer = req.layer
    scale = int(np.floor(np.log2(pixscale / layer.pixscale)))
    scale = np.clip(scale, 0, layer.maxscale)
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

    import logging
    lvl = logging.DEBUG
    logging.basicConfig(level=lvl, format='%(message)s', stream=sys.stdout)

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
    #r = c.get('/vlass/1/10/1015/228.jpg')
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
    #r = c.get('/lslga/1/cat.json?ralo=23.3077&rahi=23.4725&declo=30.6267&dechi=30.7573')
    #r = c.get('/phat-clusters/1/cat.json?ralo=10.8751&rahi=11.2047&declo=41.3660&dechi=41.5936')
    #r = c.get('/sdss-wcs/?crval1=195.00000&crval2=60.00000&crpix1=384.4&crpix2=256.4&cd11=1.4810e-4&cd12=0&cd21=0&cd22=-1.4810e-4&imagew=768&imageh=512')
    #r = c.get('/cutout-wcs/?crval1=195.00000&crval2=60.00000&crpix1=384.4&crpix2=256.4&cd11=1.4810e-4&cd12=0&cd21=0&cd22=-1.4810e-4&imagew=768&imageh=512')
    #r = c.get('/lslga/1/cat.json?ralo=23.3077&rahi=23.4725&declo=30.6267&dechi=30.7573')
    #r = c.get('/phat-clusters/1/cat.json?ralo=10.8751&rahi=11.2047&declo=41.3660&dechi=41.5936')
    #r = c.get('/data-for-radec/?ra=35.8889&dec=-2.7425&layer=dr8-test6')
    #r = c.get('/ccd/dr8-test6/decam-262575-N12-z')
    #r = c.get('/ps1/1/13/7517/2091.jpg')
    #r = c.get('/cutout-wcs/?crval1=0.00000&crval2=0.00000&crpix1=384.5&crpix2=256.5&cd11=1.4812e-4&cd12=0&cd21=0&cd22=-1.4812e-4&imagew=768&imageh=512&layer=ls-dr67')
    #r = c.get('/dr8-test10/1/9/462/260.jpg')
    #r = c.get('/dr8-test10/1/13/7395/4163.jpg')
    #r = c.get('/cutout_panels/decals-dr7/634843/S24/?x=1658&y=799&size=100')
    #r = c.get('/hsc/1/7/41/40.jpg')
    #r = c.get('/cutout_panels/decals-dr7/634843/S24/?x=1658&y=799&size=100')
    #class r = c.get('/cutout_panels/decals-dr7/392804/N13/?x=1723&y=2989&size=100&kind=weightedimage')
    #r = c.get('/cutout_panels/decals-dr5/335553/N17/?x=1034&y=800&size=100')
    #r = c.get('/hsc2/1/15/16505/16429.jpg')
    #r = c.get('/hsc2/1/8/116/129.jpg')
    #r = c.get('/hsc2/1/1/0/0.jpg')
    # r = c.get('/dr8-north/1/14/7696/5555.jpg')
    # r = c.get('/dr8-north/1/13/3848/2777.jpg')
    # r = c.get('/dr8-north/1/12/1924/1388.jpg')
    # r = c.get('/dr8-north/1/11/962/695.jpg')
    # r = c.get('/dr8-north/1/10/481/347.jpg')
    # r = c.get('/dr8-north/1/9/240/173.jpg')
    #r = c.get('/dr8-north/1/11/910/787.jpg')
    #r = c.get('/dr8-north/1/11/967/693.jpg')
    #r = c.get('/dr8-north/1/9/237/175.jpg')
    #r = c.get('/dr8-north/1/8/112/71.jpg')
    #r = c.get('/dr8-north/1/14/4578/6019.jpg')
    #r = c.get('/dr8-south/1/13/3327/3329.jpg')
    #r = c.get('/cutouts/?ra=213.7119&dec=45.0500&layer=dr8')
    #r = c.get('/dr8-model/1/14/6675/6653.jpg')
    #r = c.get('/dr8-south/1/5/30/20.jpg')
    # Problems with tilings
    #r = c.get('/dr8-south/1/7/117/56.jpg')
    #r = c.get('/dr8-south/1/6/47/40.jpg')
    #r = c.get('/dr8-north/1/14/10580/6658.cat.json')
    #r = c.get('/dr8-south/1/14/10580/6656.cat.json')
    #r = c.get('/dr8/1/14/10580/6657.cat.json')
    #r = c.get('/dr8/1/14/9389/3788.cat.json')
    #r = c.get('/ccds/?ralo=192.2058&rahi=192.7009&declo=19.1607&dechi=19.4216&id=dr8')
    #r = c.get('/exps/?ralo=192.9062&rahi=193.8963&declo=32.1721&dechi=32.6388&id=dr8-south')
    #r = c.get('/data-for-radec/?ra=127.1321&dec=30.4327&layer=dr8')
    #r = c.get('/cutout.jpg?ra=159.8827&dec=-0.6241&zoom=13&layer=dr8')
    #r = c.get('/dr8-south/1/12/2277/2055.jpg')
    #r = c.get('/cutouts/?ra=194.5524&dec=26.3962&layer=dr8')
    #r = c.get('/cutout_panels/dr8/721218/N10/?x=21&y=328&size=100')
    #r = c.get('/cutout_panels/decals-dr5/634863/N10/?x=1077&y=3758&size=100')
    #r = c.get('/cutouts/?ra=194.5517&dec=26.3977&layer=decals-dr5')
    #s = get_survey('decals-dr5')
    #s.get_ccds()
    #r = c.get('/data-for-radec/?ra=54.8733&dec=-13.1156&layer=des-dr1')
    #r = c.get('/ccd/dr8/decam-767361-N29-z/')
    #r = c.get('/image-data/dr8/decam-767361-N29-z')
    #r = c.get('/')
    #r = c.get('/jpl_lookup/?ra=346.6075&dec=-3.3056&date=2017-07-18%2007:28:16.522187&camera=decam')
    #r = c.get('/urls')
    #r = c.get('/dr8/1/14/16023/6558.cat.json')
    #r = c.get('/cutout.fits?ra=212.1944&dec=4.9083&layer=dr8-south&pixscale=0.27')
    #r = c.get('/cutout_panels/dr8-south/680175/N5/?ra=5.4638&dec=22.4002&size=100')
    #r = c.get('/dr9sv-north/1/11/1225/827.jpg')
    #r = c.get('/dr9sv-south/1/12/2412/1671.jpg')
    #r = c.get('/dr9sv-north/1/10/378/377.jpg')
    #r = c.get('/dr9sv-north/1/9/189/188.jpg')
    #r = c.get('/dr9sv-north/1/11/1220/823.jpg')
    #r = c.get('/dr9sv-north/1/10/396/372.jpg')
    #r = c.get('/bricks/?ralo=33.5412&rahi=33.5722&declo=-2.2242&dechi=-2.2070&layer=dr9sv')
    #r = c.get('/manga/1/cat.json?ralo=194.4925&rahi=194.5544&declo=29.0022&dechi=29.0325')
    #r = c.get('/bricks/?ralo=33.5412&rahi=33.5722&declo=-2.2242&dechi=-2.2070&layer=dr9sv')
    #r = c.get('/manga/1/cat.json?ralo=194.4925&rahi=194.5544&declo=29.0022&dechi=29.0325')
    #r = c.get('/fornax-model/1/11/1823/1233.jpg')
    #r = c.get('/dr9-test-9.2/1/14/14809/8145.jpg')
    #r = c.get('/brick/1379p505/?layer=dr8')
    #names = ['%s %s' % (c.strip(),i) for c,i in zip(T.ref_cat, T.ref_id)]
    #r = c.get('/cutout_panels/decals-dr7/511284/N11/?ra=163.2651&dec=13.1159&size=100')
    #r = c.get('/jpeg-cutout?ra=144.5993113&dec=4.014711559&size=128&layer=decals-dr7-resid&pixscale=0.262&bands=grz')
    #r = c.get('/cutout_panels/dr8-south/432043/N6/?ra=185.8736&dec=19.4258&size=100')
    #r = c.get('/cutout_panels/decals-dr5/521375/N11/?ra=163.2651&dec=13.1159&size=100')
    #r = c.get('/masks-dr9/1/cat.json?ralo=221.3107&rahi=221.8057&declo=1.7637&dechi=2.0399')
    #r = c.get('/masks-dr9/1/cat.json?ralo=359.6086&rahi=0.1037&declo=20.6203&dechi=20.8787')
    #r = c.get('/cutout_panels/dr8-north/78970148/CCD1/?ra=226.2625&dec=33.7491&size=100')
    #r = c.get('/unwise-neo6/1/7/79/61.jpg')
    #r = c.get('/unwise-neo6/1/7/72/60.jpg')
    #r = c.get('/cutouts-tgz/?ra=223.346&dec=43.3603&size=100&layer=dr9h-north')
    #r = c.get('/cutout_panels/decals-dr7/659598/N23/?ra=328.5984&dec=15.1565&size=100')
    #r = c.get('/')
    #r = c.get('/cutout_panels/decals-dr5/356224/S4/?ra=57.8589&dec=-15.4102&size=100')
    #r = c.get('/cutouts-tgz/?ra=57.8589&dec=-15.4102&size=100&layer=decals-dr5')
    #r = c.get('/vlass1.2/1/14/7569/6814.jpg')
    #r = c.get('/cutouts-tgz/?ra=211.7082&dec=0.9631&size=100&layer=dr9i-south')
    #r = c.get('/vlass1.2/1/11/31/1004.jpg')
    #r = c.get('/vlass1.2/1/6/0/30.jpg')
    #r = c.get('/vlass1.2/1/6/42/31.jpg')
    #r = c.get('/sga/1/cat.json?ralo=262.6500&rahi=262.7119&declo=35.7056&dechi=35.7336')
    #r = c.get('/exposures/?ra=129.3671&dec=24.9471&layer=dr8')
    #r = c.get('/namequery/?obj=NGC 5614')
    #r = c.get('/dr9k-south/2/7/33/57.jpg')
    #r = c.get('/dr9k-south/2/14/7054/7872.jpg')
    #r = c.get('/ccd/dr9k-south/decam-764080-N11.xhtml?rect=907,493,200,200')
    #r = c.get('/exposure_panels/dr8-south/702779/N5/?ra=36.5587&dec=-4.0677&size=100')
    #r = c.get('/iv-stamp/dr8/decam-361654-S31.jpg')
    #r = c.get('/dq-stamp/dr8/decam-361654-S31.jpg')
    #r = c.get('/exposures/?ra=190.1624&dec=63.0288&layer=dr9m-north')
    #r = c.get('/cutout.jpg?ra=239.6286&dec=-3.7784&layer=unwise-neo4&pixscale=0.13')
    #r = c.get('/masks-dr9/1/cat.json?ralo=14.4361&rahi=14.4980&declo=-35.8660&dechi=-35.8380')
    #r = c.get('/ztf/1/14/7281/6759.jpg')
    #r = c.get('/cutout.jpg?ra=199.68&dec=29.42&layer=ztf&pixscale=1.0&size=1000')
    #r = c.get('/cutout.jpg?ra=200.0108&dec=30.0007&layer=ztf&pixscale=0.25')
    #r = c.get('/ztf/1/12/1823/2048.jpg')
    #r = c.get('/ztf/1/11/911/1023.jpg')
    #r = c.get('/dr9m-north/1/12/2478/1493.jpg')
    #r = c.get('/dr9m-north/1/13/3520/3006.jpg')
    #r = c.get('/dr9m-south-model/1/8/238/104.jpg')
    #r = c.get('/ls-dr9-south/1/9/482/214.jpg')
    #r = c.get('/ls-dr9-south/1/9/481/210.jpg')
    #r = c.get('/ls-dr9-south/1/7/119/51.jpg')
    #r = c.get('/ls-dr9-south/1/6/59/25.jpg')
    #r = c.get('/ls-dr9/1/2/1/1.jpg')
    #r = c.get('/exps/?ralo=246.8384&rahi=247.3335&declo=32.6943&dechi=32.9266&layer=ls-dr9-south')
    #r = c.get('/exposure_panels/ls-dr9-south/624475/S21/?ra=128.6599&dec=20.0039&size=100&kind=dq')
    #r = c.get('/')
    #r = c.get('/targets-dr9-sv1-dark/1/cat.json?ralo=247.4432&rahi=247.5669&declo=29.9699&dechi=30.0297')
    #r = c.get('/targets-dr9-sv1-dark/1/cat.json?ralo=119.8540&rahi=120.3490&declo=37.6292&dechi=37.8477')
    #r = c.get('/targets-dr9-sv1-dark/1/cat.json?ralo=119.8828&rahi=120.3779&declo=37.6129&dechi=37.8315')
    #r = c.get('/ls-dr9-south/1/6/60/26.jpg')
    #r = c.get('/?layer=ls-dr9&zoom=12&tile=80256&fiber=4091')
    #r = c.get('/ls-dr9/1/3/1/3.jpg')
    #r = c.get('/')
    #r = c.get('/ls-dr9/1/5/0/12.jpg')
    #r = c.get('/cutout.jpg?ra=182.5248&dec=18.5415&layer=ls-dr9&pixscale=1.00')
    #r = c.get('/gaia-edr3/1/cat.json?ralo=200.8723&rahi=201.3674&declo=13.9584&dechi=14.2264')
    #r = c.get('/exposure_panels/mzls+bass-dr6/75120132/CCD1/?ra=230.6465&dec=56.2721&size=100')
    #r = c.get('/ls-dr9/1/8/181/103.jpg')
    #r = c.get('/exposure_panels/decals-dr5/496441/N11/?ra=121.2829&dec=29.6660&size=100')
    #r = c.get('/exposures/?ra=121.2829&dec=29.666&layer=decals-dr5')
    #r = c.get('/exposure_panels/decals-dr5/392401/N11/?ra=121.2829&dec=29.6660&size=100')
    #r = c.get('/decals-dr7/1/13/4070/3626.cat.json')
    #r = c.get('/photoz-dr9/1/cat.json?ralo=183.1147&rahi=183.1487&declo=12.1365&dechi=12.1551')
    #r = c.get('/ls-dr9.1.1/1/14/9549/8100.jpg')
    #r = c.get('/ls-dr9.1.1/1/13/4768/4040.    print('r:', type(r))
    #r = c.get('/ls-dr9-south/1/14/13604/10378.jpg')
    #r = c.get('/?tile=120')
    #r = c.get('/ls-dr9.1.1/1/14/9571/8085.jpg')
    #r = c.get('/targets-dr9-sv3-dark/1/cat.json?ralo=349.2859&rahi=349.8304&declo=10.1487&dechi=10.4476#NGC 3716')
    #r = c.get('/ls-dr9.1.1-model/1/13/4767/4044.jpg')
    #r = c.get('/ls-dr9.1.1-model/1/12/2383/2022.jpg')
    #r = c.get('/ls-dr9.1.1-resid/1/12/2374/2020.jpg')
    #r = c.get('/targets-dr9-sv3-sec-dark/1/cat.json?ralo=149.7358&rahi=150.2803&declo=2.0732&dechi=2.3768')
    #r = c.get('/ls-dr9-south/1/15/27206/20760.jpg')
    #r = c.get('/ls-dr9-south/1/12/3402/2596.jpg')
    #r = c.get('/ls-dr9-south/1/4/12/10.jpg')
    #r = c.get('/ls-dr9-south/1/5/26/19.jpg')
    r = c.get('/ls-dr9-south/1/6/52/38.jpg')
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
    view = views.get_layer('halpah').get_tile_view()
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
                   scales=dict(J=(2,0.0072),
                               H=(1,0.0032),
                               K=(0,0.002)))

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
