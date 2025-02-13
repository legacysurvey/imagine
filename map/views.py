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
from django.shortcuts import redirect

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
info = print
if not settings.INFO_LOGGING:
    def info(*args, **kwargs):
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
    'cfis-r': [1],
    'cfis-u': [1],

    'eboss': [1,],

    'phat': [1,],
    'm33': [1,],

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

    'decaps2': [2],
    'decaps2-model': [2],
    'decaps2-resid': [2],
    
    'unwise-w1w2': [1],
    'unwise-neo2': [1],
    'unwise-neo3': [1],
    'unwise-neo4': [1],
    'unwise-neo6': [1],
    'unwise-neo7': [1],

    'unwise-neo7-mask': [1],
    
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

# Used in Spin liveness test
def alive(req):
    return HttpResponse('yes')
def checkflavour(req, flavour):
    if flavour == settings.FLAVOUR:
        return HttpResponse('yes flavour ' + flavour)
    else:
        return HttpResponse('bad flavour: web service is ' + settings.FLAVOUR + ', query is ' + flavour,
                            status=500, reason='bad flavour')

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

        #'decaps2': 'decaps',
        #'decaps2-model': 'decaps-model',
        #'decaps2-resid': 'decaps-resid',

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
    layer = layer.replace('-grz', '')

    layer = {
        'ibis-color': 'ibis',
        'ibis-color-ls': 'ibis',
    }.get(layer, layer)
    
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

def is_unions(req):
    host = req.META.get('HTTP_HOST', None)
    return (host == 'unions.legacysurvey.org') or (host == 'cloud.legacysurvey.org')

def index(req, **kwargs):
    #print('Host is', req.META.get('HTTP_HOST', None))
    if is_decaps(req):
        return decaps(req)
    if is_m33(req):
        return m33(req)
    if is_unions(req):
        return unions(req)
    return _index(req, **kwargs)

def test(req):
    maxZoom = 16
    abcd = ['a','b','c','d']
    #nersc = settings.NERSC_TILE_URL
    nersc = 'https://{s}.legacysurvey.org/viewer/{id}/{ver}/{z}/{x}/{y}.jpg'
    nersc_sub = abcd
    ima = settings.STATIC_TILE_URL_B
    ima_sub = abcd
    tileurl = settings.TILE_URL
    
    tileurls = {
        'sdss': [ [1, 13, ima, ima_sub],
                  [14, maxZoom, nersc, nersc_sub], ],
        'cfis_r': [ [1, maxZoom, tileurl, []], ],
        'cfis_u': [ [1, maxZoom, tileurl, []], ],
    }

    args = dict(
        tileurls=tileurls,
        zoom = 13,
        layer = 'sdss',
        ra = 227.017,
        dec = 42.819,
        maxZoom = 16,
        maxNativeZoom = 16,
    )
    from django.shortcuts import render
    return render(req, 'test.html', args)
    
def _index(req,
           default_layer = 'ls-dr9',
           default_radec = (None,None),
           default_zoom = 12,
           rooturl=settings.ROOT_URL,
           maxZoom = 16,
           decaps_first = False,
           merian_first = False,
           **kwargs):


    tileurl = settings.TILE_URL
    subs = settings.SUBDOMAINS
    def_url = [0, maxZoom, tileurl, subs]

    prod_url = settings.STATIC_TILE_URL_B
    #'https://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
    prod_subs = settings.SUBDOMAINS_B
    prod_backstop = [0, maxZoom, prod_url, prod_subs]

    aws_tile_url = 'https://s3.us-west-1.amazonaws.com/{id}.legacysurvey.org/{z}/{x}/{y}.jpg'
    max_aws_zoom = 14
    aws_url = [0, max_aws_zoom, aws_tile_url, []]

    aws_unwise_url = 'https://s3.us-west-2.amazonaws.com/{id}.legacysurvey.org/{z}/{x}/{y}.jpg'

    # default maxNativeZoom
    maxnative = 14;

    tile_layers = {
        'sdss': ['SDSS', [[14, maxZoom, tileurl, subs], prod_backstop], maxnative, 'sdss'],
        'galex': ['GALEX', [[0, 9, prod_url, prod_subs], def_url], 12, 'galex'],
        'sfd': ['SFD Dust', [[7, 10, tileurl, subs], prod_backstop], 10, 'sfd'],
        'wssa': ['WISE 12-micron dust map', [[9, 10, tileurl, subs], prod_backstop], 10, 'wssa'],
        'halpha': ['Halpha map', [[7, 10, tileurl, subs], prod_backstop], 10, 'halpha'],
    }

    if settings.ENABLE_DR10:
        dr10layers = {
            'ls-dr10-south': ['Legacy Surveys DR10-south images',
                              [def_url],  maxnative, 'ls'],
	    'ls-dr10': ['Legacy Surveys DR10 images', [def_url], maxnative, 'ls'],
            'ls-dr10-south-model': ['Legacy Surveys DR10-south models',
                              [def_url],  maxnative, 'ls'],
	    'ls-dr10-model': ['Legacy Surveys DR10 models', [def_url], maxnative, 'ls'],
            'ls-dr10-south-resid': ['Legacy Surveys DR10-south residuals',
                              [def_url],  maxnative, 'ls'],
	    'ls-dr10-resid': ['Legacy Surveys DR10 residuals', [def_url], maxnative, 'ls'],
        }
        # Add regular and "-grz" versions of the above layers.
        for k,v in dr10layers.items():
            tile_layers[k] = v
            grz = v.copy()
            grz[0] += ' (grz)'
            tile_layers[k + '-grz'] = grz

    if settings.ENABLE_DR9 or settings.ENABLE_DR10:
        tile_layers.update({
            'ls-dr9-north': ['Legacy Surveys DR9-north images',
                             [[0, 14, 'https://s3.us-west-2.amazonaws.com/dr9-north.legacysurvey.org/{z}/{x}/{y}.jpg', []],
                              def_url], maxnative, 'ls'],
            'ls-dr9-north-model': ['Legacy Surveys DR9-north models', [def_url], maxnative, 'ls'],
            'ls-dr9-north-resid': ['Legacy Surveys DR9-north residuals', [def_url], maxnative, 'ls'],
        })

    if settings.ENABLE_DR9:
        tile_layers.update({
            'ls-dr9': ['Legacy Surveys DR9 images', [def_url], maxnative, 'ls'],
            'ls-dr9-south': ['Legacy Surveys DR9-south images',
                             [[0, 14, 'https://s3.us-west-2.amazonaws.com/dr9-south.legacysurvey.org/{z}/{x}/{y}.jpg', []],
                              def_url], maxnative, 'ls'],
            'ls-dr9-south-model': ['Legacy Surveys DR9-south models', [def_url], maxnative, 'ls'],
            'ls-dr9-south-resid': ['Legacy Surveys DR9-south residuals', [def_url], maxnative, 'ls'],
            'ls-dr9.1.1': ['Legacy Surveys DR9.1.1 COSMOS deep images', [def_url], maxZoom, 'ls'],
            'ls-dr9.1.1-model': ['Legacy Surveys DR9.1.1 COSMOS deep models', [def_url],
                                 maxZoom, 'ls'],
            'ls-dr9.1.1-resid': ['Legacy Surveys DR9.1.1 COSMOS deep residuals', [def_url],
                                 maxZoom, 'ls'],
        })

    if settings.ENABLE_DR8:
        tile_layers.update({
            'ls-dr8': ['Legacy Surveys DR8 images', [aws_url, def_url], maxnative, 'ls',
                       {'id':'dr8'}],
            'ls-dr8-north': ['Legacy Surveys DR8-north images', [aws_url, def_url], maxnative, 'ls',
                             {'id':'dr8-north'}],
            'ls-dr8-south': ['Legacy Surveys DR8-south images', [aws_url, def_url], maxnative, 'ls',
                             {'id':'dr8-south'}],
            'ls-dr8-model': ['Legacy Surveys DR8 models', [def_url], maxnative, 'ls'],
            'ls-dr8-north-model': ['Legacy Surveys DR8-north models', [def_url], maxnative, 'ls'],
            'ls-dr8-south-model': ['Legacy Surveys DR8-south models', [def_url], maxnative, 'ls'],
            'ls-dr8-resid': ['Legacy Surveys DR8 residuals', [def_url], maxnative, 'ls'],
            'ls-dr8-north-resid': ['Legacy Surveys DR8-north residuals', [def_url], maxnative, 'ls'],
            'ls-dr8-south-resid': ['Legacy Surveys DR8-south residuals', [def_url], maxnative, 'ls'],
        })

    if settings.ENABLE_DR67 or settings.ENABLE_DR7:
        tile_layers.update({
            'decals-dr7': ['DECaLS DR7 images', [[11, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls'],
        })
    if settings.ENABLE_DR7:
        tile_layers.update({
            'decals-dr7-model': ['DECaLS DR7 models', [[10, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls'],
            'decals-dr7-resid': ['DECaLS DR7 residuals', [[10, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls'],
        })

    if settings.ENABLE_DR6 or settings.ENABLE_DR67:
        tile_layers['mzls+bass-dr6'] = ['MzLS+BASS DR6 images', [[13, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls']

    if settings.ENABLE_DR6:
        tile_layers.update({
            'mzls+bass-dr6-model': ['MzLS+BASS DR6 models', [[13, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls'],
            'mzls+bass-dr6-resid': ['MzLS+BASS DR6 residuals', [[13, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls'],
        })

    if settings.ENABLE_DR67:
        tile_layers['ls-dr67'] = ['Legacy Surveys DR6+DR7 images', [[14, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls']

    if settings.ENABLE_DR5:
        tile_layers.update({
            'decals-dr5': ['DECaLS DR5 images', [[14, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls'],
            'decals-dr5-model': ['DECaLS DR5 models', [[14, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls'],
            'decals-dr5-resid': ['DECaLS DR5 residuals', [[14, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls'],
        })

    if settings.ENABLE_DECAPS1:
        tile_layers.update({
            'decaps': ['DECaPS1 images', [[14, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls'],
            'decaps-model': ['DECaPS1 models', [[14, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls'],
            'decaps-resid': ['DECaPS1 residuals', [[14, maxZoom, tileurl, subs], prod_backstop], maxnative, 'ls'],
        })

    if settings.ENABLE_DECAPS:
        tile_layers.update({
            'decaps2': ['DECaPS2 images', [def_url], maxnative, 'ls'],
            'decaps2-model': ['DECaPS2 models', [def_url], maxnative, 'ls'],
            'decaps2-resid': ['DECaPS2 residuals', [def_url], maxnative, 'ls'],
            'decaps2-riy': ['DECaPS2 images (riY)', [def_url], maxnative, 'ls'],
            'decaps2-model-riy': ['DECaPS2 models (riY)', [def_url], maxnative, 'ls'],
            'decaps2-resid-riy': ['DECaPS2 residuals (riY)', [def_url], maxnative, 'ls'],
        })

    if settings.ENABLE_UNWISE:
        tile_layers.update({
            'unwise-neo4': ['unWISE W1/W2 NEO4', [[6, maxZoom, tileurl, subs], prod_backstop],
                            12, 'unwise'],
            'unwise-neo6': ['unWISE W1/W2 NEO6', [[1, 11, aws_unwise_url, []]], 11, 'unwise'],
            'unwise-neo7': ['unWISE W1/W2 NEO7', [def_url], 11, 'unwise'],
            'unwise-cat-model': ['unWISE Catalog model', [[6, maxZoom, tileurl, subs], prod_backstop],
                                 12, 'unwise'],
        })
    if settings.ENABLE_UNWISE_W3W4:
        tile_layers['unwise-w3w4'] = ['unWISE W3/W4', [def_url], 11, 'unwise']

    if settings.ENABLE_HSC_DR2:
        tile_layers.update({
            'hsc-dr2': ['HSC DR2', [def_url], maxnative, 'hsc'],
            'hsc-dr3': ['HSC DR3', [def_url], maxnative, 'hsc'],
        })

    if settings.ENABLE_VLASS:
        tile_layers.update({
            'vlass1.2': ['VLASS 1.2', [def_url], maxnative, 'vlass'],
        })

    if settings.ENABLE_DES_DR1:
        tile_layers.update({
            'des-dr1': ['DES DR1', [def_url], maxnative, 'des'],
        })

    if settings.ENABLE_PANDAS:
        tile_layers['pandas'] = ['PANDAS', [def_url], maxnative, 'The Pan-Andromeda Archaeological Survey']

    if settings.ENABLE_PS1:
        tile_layers['ps1'] = ['Pan-STARRS1', [[8, maxZoom, tileurl, subs], prod_backstop],
                              maxnative, 'ps1']

    # 2MASS...

    if settings.ENABLE_ZTF:
        tile_layers['ztf'] = ['ZTF', [def_url], 12, 'Zwicky Transient Factory']

    if settings.ENABLE_EBOSS:
        tile_layers['eboss'] = ['special eBOSS region', [def_url], maxnative, 'ls']

    if settings.ENABLE_PHAT:
        tile_layers['phat'] = ['PHAT image', [def_url], maxnative, 'PHAT collaboration']

    if settings.ENABLE_M33:
        tile_layers['m33'] = ['HST M33 image', [[17, maxZoom, tileurl, subs], prod_backstop],
                              maxZoom, 'M33 collaboration']

    if settings.ENABLE_MERIAN:
        tile_layers.update({
            'merian-n540': ['Merian N540', [def_url], maxnative, 'MERIAN collaboration'],
            'merian-n708': ['Merian N708', [def_url], maxnative, 'MERIAN collaboration'],
        })

    # 'cfis_dr3_r': [ ],# [1, maxZoom, tileurl, []], ],
    # 'cfis_dr3_u': [ ],# [1, maxZoom, tileurl, []], ],
    # 'cfis_r': [ ],# [1, maxZoom, tileurl, []], ],
    # 'cfis_u': [ ],# [1, maxZoom, tileurl, []], ],

    test_layers = []
    try:
        from map.test_layers import test_layers as tl
        for la in tl:
            if not la in test_layers:
                test_layers.append(la)

                name,pretty = la
                tile_layers.update({name: [pretty, [def_url], maxnative, '']})

    except:
        import traceback
        traceback.print_exc()

    keys = tile_layers.keys()
    for k in keys:
        over = settings.LAYER_OVERRIDES.get(k)
        if over is None:
            continue
        orig = tile_layers[k]
        urls = over
        orig[1] = urls

    kwkeys = dict(
        tile_layers=tile_layers,
        enable_desi_edr = settings.ENABLE_DESI_EDR,
        #enable_merian = settings.ENABLE_MERIAN,
        science = settings.ENABLE_SCIENCE,
        enable_older = settings.ENABLE_OLDER,
        enable_unwise = settings.ENABLE_UNWISE,
        #enable_vlass = settings.ENABLE_VLASS,
        enable_dev = settings.ENABLE_DEV,
        #enable_m33 = False,
        enable_unwise_w3w4 = settings.ENABLE_UNWISE_W3W4,
        enable_cutouts = settings.ENABLE_CUTOUTS,
        enable_ls_bricks = settings.ENABLE_LS_BRICKS,
        enable_unwise_tiles = settings.ENABLE_UNWISE_TILES,
        enable_sdss_ccds = settings.ENABLE_SDSS_CCDS,
        enable_dr67 = settings.ENABLE_DR67,
        enable_dr5 = settings.ENABLE_DR5,
        enable_dr6 = settings.ENABLE_DR6,
        enable_dr7 = settings.ENABLE_DR7,

        enable_dr8 = settings.ENABLE_DR8,
        enable_dr8_overlays = settings.ENABLE_DR8_OVERLAYS,
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

        enable_dr10 = settings.ENABLE_DR10,
        enable_dr10_overlays = settings.ENABLE_DR10,

        enable_decaps = settings.ENABLE_DECAPS,
        enable_ps1 = settings.ENABLE_PS1,
        #enable_des_dr1 = settings.ENABLE_DES_DR1,
        #enable_ztf = settings.ENABLE_ZTF,
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
        #enable_hsc_dr2 = settings.ENABLE_HSC_DR2,
        enable_desi_targets = settings.ENABLE_DESI_TARGETS,
        enable_desi_data = settings.ENABLE_DESI_DATA,
        enable_desi_footprint = True,
        enable_spectra = settings.ENABLE_SPECTRA,
        enable_phat = settings.ENABLE_PHAT,
        #enable_pandas = settings.ENABLE_PANDAS,
        enable_desi_menu = True,
        maxNativeZoom = settings.MAX_NATIVE_ZOOM,
        discuss_cutout_url=settings.DISCUSS_CUTOUT_URL,
        append_args = '',
    )

    for k in kwargs.keys():
        if not k in kwkeys:
            raise RuntimeError('unknown kwarg "%s" in map._index()' % k)
    for k,v in kwkeys.items():
        if not k in kwargs:
            kwargs[k] = v

    from map.cats import cat_user, cat_desi_tile

    layer = request_layer_name(req, default_layer)

    # Nice spiral galaxy
    #ra, dec, zoom = 244.7, 7.4, 13

    ra, dec = default_radec
    radec_set = False
    zoom = default_zoom

    plate = req.GET.get('plate', None)
    if plate is not None:
        import numpy as np
        T,tree = read_sdss_plates()
        plate = int(plate, 10)
        # (don't use T.cut -- it's from a shared cache)
        i = np.flatnonzero(T.plate == plate)
        if len(i) == 1:
            t = T[i[0]]
            ra,dec = float(t.ra), float(t.dec)
            #zoom = 8
            layer = 'sdss'
            #print('Found plate', plate, 'at RA,Dec', ra,dec, ', setting RA,Dec,zoom,layer')

    # (note, zoom level is actually set by index.html; it's not even passed to index.html)
    # try:
    #     zoom = int(req.GET.get('zoom', zoom))
    # except:
    #     pass
    try:
        ra,dec = parse_radec_strings(req.GET.get('ra'), req.GET.get('dec'))
        radec_set = True
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

    # Process DESI targetid parameter
    try:
        from map.cats import lookup_targetid
        tid = req.GET.get('targetid')
        tid = int(tid)
        print('Looking up TARGETID', tid)
        if settings.ENABLE_DESI_DATA:
            t = lookup_targetid(tid, 'daily')
        else:
            t = lookup_targetid(tid, 'edr')

        if t is not None:
            ra = t.ra
            dec = t.dec
            print('Targetid found: RA,Dec', ra, dec)
            print('(targetid', t.targetid, ')')
        else:
            print('Targetid not found:', tid)
    except:
        pass

    from urllib.parse import unquote
    caturl = unquote(my_reverse(req, 'cat-json-tiled-pattern'))
    smallcaturl = unquote(my_reverse(req, 'cat-json-pattern'))
    cfis_cat_url = smallcaturl

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
        if not radec_set:
            try:
                ra,dec = get_desi_tile_radec(tile, fiberid=fiberid)
                print('Tile RA,Dec', ra,dec)
            except:
                pass

    # if 'targetid' in req.GET:
    #     try:
    #         targetid = int(req.GET['targetid'], 10)
    #         # 22 bits
    #         objid = targetid & 0x3fffff
    #         # 20 bits
    #         brickid = (targetid >> 22) & 0xfffff
    #         # 16 bits
    #         release = (targetid >> 42) & 0xffff
    #         print('Release', release, 'brickid', brickid, 'objid', objid)
    #     except:
    #         pass
        
    galname = None
    if ra is None or dec is None:
        #print('Getting random galaxy position')
        ra,dec,galname = get_random_galaxy(layer=layer)
    
    hostname_url = req.build_absolute_uri('/')

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
                zoom=zoom,
                maxZoom=maxZoom,
                decaps_first=decaps_first,
                merian_first=merian_first,
                galname=galname,
                layer=layer, tileurl=tileurl,
                hostname_url=hostname_url,
                root_url=settings.ROOT_URL+'/'.replace('//','/'),
                uploadurl=uploadurl,
                caturl=caturl, bricksurl=bricksurl,
                smallcaturl=smallcaturl,
                cfis_cat_url=cfis_cat_url,
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

def unions(req):
    if req.user is None or not req.user.is_authenticated:
        return redirect('/login')
    
    return _index(req,
                  default_layer='cfis-dr3-r',
                  #default_radec=(211.389, 54.461),
                  default_radec=(226.4879, 42.2253),
                  default_zoom=14,
                  maxZoom=16,
                  maxNativeZoom = 16,
                  #rooturl=settings.ROOT_URL + '/m33',
                  enable_desi_footprint=False,
                  enable_desi_targets=False,
                  #enable_spectra=False,)
                  )

def desi_edr(req):
    # q = req.META['QUERY_STRING']
    # path = req.get_full_path()
    # print('Path:', path)
    # if '?' in path: #path.endswith('?'):
    #     q += '&'
    # q += 'desi-tiles-edr&desi-spec-edr'
    # 
    # req.GET = req.GET.copy()
    # req.GET['desi-tiles-edr'] = True
    # req.GET['desi-spec-edr'] = True
    # req.META['QUERY_STRING'] = q
    # print('req.get_full_path:', req.get_full_path())
    # print('req.get_full_path_info:', req.get_full_path_info())
    # print('req.get_raw_uri:', req.get_raw_uri())
    return _index(req,
                  default_layer='ls-dr9',
                  default_radec=(191.9530, 57.9458),
                  default_zoom=3,
                  rooturl=settings.ROOT_URL + '/desi-edr',
                  append_args = '&desi-tiles-edr&desi-spec-edr',
    )

def desi_dr1(req):
    return _index(req,
                  default_layer='ls-dr9',
                  default_radec=(0.0, 0.0),
                  default_zoom=5,
                  rooturl=settings.ROOT_URL + '/desi-dr1',
                  append_args = '&desi-tiles-dr1&desi-spec-dr1',
    )

def decaps(req):
    return _index(req,
                  decaps_first=True,
                  enable_decaps=True,
                  enable_dr5_models=False,
                  enable_dr5_resids=False,
                  enable_dr7=False,
                  enable_dr5=False,
                  enable_ps1=False,
                  enable_dr5_overlays=False,
                  enable_dr7_overlays=False,
                  enable_dr8_overlays=False,
                  enable_desi_targets=False,
                  enable_desi_menu=False,
                  enable_spectra=False,
                  enable_older=False,
                  default_layer='decaps2',
                  default_radec=(225.0, -63.2),
                  default_zoom=10,
                  rooturl=settings.ROOT_URL + '/decaps',
    )

def dr5(req):
    return _index(req, enable_decaps=True,
                  enable_ps1=False,
                  enable_desi_targets=False,
                  default_layer='decals-dr5',
                  default_radec=(234.7, 13.6),
                  rooturl=settings.ROOT_URL + '/dr5',
              )

def dr6(req):
    return _index(req, enable_decaps=True,
                  enable_ps1=False,
                  enable_desi_targets=False,
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

    url = 'https://simbad.u-strasbg.fr/simbad/sim-id?output.format=votable&output.params=coo(d)&output.max=1&Ident='
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

    url = 'https://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame/NSV?'
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


    # Check for TARGET or TARGETID <targetid>
    words = obj.strip().split()
    if len(words) == 2 and words[0].lower() in ['target', 'targetid']:
        from map.cats import lookup_targetid
        tid = int(words[1])
        try:
            t = lookup_targetid(tid, 'daily')
            ra = t.ra
            dec = t.dec
        except RuntimeError as e:
            return HttpResponse(json.dumps(dict(error='DESI targetid %i not found' % tid)))
        return HttpResponse(json.dumps(dict(ra=ra, dec=dec, name='DESI Targetid %i' % tid)))

    # Check for RA,Dec in decimal degrees or H:M:S.
    words = obj.strip().split()
    #print('Parsing name query: words', words)
    if len(words) == 2:
        try:
            rastr,decstr = words
            ra,dec = parse_radec_strings(rastr, decstr)
            #print('Parsed as:', ra,dec)
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

html_tag = '''<html xmlns="https://www.w3.org/1999/xhtml" xml:lang="en">
<head>
<link rel="icon" type="image/png" href="%s/favicon.png" />
<link rel="shortcut icon" href="%s/favicon.ico" />
''' % (settings.STATIC_URL, settings.STATIC_URL)

def data_for_radec(req):
    ra  = float(req.GET['ra'])
    dec = float(req.GET['dec'])
    layername = request_layer_name(req)
    layer = get_layer(layername)
    #print('data_for_radec: layer', layer)
    return layer.data_for_radec(req, ra, dec)

class NoOverlapError(RuntimeError):
    pass

class RenderAccumulator(object):
    pass

class RenderAccumulatorImage(RenderAccumulator):
    def __init__(self, W, H):
        import numpy as np
        self.rimg = np.zeros((H,W), np.float32)
        self.rw   = np.zeros((H,W), np.float32)

    def peek(self):
        import numpy as np
        return self.rimg / np.maximum(self.rw, 1e-18)

    def peek_weight(self):
        return self.rw

    def finish(self):
        import numpy as np
        return self.rimg / np.maximum(self.rw, 1e-18)

    def accumulate(self, Yo, Xo, Yi, Xi, resamp, wt, img):
        self.rimg[Yo,Xo] += resamp * wt
        self.rw  [Yo,Xo] += wt

class RenderAccumulatorMask(RenderAccumulator):
    def __init__(self, W, H):
        import numpy as np
        self.rmask = np.zeros((H,W), np.int32)
        self.rw    = np.zeros((H,W), bool)

    def peek(self):
        return self.rmask

    def peek_weight(self):
        return self.rw

    def finish(self):
        return self.rmask

    def accumulate(self, Yo, Xo, Yi, Xi, resamp, wt, img):
        self.rmask[Yo,Xo] = img[Yi, Xi]
        self.rw   [Yo,Xo] = True

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

    def get_exposure_url(self, req, ccdlayername, expnum, ccdname,
                         ccd, mydomain, ra, dec, size, imgtype):
        url = my_reverse(req, 'exposure_panels', args=('LAYER', '12345', 'EXTNAME'))
        url = (url.replace('LAYER', '%(layer)s')
               .replace('12345', '%(expnum)i')
               .replace('EXTNAME', '%(ccdname)s'))
        url = req.build_absolute_uri(url)
        if mydomain is not None:
            url = url.replace('://www.', '://%(domain)s.')

        url +=  '?ra=%(ra).4f&dec=%(dec).4f&size=%(size)i&kind=%(imgtype)s'

        theurl = url % dict(layer=ccdlayername, expnum=expnum, ccdname=ccdname, domain=mydomain,
                            ra=ra, dec=dec, size=size, imgtype=imgtype)
        return theurl

    def get_exposure_contents(self, req, ccdlayername, expnum, ccdname,
                              ccd, mydomain, ra, dec, size):
        contents = ['<img src="%s" width="%i" height="%i" />' % (
            self.get_exposure_url(req, ccdlayername, int(ccd.expnum), ccd.ccdname.strip(),
                                   ccd, mydomain, ra, dec, size, typ), size, size)
                    for typ in ['image', 'weight', 'weightedimage', 'dq']]
        return contents

    def get_ccd_detail_url(self, req, layername, camera, expnum, ccdname, ccd, x, y, size):
        url = my_reverse(req, 'ccd_detail_xhtml', args=(layername, '%s-%i-%s' % (camera, expnum, ccdname)))
        url += '?rect=%i,%i,%i,%i' % (x-size, y-size, 2*size, 2*size)
        return url

    def has_exposure_tarball(self):
        return True

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
        #debug('Zoom:', zoom, 'x,y', x,y, 'Tile pixel scale:', tilescale, 'Scale:',scale)
        scale = np.clip(scale, 0, self.maxscale)
        #print('Old scale', oldscale, 'scale', scale)
        return scale

    def bricks_touching_aa_wcs(self, wcs, scale=None, oldcode=False):
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
        #print('Bricks within range:', B)
        if (B is None) or oldcode:
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

        #print('Checking', len(B), 'possible bricks')
        for i,brick in enumerate(B):
            bwcs = self.get_scaled_wcs(brick, None, scale)
            bh,bw = bwcs.shape
            # walk the boundary
            xl,xm,xh = 0.5, (bw+1)/2., bw+0.5
            yl,ym,yh = 0.5, (bh+1)/2., bh+0.5
            rr,dd = bwcs.pixelxy2radec([xl, xm, xh, xh, xh, xm, xl, xl, xl],
                                       [yl, yl, yl, ym, yh, yh, yh, ym, yl])
            #print('Brick', brick.brickname, 'shape', bh,bw, 'RA,Dec points:', rr, dd)
            ok,bx,by = wcs.radec2pixelxy(rr, dd)
            bx = bx[ok]
            by = by[ok]
            if len(bx) == 0:
                #print('No "ok" pixel-to-radec-to-pixel points')
                continue
            if debug_ps is not None:
                plt.plot(bx, by, 'r-')

            if polygons_intersect(xy, np.vstack((bx, by)).T):
                if debug_ps is not None:
                    plt.plot(bx, by, '-')
                keep.append(i)

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

    def get_filename(self, brick, band, scale, tempfiles=None, invvar=False, maskbits=False):
        if invvar and not self.has_invvar():
            return None
        if maskbits and not self.has_maskbits():
            return None
        kwa = {}
        if invvar:
            kwa.update(invvar=True)
        if scale == 0:
            return self.get_base_filename(brick, band, **kwa)

        ## HACK -- no invvars for scaled images.
        if invvar:
            return None

        fn = self.get_scaled_filename(brick, band, scale)
        print('Target filename:', fn)
        if os.path.exists(fn):
            return fn
        #print('Creating', fn)
        fn = self.create_scaled_image(brick, band, scale, fn, tempfiles=tempfiles)
        if fn is None:
            return None
        if os.path.exists(fn):
            return fn
        return None

    def has_invvar(self):
        return False

    def has_maskbits(self):
        return False

    def needs_recreating(self, brick, band, scale):
        fn = self.get_filename(brick, band, scale)
        deps = self.get_dependencies(brick, band, scale)
        mytime = os.path.getmtime(fn)
        for dep in deps:
            if os.path.exists(dep) and os.path.getmtime(dep) > mytime:
                return True
        return False
        
    def get_dependencies(self, brick, band, scale):
        if scale == 0:
            return []
        sourcefn = self.get_scaled_filename(brick, band, scale-1)
        return [sourcefn]

    def create_scaled_image(self, brick, band, scale, fn, tempfiles=None):
        from scipy.ndimage.filters import gaussian_filter
        import fitsio
        import tempfile
        import numpy as np

        # Read scale-1 image and scale it
        sourcefn = self.get_filename(brick, band, scale-1)
        if sourcefn is None or not os.path.exists(sourcefn):
            info('create_scaled_image: brick', brick.brickname, 'band', band, 'scale', scale, ': Image source file', sourcefn, 'not found')
            return None
        ro = settings.READ_ONLY_BASEDIR
        if ro:
            info('create_scaled_image: Read-only', brick, band, scale)
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

    # Called by render_into_wcs
    def resample_for_render(self, wcs, subwcs, img, coordtype):
        from astrometry.util.resample import resample_with_wcs
        Yo,Xo,Yi,Xi,[resamp] = resample_with_wcs(wcs, subwcs, [img],
                                                 intType=coordtype)
        return Yo,Xo,Yi,Xi,resamp

    def initialize_accumulator_for_render(self, W, H, band,
                                          invvar=False, maskbits=False):
        if maskbits:
            return RenderAccumulatorMask(W, H)
        return RenderAccumulatorImage(W, H)

    def render_into_wcs(self, wcs, zoom, x, y, bands=None, general_wcs=False,
                        scale=None, tempfiles=None, invvar=False, maskbits=False):
        import numpy as np
        from astrometry.util.resample import resample_with_wcs, OverlapError

        #print('render_into_wcs: wcs', wcs, 'zoom,x,y', zoom,x,y, 'general wcs?', general_wcs)

        if scale is None:
            scale = self.get_scale(zoom, x, y, wcs)

        # FIXME -- no scaled invvars or maskbits
        if scale >= 1 and (invvar or maskbits):
            return None

        if not general_wcs:
            bricks = self.bricks_touching_aa_wcs(wcs, scale=scale)
        else:
            bricks = self.bricks_touching_general_wcs(wcs, scale=scale)

        #print('Render into WCS: bricks', bricks)
            
        if bricks is None or len(bricks) == 0:
            info('No bricks touching WCS')
            return None

        if bands is None:
            bands = self.get_bands()

        if maskbits:
            bands = [bands[0]]

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
            acc = self.initialize_accumulator_for_render(W, H, band, invvar=invvar, maskbits=maskbits)
            bandbricks = self.bricks_for_band(bricks, band)
            for brick in bandbricks:
                brickname = brick.brickname
                info('Reading', brickname, 'band', band, 'scale', scale)
                # call get_filename to possibly generate scaled version
                fn = self.get_filename(brick, band, scale, tempfiles=tempfiles, invvar=invvar,
                                       maskbits=maskbits)
                info('Reading', brickname, 'band', band, 'scale', scale, ('invvar' if invvar else ''), ('maskbits' if maskbits else ''), '-> fn', fn)
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
                xx = xx.astype(np.int32)
                yy = yy.astype(np.int32)

                #print('Brick', brickname, 'band', band, 'shape', bwcs.shape, 'pixel coords', xx, yy)

                imW,imH = int(bwcs.get_width()), int(bwcs.get_height())
                M = 10
                xlo = np.clip(xx.min() - M, 0, imW)
                xhi = np.clip(xx.max() + M, 0, imW)
                ylo = np.clip(yy.min() - M, 0, imH)
                yhi = np.clip(yy.max() + M, 0, imH)
                #print('-- x range', xlo,xhi, 'y range', ylo,yhi)
                if xlo >= xhi or ylo >= yhi:
                    info('No pixel overlap')
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
                    rr,dd = wcs.pixelxy2radec(np.hstack((xx1,xx2,xx3,xx4)), np.hstack((yy1,yy2,yy3,yy4)))[:2]
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
                    Yo,Xo,Yi,Xi,resamp = self.resample_for_render(wcs, subwcs, img, coordtype)
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
                    if resamp is not None:
                        resamp = resamp[I]

                    #print('get_brick_mask:', len(Yo), 'pixels')

                # print('xlo xhi', xlo,xhi, 'ylo yhi', ylo,yhi,
                #       'image shape', img.shape,
                #       'Xi range', Xi.min(), Xi.max(),
                #       'Yi range', Yi.min(), Yi.max(),
                #       'subwcs shape', subwcs.shape)

                #if not np.all(np.isfinite(img[Yi,Xi])):
                if resamp is not None:
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
                    if resamp is not None:
                        resamp = resamp[ok]

                wt = self.get_pixel_weights(band, brick, scale)

                acc.accumulate(Yo, Xo, Yi, Xi, resamp, wt, img)
                #print('Coadded', len(Yo), 'pixels;', (nz-np.sum(rw==0)), 'new')

                if debug_ps is not None:
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
                               vmin=-0.001, vmax=0.1)
                    plt.title('dest')

                    plt.subplot(2,3,3)
                    rimg = acc.peek()
                    rw = acc.peek_weight()
                    plt.imshow(rimg,
                               interpolation='nearest', origin='lower',
                               vmin=-0.001, vmax=0.1)
                    plt.title('rimg')
                    plt.subplot(2,3,6)
                    plt.imshow(rw, interpolation='nearest', origin='lower')
                    plt.title('rw')
                    #plt.savefig('render-%s-%s.png' % (brickname, band))
                    debug_ps.savefig()
            rimg = acc.finish()
            rimgs.append(rimg)
        return rimgs

    def get_brick_mask(self, scale, bwcs, brick):
        return None

    def filter_pixels(self, scale, img, wcs, sub_brick_wcs, Yo,Xo,Yi,Xi):
        return None

    def get_pixel_weights(self, band, brick, scale, **kwargs):
        return 1.

    def _check_tile_args(self, req, ver, zoom, x, y):
        from map.views import tileversions
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
        return ver,zoom,x,y

    def render_rgb(self, wcs, zoom, x, y, bands=None, tempfiles=None, get_images_only=False,
                   invvar=False, maskbits=False):
        rimgs = self.render_into_wcs(wcs, zoom, x, y, bands=bands, tempfiles=tempfiles,
                                     invvar=invvar, maskbits=maskbits)
        if get_images_only:
            return rimgs,None
        if bands is None:
            bands = self.get_bands()
        if rimgs is None:
            rgb = None
        else:
            rgb = self.get_rgb(rimgs, bands)
        return rimgs, rgb

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
        if savecache is None:
            savecache = settings.SAVE_CACHE

        ver,zoom,x,y = self._check_tile_args(req, ver, zoom, x, y)

        if (not get_images) and (wcs is None):
            tilefn = self.get_tile_filename(ver, zoom, x, y)
            info('Tile image filename:', tilefn, 'exists?', os.path.exists(tilefn))
            if os.path.exists(tilefn) and not ignoreCached:
                info('Sending tile', tilefn)
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

        rimgs, rgb = self.render_rgb(wcs, zoom, x, y, bands=bands, tempfiles=tempfiles,
                                     get_images_only=(get_images and not write_jpeg))

        if rimgs is None:
            if get_images:
                return None
            if return_if_not_found and not forcecache:
                return None
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(settings.STATIC_URL + 'blank.jpg')
    
        if get_images and not write_jpeg:
            return rimgs

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
            render_sga_ellipse(tilefn, tilefn, wcs, req.GET)

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
        # (actually only used when getting cutouts, so far)
        # default: assume single-character band names
        mybands = self.get_available_bands()
        bb = []
        for b in bands:
            if b in mybands:
                bb.append(b)
            else:
                return None
        return bb

    def get_available_bands(self):
        return self.get_bands()

    def write_cutout(self, ra, dec, pixscale, width, height, out_fn,
                     bands=None,
                     fits=False, jpeg=False,
                     subimage=False,
                     with_image=True,
                     with_invvar=False,
                     with_maskbits=False,
                     tempfiles=None,
                     get_images=False,
                     req=None):
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

            brickrad = 0.2 + max(width, height) * self.pixscale / 3600.
            I,J,d = match_radec(ra, dec, bricks.ra, bricks.dec, brickrad)
            if len(I) == 0:
                raise RuntimeError('no overlap')
            scale = 0
            fitsio.write(out_fn, None, header=hdr, clobber=True)
            for brick in bricks[J]:
                info('Cutting out RA,Dec', ra,dec, 'in brick', brick.brickname)
                for band in bands:
                    fn = self.get_filename(brick, band, scale)
                    info('Image filename', fn)
                    wcs = self.read_wcs(brick, band, scale, fn=fn)
                    if wcs is None:
                        continue
                    ok,xx,yy = wcs.radec2pixelxy(ra, dec)
                    #print('x,y', xx,yy)
                    H,W = wcs.shape
                    xx = int(np.round(xx - width/2)) - 1
                    yy = int(np.round(yy - height/2)) - 1
                    x0 = np.clip(xx, 0, W-1)
                    x1 = np.clip(xx + width - 1, 0, W-1)
                    y0 = np.clip(yy, 0, H-1)
                    y1 = np.clip(yy + height - 1, 0, H-1)
                    #print('X', x0, x1, 'Y', y0, y1)
                    if x0 == x1 or y0 == y1:
                        debug('No overlap')
                        continue
                    slc = (slice(y0, y1+1), slice(x0, x1+1))
                    subwcs = wcs.get_subimage(x0, y0, 1+x1-x0, 1+y1-y0)
                    try:
                        img = self.read_image(brick, band, 0, slc, fn=fn)
                    except Exception as e:
                        print('Failed to read image:', e)
                        continue
                    hdr = fitsio.FITSHDR()
                    self.populate_fits_cutout_header(hdr)
                    hdr['BRICK'] = brick.brickname
                    hdr['BRICK_X0'] = x0
                    hdr['BRICK_Y0'] = y0
                    hdr['BAND'] = band
                    hdr['IMAGETYP'] = 'image'
                    subwcs.add_to_header(hdr)
                    # Append image to FITS file
                    fitsio.write(out_fn, img, header=hdr)
                    if self.has_invvar():
                        # Add invvar
                        ivfn = self.get_base_filename(brick, band, invvar=True)
                        iv = self.read_image(brick, band, 0, slc, fn=ivfn)
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

        #print('Cutout: bands', bands)
        if jpeg:
            ims,rgb = self.render_rgb(wcs, zoom, xtile, ytile, bands=bands, tempfiles=tempfiles)
            self.write_jpeg(out_fn, rgb)
            if req is not None:
                if 'sga' in req.GET or 'sga-parent' in req.GET:
                    render_sga_ellipse(out_fn, out_fn, wcs, req.GET)
            return

        #print('write_cutouts: with_image', with_image, 'with_invvar', with_invvar,
        #      'has_invvar', self.has_invvar(), 'get_images:', get_images)
        ims = None
        if with_image:
            #ims = self.render_into_wcs(wcs, zoom, xtile, ytile, bands=bands, tempfiles=tempfiles)
            ims,_ = self.render_rgb(wcs, zoom, xtile, ytile, bands=bands, tempfiles=tempfiles,
                                    get_images_only=True)
            if ims is None:
                raise NoOverlapError('No overlap')
        ivs = None
        if with_invvar and self.has_invvar():
            ivs,_ = self.render_rgb(wcs, zoom, xtile, ytile, bands=bands, tempfiles=tempfiles,
                                    get_images_only=True, invvar=True)
        maskbits = None
        if with_maskbits and self.has_maskbits():
            maskbits,_ = self.render_rgb(wcs, zoom, xtile, ytile, bands=bands, tempfiles=tempfiles,
                                         get_images_only=True, maskbits=True)

        if hdr is not None:
            hdr['BANDS'] = ''.join([str(b) for b in bands])
            for i,b in enumerate(bands):
                hdr['BAND%i' % i] = b
            wcs.add_to_header(hdr)

            # convert IMAGEW, IMAGEH from floats to ints.  Recent astrometry.net does this already
            hdr['IMAGEW'] = int(hdr['IMAGEW'])
            hdr['IMAGEH'] = int(hdr['IMAGEH'])

        if get_images:
            if with_invvar:
                return ims,ivs,hdr
            return ims,hdr

        clobber=True
        if with_image:
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
    
            hdr['IMAGETYP'] = 'IMAGE'
            kw = self.get_fits_cutout_kwargs(image=True)
            fitsio.write(out_fn, cube, clobber=clobber, header=hdr, **kw)
            clobber = False

        if ivs is not None:
            if len(bands) > 1:
                for i,im in enumerate(ivs):
                    cube[i,:,:] = im
            else:
                cube = ivs[0]
            del ivs
            hdr['IMAGETYP'] = 'INVVAR'
            kw = self.get_fits_cutout_kwargs(iv=True)
            fitsio.write(out_fn, cube, clobber=clobber, header=hdr, **kw)
            clobber = False

        if maskbits is not None:
            cube = maskbits[0]
            info('Writing maskbits HDU')
            hdr['IMAGETYP'] = 'MASKBITS'
            kw = self.get_fits_cutout_kwargs(maskbits=True)
            fitsio.write(out_fn, cube, clobber=clobber, header=hdr, **kw)
            clobber = False

    def get_fits_cutout_kwargs(self, image=False, iv=False, maskbits=False):
        return {}

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
            #print('Request has zoom=', zoom, ': setting pixscale=', pixscale)

        if bands is not None:
            bands = self.parse_bands(bands)
        if bands is None:
            bands = self.get_bands()

        subimage = ('subimage' in req.GET)

        with_invvar = ('invvar' in req.GET)

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
                          fits=fits, jpeg=jpeg, subimage=subimage, tempfiles=tempfiles,
                          with_invvar=with_invvar, req=req)

        return send_file(out_fn, filetype, unlink=True, filename=nice_fn)

    # Note, see cutouts.py : jpeg_cutout, which calls get_cutout directly!
    def get_jpeg_cutout_view(self):
        def view(request, ver, zoom, x, y):
            tempfiles = []
            rtn = self.get_cutout(request, jpeg=True, tempfiles=tempfiles)
            for fn in tempfiles:
                #print('Deleting temp file', fn)
                os.unlink(fn)
            return rtn
        return view

    def get_fits_cutout_view(self):
        def view(request, ver, zoom, x, y):
            tempfiles = []
            rtn = self.get_cutout(request, fits=True, tempfiles=tempfiles)
            for fn in tempfiles:
                #print('Deleting temp file', fn)
                os.unlink(fn)
            return rtn
        return view

def render_sga_ellipse(infn, outfn, wcs, request):
    from PIL import Image, ImageDraw
    import numpy as np
    img = Image.open(infn)

    ra, dec = wcs.radec_center()
    img_cx = img.size[0] / 2
    img_cy = img.size[1] / 2
    pixscale = wcs.pixel_scale()

    ralo = ra - (img_cx * pixscale / 3600 / np.cos(np.deg2rad(dec)))
    rahi = ra + (img_cx * pixscale / 3600 / np.cos(np.deg2rad(dec)))
    declo = dec - (img_cy * pixscale / 3600)
    dechi = dec + (img_cy * pixscale / 3600)

    from map.cats import query_sga_radecbox
    galaxies = None
    # if request.get('lslga', None) == '':
    #     lslgacolor_default = '#3388ff'
    #     galaxies = query_lslga_radecbox(ralo, rahi, declo, dechi)
    # elif request.get('lslga-model', None) == '':
    #     lslgacolor_default = '#ffaa33'
    #     galaxies = query_lslga_model_radecbox(ralo, rahi, declo, dechi)
    if request.get('sga', None) == '':
        lslgacolor_default = '#3388ff'
        #fn = os.path.join(settings.DATA_DIR, 'sga', 'SGA-ellipse-v3.0.kd.fits')
        fn = os.path.join(settings.DATA_DIR, 'sga', 'SGA-2020.kd.fits')
        galaxies = query_sga_radecbox(fn, ralo, rahi, declo, dechi)
    elif request.get('sga-parent', None) == '':
        lslgacolor_default = '#ffaa33'
        fn = os.path.join(settings.DATA_DIR, 'sga', 'SGA-parent-v3.0.kd.fits')
        galaxies = query_sga_radecbox(fn, ralo, rahi, declo, dechi)
    else:
        galaxies, lslgacolor_default = None, None

    for r in galaxies if galaxies is not None else []:

        RA, DEC = r.ra, r.dec
        if (request.get('lslga', None) == '' or
            request.get('sga', None) == '' or
            request.get('sga-parent', None) == ''):
            RAD = r.radius_arcsec
            AB = r.ba
            PA = r.pa
        elif request.get('lslga-model', None) == '':
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
        ellipse_color = '#' + request.get('sgacolor', lslgacolor_default).lstrip('#')
        ellipse_width = int(np.round(float(request.get('sgawidth', 3)), 0))
        draw.ellipse(box_corners, fill=None, outline=ellipse_color, width=ellipse_width)

        rotated = overlay.rotate(PA, expand=True)
        rotated_width, rotated_height = rotated.size

        ok, ellipse_x, ellipse_y = wcs.radec2pixelxy(RA, DEC)

        if ok:
            paste_shift_x = int(ellipse_x - rotated_width / 2)
            paste_shift_y = int(ellipse_y - rotated_height / 2)
            img.paste(rotated, (paste_shift_x, paste_shift_y), rotated)

    img.save(outfn)

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
        self.have_ccd_data = True

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
        if bb is not None:
            html.extend(self.data_for_radec_box_html(req, *bb))
            html.extend(self.cutouts_html(req, ra, dec))

        brick_html = self.brick_details_body(brick)
        html.extend(brick_html)

        ccds = self.get_ccds_for_brick(survey, brick)
        if ccds is not None:
            if len(ccds):
                html.extend(self.ccds_overlapping_html(req, ccds, brick=brickname, ra=ra, dec=dec))
            from legacypipe.survey import wcs_for_brick
            brickwcs = wcs_for_brick(brick)
            ok,bx,by = brickwcs.radec2pixelxy(ra, dec)
            info('Brick x,y:', bx,by)
            ccds.cut((bx >= ccds.brick_x0) * (bx <= ccds.brick_x1) *
                     (by >= ccds.brick_y0) * (by <= ccds.brick_y1))
            info('Cut to', len(ccds), 'CCDs containing RA,Dec point')
            if len(ccds):
                html.extend(self.ccds_overlapping_html(req, ccds, ra=ra, dec=dec))

        html.extend(['</body></html>',])
        return HttpResponse('\n'.join(html))

    def get_ccds_for_brick(self, survey, brick):
        ccdsfn = survey.find_file('ccds-table', brick=brick.brickname)
        if not os.path.exists(ccdsfn):
            return None
        from astrometry.util.fits import fits_table
        ccds = fits_table(ccdsfn)
        ccds = touchup_ccds(ccds, survey)
        return ccds

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

    def data_for_radec_box_html(self, req, ralo,rahi,declo,dechi):
        caturl = (my_reverse(req, 'cat-fits', args=(self.name,)) +
                  '?ralo=%f&rahi=%f&declo=%f&dechi=%f' % (ralo, rahi, declo, dechi))
        return ['<h1>%s Data for RA,Dec box:</h1>' % self.survey.drname,
                '<p><a href="%s">Catalog</a></p>' % caturl]

    def cutouts_html(self, req, ra, dec):
        qargs = '?ra=%.4f&dec=%.4f&layer=%s' % (ra, dec, self.name)
        cutout_jpg = my_reverse(req, 'cutout-jpeg') + qargs
        cutout_fits = my_reverse(req, 'cutout-fits') + qargs
        cutout_subimage = my_reverse(req, 'cutout-fits') + qargs + '&subimage'
        copsf = my_reverse(req, 'coadd_psf') + qargs

        html = ['<h1>%s Cutouts at RA,Dec:</h1>' % self.survey.drname,
                '<ul>'
                '<li><a href="%s">Image (JPG)</a></li>' % cutout_jpg,
                '<li><a href="%s">Image (FITS)</a></li>' % cutout_fits,
                '<li><a href="%s">Image (FITS; not resampled; including inverse-variance map)</a></li>' % cutout_subimage,
                '<li><a href="%s">Coadd PSF (FITS)</a></li>' % copsf,
                '</ul>'
                ]
        return html

    def ccds_overlapping_html(self, req, ccds, ra=None, dec=None, brick=None):
        if brick is not None:
            html = ['<h1>CCDs overlapping brick:</h1>']
        elif ra is not None and dec is not None:
            html = ['<h1>CCDs overlapping RA,Dec:</h1>']
        html.extend(ccds_overlapping_html(req, ccds, self.name, ra=ra, dec=dec,
                                          ccd_link=self.have_ccd_data))
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
        info(len(ccds), 'CCDs from survey')
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
                info('Does not exist:', catfn)
                continue
            debug('Reading catalog', catfn)
            T = fits_table(catfn)
            T.cut(T.brick_primary)
            info('File', catfn, 'cut to', len(T), 'primary')
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

    def get_base_filename(self, brick, band, invvar=False, maskbits=False, **kwargs):
        brickname = brick.brickname
        if invvar:
            return self.survey.find_file('invvar', brick=brickname, band=band)
        if maskbits:
            return self.survey.find_file('maskbits', brick=brickname)
        return self.survey.find_file(self.imagetype, brick=brickname, band=band)

    def has_invvar(self):
        return True

    def has_maskbits(self):
        return True

    def get_rgb(self, imgs, bands, **kwargs):
        # IGNORES KWARGS!!
        return dr2_rgb(imgs, bands, **self.rgbkwargs)
        #kw = self.rgbkwargs.copy()
        #kw.update(kwargs)
        #return dr2_rgb(imgs, bands, **kw)

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

    def get_dependencies(self, brick, band, scale):
        if scale == 0:
            return []
        finalwcs = self.get_scaled_wcs(brick, band, scale)
        bricks = self.bricks_touching_aa_wcs(finalwcs, scale-1)
        fns = []
        for b in brick:
            fns.append(self.get_scaled_filename(b, band, scale-1))
        return fns
    
    def create_scaled_image(self, brick, band, scale, fn, tempfiles=None):
        import numpy as np
        from scipy.ndimage.filters import gaussian_filter
        import fitsio
        import tempfile

        ro = settings.READ_ONLY_BASEDIR
        if ro:
            print('Read-only; not creating scaled', brick.brickname, band, scale, 'fn', fn)
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
        info('Wrote', fn)
        return fn

    def get_filename(self, brick, band, scale, tempfiles=None, invvar=False, maskbits=False):
        #print('RebrickedMixin.get_filename: brick', brick, 'band', band, 'scale', scale)
        if scale == 0:
            #return self.get_base_filename(brick, band)
            return super(RebrickedMixin, self).get_filename(brick, band, scale,
                                                            tempfiles=tempfiles, invvar=invvar,
                                                            maskbits=maskbits)
        if invvar:
            return None

        fn = self.get_scaled_filename(brick, band, scale)
        if os.path.exists(fn):
            print('Target filename (rebricked) exists:', fn)
            return fn
        print('Creating target filename (rebricked):', fn)
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

            # Check for actual RA,Dec box overlap
            # handle RA wrap: if ra1 (near 360) > ra2 (near 0), bring ra1 negative
            ra1 = bsmall.ra1[I]
            ra2 = bsmall.ra2[I]
            ra1 -= (360. * (ra1 > ra2))
            ara1 = allbricks.ra1[ia]
            ara2 = allbricks.ra2[ia]
            ara1 -= (360. * (ara1 > ara2))
            overlap = ((bsmall.dec2[I] >= allbricks.dec1[ia]) *
                       (bsmall.dec1[I] <= allbricks.dec2[ia]) *
                       (ra2 >= ara1) *
                       (ra1 <= ara2))
            if haves:
                Igood = np.array(I)[overlap]
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
                good = np.any(overlap)
                if good:
                    keep.append(ia)
        keep = np.array(keep)
        allbricks.cut(keep)
        info('Cut generic bricks to', len(allbricks))
        allbricks.writeto(fn)
        info('Wrote', fn)
        return allbricks

        # tmpfn = fn.replace('.gz','')
        # assert(tmpfn != fn)
        # allbricks.writeto(tmpfn)
        # kdfn = os.path.join(self.basedir, 'survey-bricks-%i.kd.fits' % scale)
        # cmd = 'startree -i %s -o %s -PTk' % (tmpfn, kdfn)
        # os.system(cmd)
        # os.remove(tmpfn)
        # return allbricks

    def get_brick_size_for_scale(self, scale):
        if scale is None:
            scale = 0
        if scale == 0:
            try:
                bs = self.survey.bricksize
            except:
                bs = 0.25
            return bs * 2**scale
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

    def bricks_within_range(self, ra, dec, radius, scale=None):
        from astrometry.libkd.spherematch import match_radec
        import numpy as np
        #print('bricks_within_range for scale', scale)
        B = self.get_bricks_for_scale(scale)
        #brad = self.pixelsize * self.pixscale/3600. * 2**scale * np.sqrt(2.)/2. * 1.01
        brad = self.get_brick_size_for_scale(scale) * np.sqrt(2.) / 2. * 1.1
        I,J,d = match_radec(ra, dec, B.ra, B.dec, radius + brad)
        J = np.sort(J)
        return B[J]
        
class DecapsLayer(DecalsLayer):

    def has_invvar(self):
        return False

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
        fn = super().get_scaled_filename(brick, band, scale)
        if not os.path.exists(fn) and os.path.exists(fn + '.fz'):
            return fn + '.fz'
        return fn

    def get_fits_extension(self, scale, fn):
        if fn.endswith('.fz'):
            return 1
        return super().get_fits_extension(scale, fn)
    
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
            return HttpResponseRedirect('https://' + host + '/viewer' + req.path)
        return super().get_tile(req, ver, zoom, x, y, **kwargs)

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

    def get_filename(self, brick, band, scale, tempfiles=None, invvar=False, maskbits=False):
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
        debug('Getting unique-area mask for brick', brick.brickname)
        return U

class DecalsResidLayer(ResidMixin, UniqueBrickMixin, DecalsLayer):
    pass

class DecalsModelLayer(UniqueBrickMixin, DecalsLayer):
    pass

class DecapsResidLayer(ResidMixin, DecapsLayer):
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

    #def has_cutouts(self):
    #    return True

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

    def get_filename(self, brick, band, scale, tempfiles=None, invvar=False, maskbits=False):
        brickname = brick.brickname
        brickpre = brickname[:3]
        fn = os.path.join(self.basedir, 'coadd', brickpre,
                          'sdssco-%s-%s.fits.fz' % (brickname, band))
        info('SdssLayer.get_filename: brick', brickname, 'band', band, 'scale', scale, 'fn', fn)
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
        if scale is None:
            scale = 0
        size = self.get_pixel_size_for_scale(scale)
        pixscale = self.pixscale * 2**scale
        cd = pixscale / 3600.
        crpix = size/2. + 0.5
        wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                  float(size), float(size))
        return wcs

    def get_pixel_size_for_scale(self, scale):
        # Work around issue where the largest-scale bricks don't quite
        # meet up due to TAN projection effects.
        if scale >= 6:
            size = 3800
        else:
            size = 3600
        return size

class LsDr10Layer(ReDecalsLayer):
    def get_rgb(self, imgs, bands, **kwargs):
        #print('LsDr10Layer.get_rgb: self.bands', self.bands)

        if self.bands == 'grz':
            return super().get_rgb(imgs, bands, **kwargs)
        if self.bands == 'gri':
            #print('LS DR10 gri')
            rgb_stretch_factor = 1.5
            rgbscales = {
                 'g': (2, 6.0 * rgb_stretch_factor),
                 'r': (1, 3.4 * rgb_stretch_factor),
                 'i': (0, 3.0 * rgb_stretch_factor),}
            kwargs.update(scales=rgbscales)
            return sdss_rgb(imgs, bands, **kwargs)

        import numpy as np
        m=0.03
        Q=20
        mnmx=None
        clip=True
        allbands = ['g','r','i','z']
        rgb_stretch_factor = 1.5
        rgbscales=dict(
            g =    (2, 6.0 * rgb_stretch_factor),
            r =    (1, 3.4 * rgb_stretch_factor),
            i =    (0, 3.0 * rgb_stretch_factor),
            z =    (0, 2.2 * rgb_stretch_factor),
            )
        I = 0
        for img,band in zip(imgs, bands):
            plane,scale = rgbscales[band]
            img = np.maximum(0, img * scale + m)
            I = I + img
        I /= len(bands)
        if Q is not None:
            fI = np.arcsinh(Q * I) / np.sqrt(Q)
            I += (I == 0.) * 1e-6
            I = fI / I
        H,W = I.shape
        rgb = np.zeros((H,W,3), np.float32)

        rgbvec = dict(
            g = (0.,   0.,  0.75),
            r = (0.,   0.5, 0.25),
            i = (0.25, 0.5, 0.),
            z = (0.75, 0.,  0.))

        for img,band in zip(imgs, bands):
            _,scale = rgbscales[band]
            rf,gf,bf = rgbvec[band]
            if mnmx is None:
                v = (img * scale + m) * I
            else:
                mn,mx = mnmx
                v = ((img * scale + m) - mn) / (mx - mn)
            if clip:
                v = np.clip(v, 0, 1)
            if rf != 0.:
                rgb[:,:,0] += rf*v
            if gf != 0.:
                rgb[:,:,1] += gf*v
            if bf != 0.:
                rgb[:,:,2] += bf*v
        return rgb

    def get_ccds_for_brick(self, survey, brick):
        from astrometry.util.fits import fits_table
        ccdsfn = survey.find_file('ccds-table', brick=brick.brickname)
        ccds = fits_table(ccdsfn)
        ccds = touchup_ccds(ccds, survey)
        return ccds

class LsDr10ModelLayer(UniqueBrickMixin, LsDr10Layer):
    pass
class LsDr10ResidLayer(UniqueBrickMixin, ResidMixin, LsDr10Layer):
    pass

    
class ReDecalsResidLayer(UniqueBrickMixin, ResidMixin, ReDecalsLayer):
    pass

class ReDecalsModelLayer(UniqueBrickMixin, ReDecalsLayer):
    pass

def plot_boundary_map(X, rgb=(0,255,0), extent=None, iterations=1):
    from scipy.ndimage import binary_dilation
    import numpy as np
    H,W = X.shape
    it = iterations
    padded = np.zeros((H+2*it, W+2*it), bool)
    padded[it:-it, it:-it] = X.astype(bool)
    bounds = np.logical_xor(binary_dilation(padded), padded)
    if extent is None:
        extent = [-it, W+it, -it, H+it]
    else:
        x0,x1,y0,y1 = extent
        extent = [x0-it, x1+it, y0-it, y1+it]
    plot_mask(bounds, rgb=rgb, extent=extent)

def plot_mask(X, rgb=(0,255,0), extent=None):
    import pylab as plt
    import numpy as np
    H,W = X.shape
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[:,:,0] = X*rgb[0]
    rgba[:,:,1] = X*rgb[1]
    rgba[:,:,2] = X*rgb[2]
    rgba[:,:,3] = X*255
    plt.imshow(rgba, interpolation='nearest', origin='lower', extent=extent)

class LsSegmentationLayer(RebrickedMixin, MapLayer):
    def __init__(self, ls_layer):
        super().__init__(ls_layer.name + '-segmentation')
        self.ls_layer = ls_layer
        self.pixscale = ls_layer.pixscale
        self.nativescale = ls_layer.nativescale

    # Only works for scale=0
    def get_bricks_for_scale(self, scale):
        if scale in [0, None]:
            return self.ls_layer.get_bricks_for_scale(scale)
        return None

    # One mask file per brick
    def get_bands(self):
        return 'r'

    def get_fits_cutout_kwargs(self, image=False, iv=False, maskbits=False):
        return dict(compress='GZIP')

    def render_rgb(self, wcs, zoom, x, y, bands=None, get_images_only=False,
                   **kwargs):
        import numpy as np
        from scipy.ndimage import gaussian_filter
        from scipy.ndimage import label
        from collections import Counter

        imgs,_ = self.ls_layer.render_rgb(wcs, zoom, x, y, bands=bands, get_images_only=True,
                                          **kwargs)
        kwargs.update(invvar=True)
        ivs,_ = self.ls_layer.render_rgb(wcs, zoom, x, y, bands=bands, get_images_only=True,
                                          **kwargs)
        cat,hdr = self.ls_layer.get_catalog_in_wcs(wcs)
        #print('Got', len(cat), 'catalog objects in WCS')
        #cat.about()
        #print('Cat types:', Counter(cat.type))

        if len(cat) > 0:
            pixscale = wcs.pixel_scale()
            fwhmpix = cat.psfsize_r[0] / pixscale
            #print('PSF size:', cat.psfsize_r)
            #print('WCS pixscale:', pixscale)
            sigpix = fwhmpix / 2.35
            #print('Sigma in pixels:', sigpix)
        else:
            sigpix = 1.

        psfnorm = 1. / (2.*np.sqrt(np.pi) * sigpix)
        #print('Constant SB detection level:', 5. * psfnorm, 'sig1')

        ok,x,y = wcs.radec2pixelxy(cat.ra, cat.dec)
        h,w = wcs.shape
        ix = np.clip(np.round(x-1.).astype(int), 0, w-1)
        iy = np.clip(np.round(y-1.).astype(int), 0, h-1)

        img = imgs[0]
        iv = ivs[0]
        H,W = img.shape

        ie = np.sqrt(np.maximum(iv, 0.))
        ie = gaussian_filter(ie, 10)

        plots = False
        if plots:
            import matplotlib as mpl
            cmap = mpl.colormaps['tab20']

        segmap = np.empty((H,W), np.int32)
        segmap[:,:] = -1

        k = 0
        import heapq
        from scipy.ndimage import binary_dilation

        K = np.argsort(-cat.flux_r)
        iy = iy[K]
        ix = ix[K]

        # Watershed by priority-fill.
        # Seed the segmentation map
        segmap[iy, ix] = np.arange(len(iy))

        # values are (-sn, key, x, y, cx, cy)
        q = [(-img[y,x], segmap[y,x], x,y, x,y)
             for x,y in zip(ix, iy)]
        heapq.heapify(q)

        sn = img * ie

        # add in any edge pixels that are peaks
        edgepeaks = np.zeros(segmap.shape, bool)
        edgepeaks[ 0,:] = (sn[ 0,:] >= 5.)
        edgepeaks[-1,:] = (sn[-1,:] >= 5.)
        edgepeaks[:, 0] = (sn[:, 0] >= 5.)
        edgepeaks[:,-1] = (sn[:,-1] >= 5.)

        edgepeaks[:, 1:  ] &= (sn[:, 1:  ] >= sn[:,  :-1])
        edgepeaks[:,  :-1] &= (sn[:,  :-1] >= sn[:, 1:  ])
        edgepeaks[1:  , :] &= (sn[1:  , :] >= sn[ :-1, :])
        edgepeaks[ :-1, :] &= (sn[ :-1, :] >= sn[1:  , :])

        hy,hx = np.nonzero(edgepeaks)
        del edgepeaks
        #print('Adding', len(hy), 'edge pixels that are peaks')
        for x,y,key in zip(hx, hy, len(iy) + np.arange(len(hy))):
            heapq.heappush(q, (-img[y,x], key, x, y, x, y))

        # Pixels to include in the blobs
        blobmask = (sn >= 5.*psfnorm)
        # Grow the blob mask a bit..
        blob_dilate = 2
        blobmask = binary_dilation(blobmask, iterations=blob_dilate)
        # No blobs where the model == 0
        blobmask[(img == 0.0) * (ie > 0)] = False

        # Watershed based on image val * a Gaussian of this stdev in pixels
        R = 5.
        
        j = 0
        jnext = 2
        while len(q):
            j += 1
            if plots and j >= jnext:
                jnext *= 2
                cmap = mpl.colormaps['tab20']
                plt.clf()
                plt.subplot(1,2,1)
                rgb = cmap((segmap + 2) % 20)
                plt.imshow(rgb, origin='lower', interpolation='nearest')

                plt.subplot(1,2,2)
                plt.imshow(img, origin='lower', interpolation='nearest', vmin=0, vmax=10.*psfnorm/np.median(ie.ravel()))
                fn = 'seg-%07i.png' % k
                k += 1
                plt.savefig(fn)
                #print('Wrote', fn)

            _,key,x,y,cx,cy = heapq.heappop(q)
            segmap[y,x] = key
            # 4-connected neighbours
            for x,y in [(x, y-1), (x, y+1), (x-1, y), (x+1, y),]:
                # out of bounds?
                if x<0 or y<0 or x==W or y==H:
                    continue
                # not in blobmask?
                if not blobmask[y,x]:
                    continue
                # already queued or segmented?
                if segmap[y,x] != -1:
                    continue
                # mark as queued
                segmap[y,x] = -2
                # enqueue!
                heapq.heappush(q, (-img[y,x] * np.exp(-0.5 * ((x-cx)**2+(y-cy)**2) / R**2), key, x, y, cx, cy))

        assert(np.all(segmap > -2))
        segmap += 1
        assert(np.all(segmap >= 0))

        # Make central pixel have value 1, if it is marked.
        cx = W//2
        cy = H//2
        if segmap[cy,cx] != 0:
            # swap
            oldval = segmap[cy,cx]
            newval = segmap.max()+1
            segmap[segmap == 1] = newval
            segmap[segmap == oldval] = 1
            segmap[segmap == newval] = oldval
        
        if plots:
            plt.clf()
            rgb = cmap(segmap % 20)
            plt.imshow(rgb, origin='lower', interpolation='nearest')
            fn = 'seg-%07i.png' % k
            k += 1
            plt.savefig(fn)
            #print('Wrote', fn)

        if get_images_only:
            return [segmap],None
        import matplotlib as mpl
        cmap = mpl.colormaps['tab20']
        rgb = cmap(segmap % 20)
        return [segmap],rgb

class Decaps2Layer(ReDecalsLayer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.have_ccd_data = False

    def get_exposure_url(self, req, ccdlayername, expnum, ccdname,
                         ccd, mydomain, ra, dec, size, typ):
        fn = ccd.image_filename.split('/')[-1]
        if typ == 'image':
            pass
        elif typ == 'weight':
            fn = fn.replace('_ooi_', '_oow_')
        elif typ == 'dq':
            fn = fn.replace('_ooi_', '_ood_')
        #return 'http://decaps.skymaps.info/release/data/files/EXPOSURES/DR2/' + fn
        return 'https://decaps.rc.fas.harvard.edu/release/data/files/EXPOSURES/DR2/' + fn

    def get_exposure_contents(self, req, ccdlayername, expnum, ccdname,
                              ccd, mydomain, ra, dec, size):
        cc = []
        for typ in ['image', 'weight', 'dq']:
            url = self.get_exposure_url(req, ccdlayername, expnum, ccdname,
                                        ccd, mydomain, ra, dec, size, typ)
            cc.append('<a href="' + url + '">' + url.split('/')[-1] + '</a>')

        contents = [cc[0], cc[1], '', cc[2]]
        return contents

    def get_ccd_detail_url(self, req, layername, camera, expnum, ccdname, ccd, x, y, size):
        return None

    def has_exposure_tarball(self):
        return False

    def get_base_filename(self, brick, band, invvar=False, **kwargs):
        # image-*.fits, invvar-*.fits, not .fz
        fn = super().get_base_filename(brick, band, invvar=invvar, **kwargs)
        if not os.path.exists(fn) and fn.endswith('.fz') and os.path.exists(fn[:-3]):
            return fn[:-3]
        return fn
        
    def data_for_radec_box_html(self, req, ralo,rahi,declo,dechi):
        return []

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

    def ccds_overlapping_html(self, req, ccds, ra=None, dec=None, brick=None):

        def img_url(req, layer, ccd, ccdtag):
            fn = ccd.image_filename.strip()
            if fn.startswith('/n/fink2/decaps2'):
                url = 'http://decaps.skymaps.info/release/data/files/EXPOSURES/DR2/' + fn.replace('/n/fink2/decaps2/', '')
            else:
                url = 'http://decaps.skymaps.info/release/data/files/EXPOSURES/DR1/' + fn.replace('/n/fink2/decaps/', '')
            return url
        def dq_url(req, layer, ccd, ccdtag):
            return img_url(req, layer, ccd, ccdtag).replace('_ooi_', '_ood_')
        def iv_url(req, layer, ccd, ccdtag):
            return img_url(req, layer, ccd, ccdtag).replace('_ooi_', '_oow_')
        
        if brick is not None:
            html = ['<h1>CCDs overlapping brick:</h1>']
        elif ra is not None and dec is not None:
            html = ['<h1>CCDs overlapping RA,Dec:</h1>']
        html.extend(ccds_overlapping_html(req, ccds, self.name, ra=ra, dec=dec,
                                          ccd_link=self.have_ccd_data,
                                          img_url=img_url, dq_url=dq_url, iv_url=iv_url))
        return html

    def cutouts_html(self, req, ra, dec):
        qargs = '?ra=%.4f&dec=%.4f&layer=%s' % (ra, dec, self.name)
        cutout_jpg = my_reverse(req, 'cutout-jpeg') + qargs
        cutout_fits = my_reverse(req, 'cutout-fits') + qargs
        cutout_subimage = my_reverse(req, 'cutout-fits') + qargs + '&subimage'
    
        html = ['<h1>%s Cutouts at RA,Dec:</h1>' % self.survey.drname,
                '<ul>'
                '<li><a href="%s">Image (JPG)</a></li>' % cutout_jpg,
                '<li><a href="%s">Image (FITS)</a></li>' % cutout_fits,
                '<li><a href="%s">Image (FITS; not resampled; including inverse-variance map)</a></li>' % cutout_subimage,
                '</ul>'
                ]
        return html

    # Some of the DECaPS2 images do not have WCS headers, so create them based on the brick center.
    def read_wcs(self, brick, band, scale, fn=None):
        if scale > 0:
            return super(Decaps2Layer, self).read_wcs(brick, band, scale, fn=fn)
        from legacypipe.survey import wcs_for_brick
        return wcs_for_brick(brick)

    def get_rgb(self, imgs, bands, **kwargs):
        if self.bands == 'grz':
            # equivalent to:
            #return sdss_rgb(rimgs, bands, scales=dict(g=(2,6.0), r=(1,3.4), z=(0,2.2)), m=0.03)
            return super().get_rgb(imgs, bands, **kwargs)
        elif self.bands == 'riY':
            return sdss_rgb(imgs, bands, scales=dict(r=(2,3.4), i=(1,2.8), Y=(0,2.0)), m=0.03)
        return None

    def get_available_bands(self):
        return 'grizY'
    
class Decaps2ModelLayer(Decaps2Layer, ReDecalsModelLayer):
    pass
class Decaps2ResidLayer(Decaps2Layer, ReDecalsResidLayer):
    pass


class WiroCLayer(ReDecalsLayer):
    #def __init__(self, name):
    def get_bands(self):
        return ['NB_C']
    def get_available_bands(self):
        return ['NB_C']
    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        #from legacypipe.survey import get_rgb as rgb
        rgb,kwa = self.survey.get_rgb(imgs, bands, coadd_bw=True)
        rgb = rgb[:,:,np.newaxis].repeat(3, axis=2)
        return rgb
    def get_brick_size_for_scale(self, scale):
        if scale in [0, None]:
            return 0.7
        return super().get_brick_size_for_scale(scale)
    def get_scaled_wcs(self, brick, band, scale):
        from astrometry.util.util import Tan
        if scale in [0,None]:
            #print('Get scaled WCS: brick', brick)
            pixscale = 0.58
            cd = pixscale / 3600.
            size = 4200
            crpix = size/2. + 0.5
            wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                      float(size), float(size))
            return wcs
        return super().get_scaled_wcs(brick, band, scale)

class WiroDLayer(WiroCLayer):
    def get_bands(self):
        return ['NB_D']
    def get_available_bands(self):
        return ['NB_D']


class SuprimeIALayer(ReDecalsLayer):
    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        #from legacypipe.survey import get_rgb as rgb
        rgb,kwa = self.survey.get_rgb(imgs, bands, coadd_bw=True)
        rgb = rgb[:,:,np.newaxis].repeat(3, axis=2)
        return rgb
    def get_scaled_wcs(self, brick, band, scale):
        from astrometry.util.util import Tan
        if scale in [0,None]:
            pixscale = 0.2
            cd = pixscale / 3600.
            size = 4800
            crpix = size/2. + 0.5
            wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                      float(size), float(size))
            return wcs
        return super().get_scaled_wcs(brick, band, scale)

class SuprimeIAResidLayer(UniqueBrickMixin, ResidMixin, SuprimeIALayer):
    pass

class SuprimeAllIALayer(SuprimeIALayer):
    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        self.survey.rgb_stretch_factor = 1.5
        rgb,kwa = self.survey.get_rgb(imgs, bands, )
        return rgb

class SuprimeAllIAResidLayer(UniqueBrickMixin, ResidMixin, SuprimeAllIALayer):
    pass

class CfhtLayer(ReDecalsLayer):
    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        #from legacypipe.survey import get_rgb as rgb
        rgb,kwa = self.survey.get_rgb(imgs, bands, coadd_bw=True)
        rgb = rgb[:,:,np.newaxis].repeat(3, axis=2)
        return rgb
    def get_scaled_wcs(self, brick, band, scale):
        from astrometry.util.util import Tan
        if scale in [0,None]:
            pixscale = 0.186
            cd = pixscale / 3600.
            size = 5070
            crpix = size/2. + 0.5
            wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                      float(size), float(size))
            return wcs
        return super().get_scaled_wcs(brick, band, scale)

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

    def read_image(self, brick, band, scale, slc, fn=None):
        import fitsio
        if fn is None:
            fn = self.get_filename(brick, band, scale)
        debug('Reading image from', fn)
        ext = self.get_fits_extension(scale, fn)
        F = fitsio.FITS(fn)
        f = F[ext]
        if slc is None:
            img = f.read()
        else:
            img = f[slc]
        if scale == 0:
            ### Zero out pixels where MASK has MP_NO_DATA set --
            ### especially HSC-DR3 at the survey edges.
            maskext = 2
            f = F[maskext]
            # check
            hdr = f.read_header()
            assert(hdr['EXTTYPE'] == 'MASK')
            #
            maskbit = hdr['MP_NO_DATA']
            nodata = 1<<maskbit
            #maskbit = hdr['MP_SAT']
            #sat = 1<<maskbit
            maskbit = hdr['MP_DETECTED']
            det = 1<<maskbit
            if slc is None:
                mask = f.read()
            else:
                mask = f[slc]
            # badpix = (mask & nodata != 0)
            # badpix = (mask & (nodata | sat) == nodata)
            badpix = (mask & (nodata | det) == nodata)
            img[badpix] = 0.

        return img

class MerianLayer(HscLayer):
    '''
    table+5:
       flags                             band                         physical
    1 10000000 N540
    +14: input exposures

    TAN WCS in first extension HDU
    
    4100 pix x 0.168 "/pixel
    (HSC gridding!)
    has sky sub
    zpt??

    For RGB images, we'll take HSC g,z for B,R and use one of the Merian filters
    (N540, N708) for G.


    '''
    def __init__(self, name, hsc_layer):
        super().__init__(name)
        self.hsc = hsc_layer
        self.bands = ['g', 'N540', 'z'] #, 'N708']
        self.basedir = os.path.join(settings.DATA_DIR, self.name)
        self.scaleddir = os.path.join(settings.DATA_DIR, 'scaled', self.name)
        self.rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)
        self.bricks = None
        self.pixscale = 0.168

    def render_into_wcs(self, wcs, zoom, x, y, bands=None, **kwargs):
        import numpy as np
        if bands is None:
            bands = self.get_bands()
        # Call HSC for g,z bands
        hscbands = []
        mybands = []
        for b in bands:
            if b in ['g','z']:
                hscbands.append(b)
            else:
                mybands.append(b)
        bmap = {}
        if len(hscbands):
            rimgs = self.hsc.render_into_wcs(wcs, zoom, x, y, bands=hscbands, **kwargs)
            if rimgs is not None:
                for b,img in zip(hscbands, rimgs):
                    #print('Band', b, 'from HSC: RMS', np.sqrt(np.mean(img**2)))
                    bmap[b] = img
        if len(mybands):
            rimgs = super().render_into_wcs(wcs, zoom, x, y, bands=mybands, **kwargs)
            if rimgs is not None:
                for b,img in zip(mybands, rimgs):
                    #print('Band', b, 'from Merian: RMS', np.sqrt(np.mean(img**2)))
                    bmap[b] = img
        if len(bmap) == 0:
            return None
        res = []
        for b in bands:
            res.append(bmap.get(b))
        return res

    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
                            '%(scale)i%(band)s', '%(brickname).4s',
                            'merian' + '-%(brickname)s-%(band)s.fits')

    def get_rgb(self, imgs, bands, **kwargs):
        from tractor.brightness import NanoMaggies
        zpscale = NanoMaggies.zeropointToScale(27.0)
        rgb = sdss_rgb([im/zpscale for im in imgs], bands,
                       scales=dict(#N540=(1,3.4*5.),
                           N540=(1, 5.0 *5.),
                           N708=(1, 3.0 *5.),
                           g   =(2, 6.0 *5.),
                           z   =(0, 2.2 *5.)), m=0.03)
        return rgb

    def get_base_filename(self, brick, band, **kwargs):
        path = os.path.join(self.basedir, brick.filename.strip().replace('N540', band.upper()))
        return path
    
    def get_bricks(self):
        if self.bricks is not None:
            return self.bricks
        from astrometry.util.fits import fits_table
        self.bricks = fits_table(os.path.join(self.basedir, 'merian-bricks.fits'))
        return self.bricks

    def get_brick_size_for_scale(self, scale):
        if scale == 0:
            return 4100 * self.pixscale / 3600.
        return 0.25 * 2**scale

class IbisColorLayer(ReDecalsLayer):
    def __init__(self, name, hsc_layer):
        survey = get_survey(name)
        print('Survey for', name, ':', survey)
        super().__init__(name, 'image', survey)
        self.rgb_plane = None
        self.hsc = hsc_layer
        # HSC
        self.other_zpt = 27.0
        self.r_scale = 15.0
        
        self.bands = ['M411', 'M464', 'r']
        self.basedir = os.path.join(settings.DATA_DIR, self.name)
        self.scaleddir = os.path.join(settings.DATA_DIR, 'scaled', self.name)
        self.rgbkwargs = dict(mnmx=(-1,100.), arcsinh=1.)
        self.bricks = None

    def render_into_wcs(self, wcs, zoom, x, y, bands=None, **kwargs):
        import numpy as np
        if bands is None:
            bands = self.get_bands()
        # Call HSC for r
        hscbands = []
        mybands = []
        for b in bands:
            if b in ['r']:
                hscbands.append(b)
            else:
                mybands.append(b)
        bmap = {}
        if len(hscbands):
            rimgs = self.hsc.render_into_wcs(wcs, zoom, x, y, bands=hscbands, **kwargs)
            if rimgs is not None:
                for b,img in zip(hscbands, rimgs):
                    bmap[b] = img
        if len(mybands):
            rimgs = super().render_into_wcs(wcs, zoom, x, y, bands=mybands, **kwargs)
            if rimgs is not None:
                for b,img in zip(mybands, rimgs):
                    bmap[b] = img
        if len(bmap) == 0:
            return None
        res = []
        for b in bands:
            res.append(bmap.get(b))
        return res

    def get_rgb(self, imgs, bands, **kwargs):
        from tractor.brightness import NanoMaggies
        # HSC zeropoint
        #zpscale = NanoMaggies.zeropointToScale(27.0)
        zpscale = NanoMaggies.zeropointToScale(self.other_zpt)
        print('scale', zpscale)
        scales = dict(r=zpscale)
        rgb = sdss_rgb([im / scales.get(b, 1.) for im,b in zip(imgs, bands)], bands,
                       scales=dict(
                           M411=(2, 9.0),
                           M464=(1, 9.0),
                           r   =(0, self.r_scale),
                           ),
                       m=0.03)
        if self.rgb_plane is not None:
            for i in range(3):
                if i != self.rgb_plane:
                    rgb[:,:,i] = rgb[:,:,self.rgb_plane]

        return rgb

class Ibis3Layer(ReDecalsLayer):
    def __init__(self, name, imagetype, survey):
        super().__init__(name, imagetype, survey, bands=['M411', 'M438', 'M464', 'M490', 'M517'])
        self.rgb_plane = None
    def get_rgb(self, imgs, bands, **kwargs):
        from legacypipe.survey import sdss_rgb as ls_rgb
        rgb = ls_rgb(imgs, bands)

        # single-band layers
        if self.rgb_plane is not None:
            for i in range(3):
                if i != self.rgb_plane:
                    rgb[:,:,i] = rgb[:,:,self.rgb_plane]
        
        return rgb

class LegacySurveySplitLayer(MapLayer):
    def __init__(self, name, top, bottom, decsplit, top_bands='grz', bottom_bands='grz'):
        super(LegacySurveySplitLayer, self).__init__(name)
        self.layers = [top, bottom]
        self.top = top
        self.bottom = bottom
        self.top_bands = top_bands
        self.bottom_bands = bottom_bands
        self.decsplit = decsplit
        self.have_ccd_data = True

        self.tilesplits = {}

        import numpy as np
        dec = decsplit
        fy = 1. - (np.log(np.tan(np.deg2rad(dec + 90)/2.)) - -np.pi) / (2.*np.pi)
        for zoom in range(0, 18):
            n = 2**zoom
            y = int(fy * n)
            #print('Zoom', zoom, '-> y', y)
            #X = get_tile_wcs(zoom, 0, y)
            #wcs = X[0]
            #ok,rr,dd = wcs.pixelxy2radec([1,1], [1,256])
            #print('Decs', dd)
            self.tilesplits[zoom] = y

    def populate_fits_cutout_header(self, hdr):
        hdr['SURVEY'] = 'LegacySurvey'
        hdr['VERSION'] = self.drname.split(' ')[-1]
        hdr['IMAGETYP'] = self.top.imagetype

    def get_layer_for_radec(self, ra, dec):
        if dec < self.decsplit:
            return self.bottom
        from astrometry.util.starutil_numpy import radectolb
        l,b = radectolb(ra, dec)
        ngc = (b > 0.)
        if ngc and dec > self.decsplit:
            return self.top
        return self.bottom

    def get_bricks_for_scale(self, scale):
        import numpy as np
        from astrometry.util.fits import merge_tables
        bl = self.bottom.get_bricks_for_scale(scale)
        tl = self.top.get_bricks_for_scale(scale)
        bnames = list(bl.brickname)
        tin = np.isin(tl.brickname, bnames)
        return merge_tables([bl, tl[~tin]], columns='fillzero')

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
            #print('RA,Dec bb:', bb)
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

            html.extend(layer.cutouts_html(req, ra, dec))
            html.extend(layer.ccds_overlapping_html(req, ccds, ra=ra, dec=dec, brick=brickname))

            from legacypipe.survey import wcs_for_brick
            brickwcs = wcs_for_brick(brick)
            ok,bx,by = brickwcs.radec2pixelxy(ra, dec)
            #print('Brick x,y:', bx,by)
            ccds.cut((bx >= ccds.brick_x0) * (bx <= ccds.brick_x1) *
                     (by >= ccds.brick_y0) * (by <= ccds.brick_y1))
            #print('Cut to', len(ccds), 'CCDs containing RA,Dec point')
            if len(ccds):
                html.extend(layer.ccds_overlapping_html(req, ccds, ra=ra, dec=dec))

        html.extend(['</body></html>',])
        return HttpResponse('\n'.join(html))

    def ccds_touching_box(self, north, south, east, west, Nmax=None):
        from astrometry.util.fits import merge_tables
        import numpy as np
        ccds_n = self.top.ccds_touching_box(north, south, east, west, Nmax=Nmax)
        ccds_s = self.bottom.ccds_touching_box(north, south, east, west, Nmax=Nmax)
        ccds = []
        if ccds_n is not None:
            ccds_n.is_north = np.ones(len(ccds_n), bool)
            ccds.append(ccds_n)
        if ccds_s is not None:
            ccds_s.is_north = np.zeros(len(ccds_s), bool)
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

    def get_catalog_table(self, req, ralo, rahi, declo, dechi, brick=None, objid=None):
        from django.shortcuts import render
        from map.cats import radecbox_to_wcs
        wcs = radecbox_to_wcs(ralo, rahi, declo, dechi)
        cat,hdr = self.get_catalog_in_wcs(wcs)
        if brick is not None:
            cat = cat[cat.brickname == brick]
        if objid is not None:
            cat = cat[cat.objid == objid]
        if len(cat) == 0:
            return HttpResponse('No sources')
        cols = cat.get_columns()
        for band in ['g','r','i','z','w1','w2','w3','w4']:
            c = 'flux_' + band
            import numpy as np
            if c in cols:
                f = cat.get(c)
                mag = -2.5 * (np.log10(f) - 9)
                cat.set('mag_' + band, mag)
        cols = cat.get_columns()
        cat_dict = {}
        for c in cols:
            cat_dict[c] = cat.get(c)
        args = dict(cat_entries=cat_dict)
        return render(req, 'cat_table.html', args)
        #return HttpResponse('got %i sources' % len(cat))
        # fn = 'cat-%s.fits' % (self.name)
        # import tempfile
        # f,outfn = tempfile.mkstemp(suffix='.fits')
        # os.close(f)
        # os.unlink(outfn)
        # cat.writeto(outfn, header=hdr)
        # return send_file(outfn, 'image/fits', unlink=True, filename=fn)

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
            # Merge DRs with different lengths of WISE light curves...
            lclen = 0
            for c in allcats:
                x = c.lc_flux_w1
                _,w = x.shape
                lclen = max(lclen, w)
            for c in allcats:
                for col in c.get_columns():
                    if not col.startswith('lc_'):
                        continue
                    x = c.get(col)
                    n,w = x.shape
                    if w == lclen:
                        continue
                    y = np.zeros((n,lclen), x.dtype)
                    y[:,:w] = x
                    c.set(col, y)

            allcats = merge_tables(allcats, columns='fillzero')
        return allcats,hdr

    def get_bricks(self):
        from astrometry.util.fits import merge_tables
        BB = merge_tables([l.get_bricks() for l in self.layers], columns='fillzero')
        return BB

    def bricks_touching_radec_box(self, *args, **kwargs):
        from astrometry.util.fits import merge_tables
        BB = merge_tables([l.bricks_touching_radec_box(*args, **kwargs)
                           for l in self.layers], columns='fillzero')
        return BB

    def get_filename(self, brick, band, scale, tempfiles=None, invvar=False, maskbits=False):
        layer = self.get_layer_for_radec(brick.ra, brick.dec)
        return layer.get_filename(brick, band, scale, tempfiles=tempfiles, invvar=invvar, maskbits=maskbits)

    def get_base_filename(self, brick, band, **kwargs):
        layer = self.get_layer_for_radec(brick.ra, brick.dec)
        return layer.get_base_filename(brick, band, **kwargs)

    def has_invvar(self):
        return True

    def has_maskbits(self):
        return True

    def get_fits_extension(self, scale, fn):
        if fn.endswith('.fz'):
            return 1
        return 0

    def render_rgb(self, wcs, zoom, x, y, bands=None, tempfiles=None, get_images_only=False,
                   invvar=False, maskbits=False):
        #print('Split Layer render_rgb: bands=', bands)
        kwa = dict(tempfiles=tempfiles, get_images_only=get_images_only, invvar=invvar,
                   maskbits=maskbits)
        if y != -1:
            # FIXME -- this is not the correct cut -- only listen to split for NGC --
            # but this doesn't get called anyway because the JavaScript layer has the smarts.
            split = self.tilesplits[zoom]
            if y < split:
                #print('Split Layer render_rgb: short-cutting to north')
                #print('y below split -- north')
                if bands is None:
                    b = self.top_bands
                else:
                    b = bands
                return self.top.render_rgb(wcs, zoom, x, y, bands=b, **kwa)
            if y > split:
                #print('Split Layer render_rgb: short-cutting to south')
                if bands is None:
                    b = self.bottom_bands
                else:
                    b = bands
                #print('y above split -- south')
                return self.bottom.render_rgb(wcs, zoom, x, y, bands=b, **kwa)

        # ASSUME that the WCS is axis-aligned!!
        # Compute Decs for each Y in the WCS
        import numpy as np
        from astrometry.util.starutil_numpy import radectolb
        H,W = wcs.shape
        x = np.empty(H)
        x[:] = W//2 + 0.5
        y = np.arange(1, H+1)
        rr,dd = wcs.pixelxy2radec(x, y)[-2:]
        ll,bb = radectolb(rr, dd)
        ngc = (bb > 0.)
        topmask = (dd >= self.decsplit) * ngc

        botonly = np.all(np.logical_not(topmask))

        if not botonly:
            topims,toprgb = self.top.render_rgb(wcs, zoom, x, y, bands=bands, **kwa)
            if np.all(topmask):
                return topims,toprgb

        botims,botrgb = self.bottom.render_rgb(wcs, zoom, x, y, bands=bands, **kwa)
        if botonly:
            return botims,botrgb

        if get_images_only and topims is None and botims is None:
            return None,None

        topbandmap = {}
        if bands is None:
            topbandmap.update(dict([(b,i) for i,b in enumerate(self.top_bands)]))
            # HACK
            bands = self.bottom_bands
        else:
            topbandmap.update(dict([(b,i) for i,b in enumerate(bands)]))
            
        ims = []
        topim = None
        botim = None
        for ii,band in enumerate(bands):
            if topims is not None:
                if band not in topbandmap:
                    continue
                topim = topims[topbandmap[band]]
            if botims is not None:
                botim = botims[ii]
            if (topim is None) and (botim is None):
                ims.append(None)
                continue
            im = np.zeros(wcs.shape, np.float32)
            if topim is not None:
                im[topmask,:] = topim[topmask,:]
            if botim is not None:
                im[~topmask,:] = botim[~topmask,:]
            ims.append(im)
        if get_images_only:
            return ims,None

        #print('SplitLayer render_rgb: rgb: top', toprgb.shape if toprgb is not None else 'None', 'bottom', botrgb.shape if botrgb is not None else 'None')

        if toprgb is not None and botrgb is None:
            return ims,toprgb
        # Copy top into bottom
        if botrgb is not None and toprgb is not None:
            botrgb[topmask,:,:] = toprgb[topmask,:,:]

        return ims,botrgb

    def get_bands(self):
        #return self.top.get_bands()
        return self.bottom_bands
    def get_rgb(self, *args, **kwargs):
        return self.top.get_rgb(*args, **kwargs)
    def get_scale(self, *args):
        return self.top.get_scale(*args)

    def get_tile_filename(self, ver, zoom, x, y):
        '''Pre-rendered JPEG tile filename.'''
        #print('SplitLayer.get_tile_filename: zoom', zoom, 'y', y)
        split = self.tilesplits[zoom]
        ## FIXME -- this is not the correct cut -- ignores NGC/SGC difference
        if y < split:
            fn = self.top.get_tile_filename(ver, zoom, x, y)
            #print('Top fn', fn)
            return fn
            #return self.top.get_tile_filename(ver, zoom, x, y)
        if y > split:
            #return self.bottom.get_tile_filename(ver, zoom, x, y)
            fn = self.bottom.get_tile_filename(ver, zoom, x, y)
            #print('Bottom fn', fn)
            return fn
            
        tilefn = os.path.join(self.tiledir,
                              '%i' % ver, '%i' % zoom, '%i' % x, '%i.jpg' % y)
        #print('Middle:', tilefn)
        return tilefn

class DesLayer(ReDecalsLayer):

    def __init__(self, name):
        super(DesLayer, self).__init__(name, 'image', None)
        self.bricks = None
        self.dir = os.path.join(settings.DATA_DIR, name)

    def has_cutouts(self):
        return False

    def has_invvar(self):
        return False

    def get_base_filename(self, brick, band, **kwargs):
        from glob import glob
        brickname = brick.brickname
        # DES filenames have a weird-ass string in them so glob
        # eg, "DES0000+0209_r2590p01_g.fits.fz"
        pat = os.path.join(self.dir, 'dr1_tiles', brickname,
                           '%s_*_%s.fits.fz' % (brickname, band))
        fns = glob(pat)
        #print('Glob:', pat, '->', fns)
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

    def get_pixel_size_for_scale(self, scale):
        if scale == 0:
            return 10000
        return super(DesLayer,self).get_pixel_size_for_scale(scale)

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
        #print('Bricks:', bricks)
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
        print('Read', len(self.bricks), 'bricks (ps1 skycells)')
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

    def get_filename(self, brick, band, scale, tempfiles=None, invvar=False, maskbits=False):
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
        #print('Bwcs shape:', H,W)
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
        debug('Unwise bricks touching RA,Dec box', ralo, rahi, declo, dechi)
        I, = np.nonzero((bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        ok = ra_ranges_overlap(ralo, rahi, bricks.ra1[I], bricks.ra2[I])
        I = I[ok]
        debug('-> bricks', bricks.brickname[I])
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
        #print('unWISE populate FITS cutout header')
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
        #print('Unwise bricks for scale', scale, '->', fn)
        b = fits_table(fn)
        return b

    def bricks_touching_radec_box(self, ralo, rahi, declo, dechi, scale=None):
        '''
        Both RebrickedMixin and UnwiseLayer override this function -- here we have
        to merge the capabilities.
        '''
        import numpy as np
        bricks = self.get_bricks_for_scale(scale)
        #print('(unwise) scale', scale, 'bricks touching RA,Dec box', ralo, rahi, declo, dechi)
        I, = np.nonzero((bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        ok = ra_ranges_overlap(ralo, rahi, bricks.ra1[I], bricks.ra2[I])
        I = I[ok]
        #print('-> bricks', bricks.brickname[I])
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

class UnwiseMask(RebrickedUnwise):
    # Only works for scale=0
    def get_bricks_for_scale(self, scale):
        if scale in [0, None]:
            return super().get_bricks_for_scale(scale)
        return None
    # One mask file per brick
    def get_bands(self):
        return '1'
    # data/unwise-neo7/000/0000p757/unwise-0000p757-msk.fits.gz
    def get_base_filename(self, brick, band, **kwargs):
        brickname = brick.brickname
        brickpre = brickname[:3]
        fn = os.path.join(self.dir, brickpre, brickname,
                          'unwise-%s-msk.fits.gz' % (brickname))
        return fn

    # Called by render_into_wcs
    def resample_for_render(self, wcs, subwcs, img, coordtype):
        from astrometry.util.resample import resample_with_wcs
        Yo,Xo,Yi,Xi,_ = resample_with_wcs(wcs, subwcs, [],
                                          intType=coordtype)
        return Yo,Xo,Yi,Xi,None

    def initialize_accumulator_for_render(self, W, H, band, **kwargs):
        return RenderAccumulatorMask(W, H)

class UnwiseW3W4(RebrickedUnwise):
    def get_bands(self):
        # Note, not 'w1','w2'...
        return '34'
    def get_rgb(self, imgs, bands, **kwargs):
        return _unwise_w34_to_rgb(imgs, **kwargs)

def _unwise_w34_to_rgb(imgs, bands=[3,4],
                   scale3=10.,
                   scale4=40.,
                   arcsinh=1./20.,
                   mn=-20.,
                   mx=10000.,
                   w3weight=9.):
    import numpy as np
    img = imgs[0]
    H,W = img.shape
    ## FIXME
    assert(bands == [3,4])
    w3,w4 = imgs
    rgb = np.zeros((H, W, 3), np.uint8)
    img3 = w3 / scale3
    img4 = w4 / scale4
    if arcsinh is not None:
        def nlmap(x):
            return np.arcsinh(x * arcsinh) / np.sqrt(arcsinh)
        # intensity -- weight W3 more
        bright = (w3weight * img3 + img4) / (w3weight + 1.)
        I = nlmap(bright)
        # color -- abs here prevents weird effects when, eg, W3>0 and W4<0.
        mean = np.maximum(1e-6, (np.abs(img3)+np.abs(img4))/2.)
        img3 = np.abs(img3)/mean * I
        img4 = np.abs(img4)/mean * I
        mn = nlmap(mn)
        mx = nlmap(mx)
    img3 = (img3 - mn) / (mx - mn)
    img4 = (img4 - mn) / (mx - mn)
    rgb[:,:,2] = (np.clip(img3, 0., 1.) * 255).astype(np.uint8)
    rgb[:,:,0] = (np.clip(img4, 0., 1.) * 255).astype(np.uint8)
    rgb[:,:,1] = rgb[:,:,0]/2 + rgb[:,:,2]/2
    return rgb


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
        #print('Wrote', fn)

    def create_scaled_image(self, brick, band, scale, fn, tempfiles=None):
        ro = settings.READ_ONLY_BASEDIR
        if ro:
            print('Read-only; not creating scaled GALEX image for brick', brick, 'scale', scale, 'band', band)
            return None
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

    def get_filename(self, brick, band, scale, tempfiles=None, invvar=False, maskbits=False):
        #print('galex get_filename: scale', scale, 'band', band, 'brick', brick.brickname)
        if scale == -1:
            return self.get_base_filename(brick, band)
        brickname = brick.brickname
        fnargs = dict(band=band, brickname=brickname, scale=scale)
        fn = self.get_scaled_pattern() % fnargs
        if not os.path.exists(fn):
            #print('Creating', fn)
            r = self.create_scaled_image(brick, band, scale, fn, tempfiles=tempfiles)
            if r is None:
                return None
            #print('Created', fn)
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
        #print('Galex bricks for scale', scale, '->', fn)
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
            #print('Image', brick.brickname, 'exptime', brick.nexptime, 'NUV', brick.fexptime, 'FUV')
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
        #print('Reading image from', fn)
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
        #print('2MASS bricks touching RA,Dec box', ralo, rahi, declo, dechi)
        I, = np.nonzero((bricks.dec1 <= dechi) * (bricks.dec2 >= declo))
        ok = ra_ranges_overlap(ralo, rahi, bricks.ra1[I], bricks.ra2[I])
        I = I[ok]
        #print('-> bricks', bricks.brickname[I])
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
        #print('Reading image from', fn)
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

    def get_brick_size_for_scale(self, scale):
        if scale is None:
            scale = 0
        return 1. * 2**scale

    def get_bricks(self):
        from astrometry.util.fits import fits_table
        return fits_table(os.path.join(self.basedir, 'vlass-tiles.fits'))

    def get_bricks_for_scale(self, scale):
        if scale in [0, None]:
            return self.get_bricks()
        scale = min(scale, self.maxscale)
        from astrometry.util.fits import fits_table
        fn = os.path.join(self.basedir, 'vlass-bricks-%i.fits' % scale)
        #print('vlass bricks for scale', scale, '->', fn)
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
        wcs = Tan(*[float(f) for f in [brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                                      size, size]])
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
        #print('Bricks:', bricks)
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


class anwcs_wrapper(object):
    def __init__(self, *args):
        from astrometry.util.util import anwcs_t
        self._anwcs = anwcs_t(*args)
    def get_subimage(self, x0, y0, w, h):
        #print('anwcs_wrapper: get_subimage')
        s = self._anwcs.getHeaderString()
        s = s.encode()
        s = (b'SIMPLE  =                    T / Standard FITS file                             ' +
             b'BITPIX  =                    8 / ASCII or bytes array                           ' +
             b'NAXIS   =                    0 / Minimal header                                 ' +
             s)
        L = len(s)
        pad = 2880 - (L % 2880)
        s += b' '*pad
        import tempfile
        f,tmpfn = tempfile.mkstemp()
        os.close(f)
        open(tmpfn,'wb').write(s)
        import fitsio
        hdr = fitsio.read_header(tmpfn)
        crpix1 = hdr['CRPIX1']
        crpix2 = hdr['CRPIX2']
        crpix1 -= x0
        crpix2 -= y0
        hdr['CRPIX1'] = crpix1
        hdr['CRPIX2'] = crpix2
        hdr.delete('NAXIS1')
        hdr.delete('NAXIS2')
        fitsio.write(tmpfn, None, header=hdr, clobber=True)
        wcs = anwcs_wrapper(tmpfn, 0)
        os.remove(tmpfn)
        wcs.imagew = int(w)
        wcs.imageh = int(h)
        #print('desired h,w:', h, w, 'wcs shape:', wcs.shape)
        return wcs
        
    def __getattr__(self, k):
        return getattr(self._anwcs, k)
    def __setattr__(self, k, v):
        if k == '_anwcs':
            object.__setattr__(self, k, v)
        else:
            self._anwcs.__setattr__(k, v)

class PandasLayer(RebrickedMixin, MapLayer):

    def __init__(self, name):
        super().__init__(name, nativescale=14)
        self.pixscale = 0.186
        self.bands = self.get_bands()
        self.pixelsize = 5100
        self.maxscale = 7

    def get_bricks(self):
        from astrometry.util.fits import fits_table
        return fits_table(os.path.join(self.basedir, 'pandas.fits'))

    # def get_bricks_for_scale(self, scale):
    #     if scale in [0, None]:
    #         return self.get_bricks()
    #     scale = min(scale, self.maxscale)
    #     from astrometry.util.fits import fits_table
    #     fn = os.path.join(self.basedir, 'pandas-bricks-%i.fits' % scale)
    #     b = fits_table(fn)
    #     return b

    def get_scaled_wcs(self, brick, band, scale):
        #print('get_scaled_wcs: scale', scale, 'brick', brick)
        from astrometry.util.util import Tan
        if scale < 5:
            size = self.pixelsize
        elif scale == 5:
            size = self.pixelsize * 1.07
        elif scale >= 6:
            size = self.pixelsize * 1.18

        pixscale = self.pixscale * 2**scale
        cd = pixscale / 3600.
        crpix = size/2. + 0.5
        wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                  float(size), float(size))
        return wcs

    def get_bands(self):
        return ['g','i']

    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        assert(len(imgs) == 2)
        img = imgs[0]
        H,W = img.shape

        rgb = np.zeros((H,W,3), np.uint8)
        # g,i
        blu,red = imgs
        mn,mx = -20, 2000

        blu *= 1.2
        
        arcsinh=1./20.
        def nlmap(x):
            return np.arcsinh(x * arcsinh) / np.sqrt(arcsinh)
        bright = (blu + red) / 2.
        I = nlmap(bright)
        # color -- abs here prevents weird effects when, eg, W1>0 and W2<0.
        mean = np.maximum(1e-6, (np.abs(red)+np.abs(blu))/2.)
        red = np.abs(red)/mean * I
        blu = np.abs(blu)/mean * I
        mn = nlmap(mn)
        mx = nlmap(mx)

        blu = (blu - mn) / (mx - mn)
        red = (red - mn) / (mx - mn)

        rgb[:,:,2] = (np.clip(blu, 0., 1.) * 255).astype(np.uint8)
        rgb[:,:,0] = (np.clip(red, 0., 1.) * 255).astype(np.uint8)
        rgb[:,:,1] = rgb[:,:,0]/2 + rgb[:,:,2]/2

        return rgb

    def get_base_filename(self, brick, band, **kwargs):
        # The "pandas.fits" file contains only g-band images; swap in correct band.
        fn = brick.filename_g.strip().replace('_g.fit', '_%s.fit'%band)
        return os.path.join(self.basedir, fn)

    def read_image(self, brick, band, scale, slc, fn=None):
        if scale > 0:
            return super().read_image(brick, band, scale, slc, fn=fn)
        import fitsio
        if fn is None:
            fn = self.get_filename(brick, band, scale)
        #print('read_image: brick', brick.brickname, 'band', band, 'scale', scale, 'fn', fn)
        #print('ext', brick.ext)
        f = fitsio.FITS(fn)[brick.ext]
        med = getattr(brick, 'median_'+band)
        if slc is None:
             return f.read() - med
        return f[slc] - med

    def read_wcs(self, brick, band, scale, fn=None):
        if scale > 0:
            return super().read_wcs(brick, band, scale, fn=fn)

        if fn is None:
            fn = self.get_filename(brick, band, scale)
        if fn is None:
            return None
        #print('read_wcs: brick', brick.brickname, 'band', band, 'scale', scale, 'fn', fn)
        #print('ext', brick.ext)
        wcs = anwcs_wrapper(fn, int(brick.ext))
        import fitsio
        hdr = fitsio.read_header(fn, ext=int(brick.ext))
        w = hdr['NAXIS1']
        h = hdr['NAXIS2']
        wcs.imagew = int(w)
        wcs.imageh = int(h)
        #wcs.imagew = int(brick.width)
        #wcs.imageh = int(brick.height)
        #sub = wcs.get_subimage(100, 100, 200, 200)
        return wcs
    
    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
                            '%(scale)i%(band)s', '%(brickname).3s',
                            '%(brickname)s.fits')


    
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


class CFISLayer(RebrickedMixin, MapLayer):
    def __init__(self, name, band):
        super(CFISLayer, self).__init__(name, nativescale=14)
        self.pixscale = 0.186
        self.bands = [band]
        self.pixelsize = 5300
        self.maxscale = 7

    def get_bricks(self):
        from astrometry.util.fits import fits_table
        import numpy as np
        T = fits_table(os.path.join(self.basedir, 'cfis-tiles.kd.fits'))
        T.brickname = np.array(['%s.%s' % (g1,g2)
                                for g1,g2 in zip(T.grid1, T.grid2)])
        T.ra  = T.crval1
        T.dec = T.crval2
        return T

    def get_pixel_coord_type(self, scale):
        import numpy as np
        return np.int16

    # def get_bricks_for_scale(self, scale):
    #     print('CFISlayer: get_bricks_for_scale', scale)
    #     if scale in [0, None]:
    #         return self.get_bricks()
    #     scale = min(scale, self.maxscale)
    #     from astrometry.util.fits import fits_table
    #     fn = os.path.join(self.basedir, 'bricks-%i.fits' % scale)
    #     if not os.path.exists(fn):
    #         # generic
    #         fn = os.path.join(settings.DATA_DIR, 'bricks-%i.fits' % scale)
    #         b = fits_table(fn)
    #         print('generic bricks:', len(b))
    #         b0 = self.get_bricks_for_scale(scale-1)
    #         print('smaller-scale bricks:', len(b0))
    #         rad = 1.5 * (self.pixelsize * self.pixscale * 2.**scale) / 3600. / np.sqrt(2.)
    #         
    # 
    #         sys.exit(-1)
    #         
    #     else:
    #         b = fits_table(fn)
    #     return b

    def bricks_within_range(self, ra, dec, radius, scale=None):
        from astrometry.libkd.spherematch import match_radec, tree_open, tree_search_radec
        from astrometry.util.fits import fits_table
        import numpy as np
        if scale > 0:
            return None
        # cfis.py
        # startree -i cfis-files-dr3-r.fits -o data/cfis-dr3-r/cfis-tiles.kd.fits -PTk
        fn = os.path.join(self.basedir, 'cfis-tiles.kd.fits')
        kd = tree_open(fn)
        # 0.4 ~ 10k / 2 * sqrt(2) x 186"/pix
        I = tree_search_radec(kd, ra, dec, radius + 0.4)
        T = fits_table(fn, rows=I)
        T.brickname = np.array(['%s.%s' % (g1,g2)
                                for g1,g2 in zip(T.grid1, T.grid2)])
        T.ra  = T.crval1
        T.dec = T.crval2
        return T

    def get_scaled_wcs(self, brick, band, scale):
        from astrometry.util.util import Tan
        if scale == 0:
            size = 10000
        elif scale < 7:
            size = self.pixelsize
        elif scale == 7:
            size = int(self.pixelsize * 1.1)
        elif scale >= 8:
            size = int(self.pixelsize * 1.2)
        pixscale = self.pixscale * 2**scale
        cd = pixscale / 3600.
        crpix = size/2. + 0.5
        wcs = Tan(brick.ra, brick.dec, crpix, crpix, -cd, 0., 0., cd,
                  float(size), float(size))
        return wcs

    def get_bands(self):
        return self.bands

    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        #scales = dict(g=(2,3.0), r=(1,2.0), i=(0,0.8))

        scales = dict(R=(1, 10.), U=(1, 10.))
        rgb = sdss_rgb(imgs, bands, scales=scales)
        rgb[:,:,0] = rgb[:,:,2] = rgb[:,:,1]
        return rgb

    def get_base_filename(self, brick, band, **kwargs):
        return os.path.join(self.basedir, brick.filename.strip())

    def get_fits_extension(self, scale, fn):
        # if scale == 0:
        #     return 0
        return 1

    def get_scaled_pattern(self):
        return os.path.join(self.scaleddir,
                            '%(scale)i%(band)s', '%(brickname).3s',
                            'cfis-%(brickname)s-%(band)s.fits')

    def read_image(self, brick, band, scale, slc, fn=None):
        #print('Read CFIS image: brick', brick, 'band', band, 'scale', scale, 'slice', slc)
        img = super(CFISLayer, self).read_image(brick, band, scale, slc, fn=fn)
        if scale > 0:
            return img

        # scale
        zpscale = 10.**((30 - 22.5) / 2.5)
        img = img / zpscale
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

    def render_into_wcs(self, wcs, zoom, x, y, bands=None, tempfiles=None,
                        invvar=False, maskbits=False):
        assert(not invvar)
        assert(not maskbits)
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
            #print('Wrote', fn)
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
                #print('Found', len(I), 'rows with expnum ==', expnum)

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
        #print('north CCDs:', ccds_n)
        ccds_s = self.south.find_ccds(expnum=expnum, ccdname=ccdname, camera=camera)
        #print('south CCDs:', ccds_s)
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
        #print('ccds_touching_wcs: north', n)
        if n is not None:
            n.is_north = np.ones(len(n), bool)
            n.layer = np.array([self.north.layer] * len(n))
            ns.append(n)
        s = self.south.ccds_touching_wcs(wcs, **kwargs)
        #print('ccds_touching_wcs: south', s)
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
            codir0 = os.path.join(basedir, 'coadd-override', brickpre, brick)
            codir = os.path.join(basedir, 'coadd', brickpre, brick)
        sname = self.file_prefix
        # No .fits.fz suffix, just .fits
        if filetype in ['image']:
            fn = os.path.join(codir0,
                              '%s-%s-%s-%s.fits' % (sname, brick, filetype, band))
            if os.path.exists(fn):
                return fn
            return os.path.join(codir,
                                '%s-%s-%s-%s.fits' % (sname, brick, filetype, band))
        if filetype in ['model']:
            # coadd-model dir; named "legacysurvey-BRICK-image", not "-model"
            codir0 = os.path.join(basedir, 'coadd-model-override', brickpre, brick)
            fn = os.path.join(codir0,
                            '%s-%s-%s-%s.fits' % (sname, brick, 'image', band))
            if os.path.exists(fn):
                return fn
            codir = os.path.join(basedir, 'coadd-model', brickpre, brick)
            return os.path.join(codir,
                                '%s-%s-%s-%s.fits' % (sname, brick, 'image', band))
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

class AsteroidsLayer(ReDecalsLayer):
    def get_rgb(self, imgs, bands, **kwargs):
        rgb = super().get_rgb(imgs, bands, **kwargs)
        rgb[:,:,1] = rgb[:,:,2] = rgb[:,:,0]
        return rgb
    def get_bands(self):
        return 'i'

class OutliersLayer(DecalsLayer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scaledir = None
        #self.bands = 'o'
        self.bands = 'rgb'
        self.imagetype = 'outliers-masked-pos'

        self.cached_brick = None
        self.cached_image = None

    def has_invvar(self):
        return False

    def get_base_filename(self, brick, band, invvar=False, **kwargs):
        return self.survey.find_file(self.imagetype, brick=brick.brickname, band=band)

    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        #print('get_rgb: Bands:', bands)
        #print('imgs:', [i.shape for i in imgs])
        #return imgs[0]
        rgb = np.dstack(imgs)
        #print('get_rgb:', rgb.shape)
        #print('rgb range:', rgb.min(), rgb.max())
        rgb = np.clip(rgb, 0., 1.)
        return rgb

    def get_scale(self, zoom, x, y, wcs):
        if zoom >= 12:
            return 0
        return -1

    def read_image(self, brick, band, scale, slc, fn=None):
        import pylab as plt
        import numpy as np

        if fn is None:
            fn = self.get_filename(brick, band, scale)

        key = fn #(brick, scale, slc)
        if self.cached_brick == key:
            #print('Using cached image for', fn, 'band', band)
            rgb = self.cached_image
        else:
            #print('Reading image from', fn)
            rgb = plt.imread(fn)
            rgb = np.flipud(rgb)
            #print('rgb:', rgb.shape)

            self.cached_brick = key
            self.cached_image = rgb

        plane = 'rgb'.index(band)
        img = rgb[:,:,plane]
        if slc is not None:
            img = img[slc]
            #print('sliced:', img.shape)
        #print('returning image type', img.dtype)
        img = img.astype(np.float32) / 255.
        return img

    def read_wcs(self, brick, band, scale, fn=None):
        if fn is None:
            fn = self.get_filename(brick, band, scale)
        #print('Reading WCS for', fn)
        if not os.path.exists(fn):
            return None
        #print('(brick', brick, 'band', band, 'scale', scale)
        from legacypipe.survey import wcs_for_brick
        wcs = wcs_for_brick(brick)
        return wcs

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
            #print('No bricks touching WCS')
            return None
        if bands is None:
            bands = self.get_bands()
        W = int(wcs.get_width())
        H = int(wcs.get_height())
        target_ra,target_dec = wcs.pixelxy2radec([1,  1,1,W/2,W,W,  W,W/2],
                                                 [1,H/2,H,H,  H,H/2,1,1  ])[-2:]
        coordtype = self.get_pixel_coord_type(scale)
        rimgs = {}
        rws = {}
        for band in bands:
            rimgs[band] = np.zeros((H,W), np.float32)
            rws[band]   = np.zeros((H,W), np.float32)
        brick_bands = {}
        allbricks = {}
        for band in bands:
            bandbricks = self.bricks_for_band(bricks, band)
            for brick in bandbricks:
                if not brick.brickname in brick_bands:
                    brick_bands[brick.brickname] = []
                    allbricks[brick.brickname] = brick
                brick_bands[brick.brickname].append(band)
        for brickname,brick in allbricks.items():
            bimgs = []
            # ASSUME WCS for all bands is the same!
            band = brick_bands[brickname][0]
            fn = self.get_filename(brick, band, scale, tempfiles=tempfiles)
            #print('Reading', brickname, 'band', band, 'scale', scale, '-> fn', fn)
            if fn is None:
                continue
            try:
                bwcs = self.read_wcs(brick, band, scale, fn=fn)
                if bwcs is None:
                    #print('No such file:', brickname, band, scale, 'fn', fn)
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
            xx = xx.astype(np.int32)
            yy = yy.astype(np.int32)
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
            ih,iw = subwcs.shape
            assert(np.iinfo(coordtype).max > max(ih,iw))
            oh,ow = wcs.shape
            assert(np.iinfo(coordtype).max > max(oh,ow))

            goodimgs = []
            goodbands = []
            imgtype = None
            for band in brick_bands[brickname]:
                try:
                    img = self.read_image(brick, band, scale, slc, fn=fn)
                    imgtype = img.dtype
                except:
                    print('Failed to read image:', brickname, band, scale, 'fn', fn)
                    savecache = False
                    import traceback
                    import sys
                    traceback.print_exc(None, sys.stdout)
                    continue
                goodimgs.append(img)
                goodbands.append(band)
            try:
                Yo,Xo,Yi,Xi,resamps = resample_with_wcs(wcs, subwcs, goodimgs, intType=coordtype)
            except OverlapError:
                continue
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
                resamps = [resamp[I] for resamp in resamps]

            # if not np.all(np.isfinite(resamp)):
            #     ok, = np.nonzero(np.isfinite(resamp))
            #     Yo = Yo[ok]
            #     Xo = Xo[ok]
            #     Yi = Yi[ok]
            #     Xi = Xi[ok]
            #     resamps = [resamp[ok] for resamp in resamps]

            ok = self.filter_pixels(scale, img, wcs, subwcs, Yo,Xo,Yi,Xi)
            if ok is not None:
                Yo = Yo[ok]
                Xo = Xo[ok]
                Yi = Yi[ok]
                Xi = Xi[ok]
                resamps = [resamp[ok] for resamp in resamps]

            for band,resamp in zip(goodbands, resamps):
                wt = self.get_pixel_weights(band, brick, scale)
                rimgs[band][Yo,Xo] += resamp * wt
                rws  [band][Yo,Xo] += wt

            for band in goodbands:
                rimgs[band] /= np.maximum(rws[band], 1e-18)

        rimgs = [rimgs[b] for b in bands]
        return rimgs


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

    elif name == 'decaps2':
        survey = Decaps2LegacySurveyData(survey_dir=dirnm)
        survey.drname = 'DECaPS 2'
        survey.drurl = 'https://portal.nersc.gov/project/cosmo/temp/dstn/decaps2-coadd'#https://portal.nersc.gov/cfs/cosmo/data/decaps/dr1'
        
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

    elif name in ['ls-dr10']:
        north = get_survey('ls-dr9-north')
        north.layer = 'ls-dr9-north'
        south = get_survey('ls-dr10-south')
        south.layer = 'ls-dr10-south'
        survey = SplitSurveyData(north, south)

    elif name == 'dr10-deep':
        survey = LegacySurveyData(survey_dir=dirnm, cache_dir=cachedir)
        survey.bricksize = 0.025

    #print('dirnm', dirnm, 'exists?', os.path.exists(dirnm))

    elif name in ['ibis-3-m411', 'ibis-3-m438', 'ibis-3-m464', 'ibis-3-m490', 'ibis-3-m517',
                  'ibis-3-wide-m411', 'ibis-3-wide-m438', 'ibis-3-wide-m464',
                  'ibis-3-wide-m490', 'ibis-3-wide-m517',]:
        name = name[:-5]
        dirnm = os.path.join(basedir, name)


    if survey is None and not os.path.exists(dirnm):
        return None

    if survey is None:
        survey = LegacySurveyData(survey_dir=dirnm, cache_dir=cachedir)
        #print('Creating LegacySurveyData for', name, 'with survey', survey, 'dir', dirnm)

    names_urls = {
        'mzls+bass-dr6': ('MzLS+BASS DR6', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr6/'),
        'decals-dr5': ('DECaLS DR5', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr5/'),
        'decals-dr7': ('DECaLS DR7', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr7/'),
        'eboss': ('eBOSS', 'https://legacysurvey.org/'),
        #'decals': ('DECaPS', 'https://legacysurvey.org/'),
        'ls-dr67': ('Legacy Surveys DR6+DR7', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/'),
        'ls-dr8-north': ('Legacy Surveys DR8-north', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr8/north'),
        'ls-dr8-south': ('Legacy Surveys DR8-south', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr8/south'),
        'ls-dr8': ('Legacy Surveys DR8', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr8/'),

        'ls-dr9-north': ('Legacy Surveys DR9-north', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr9/north'),
        'ls-dr9-south': ('Legacy Surveys DR9-south', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr9/south'),
        'ls-dr9': ('Legacy Surveys DR9', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr9/'),
        'ls-dr10-south': ('Legacy Surveys DR10-south', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr10/south'),
        'ls-dr10': ('Legacy Surveys DR10', 'https://portal.nersc.gov/cfs/cosmo/data/legacysurvey/dr10'),
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
    #print('Name:', name)
    name = clean_layer_name(name)
    #print('Mapped name:', name)

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
        #print(len(I), 'unwise tiles within', radius, 'deg of RA,Dec (%.3f, %.3f)' % (rc,dc))
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
    #print('No CCDs touching box from layer', layer)
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
        filters = set(c.filter)
        if 'i' in filters or 'Y' in filters:
            ccmap = dict(g='#0000cc', r='#008844', i='#448800', z='#cc0000', Y='#cc4444')
        else:
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
    if name in ['decals-dr5', 'decals-dr7', 'ls-dr8-south', 'ls-dr9-south', 'ls-dr10-south']:
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
    #print('Name:', name)
    name = clean_layer_name(name)
    #print('Mapped name:', name)

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
    cmap = dict(g='#00ff00', r='#ff0000', z='#cc00cc')
    if 'ls-dr10' in name:
        cmap = dict(g='#0000cc', r='#008844', i='#448800', z='#cc0000')
    for t in T:
        if t.filter not in cmap:
            continue
        exps.append(dict(name='%i %s' % (t.expnum, t.filter),
                         ra=t.ra, dec=t.dec, radius=radius,
                         color=cmap[t.filter]))

    return HttpResponse(json.dumps(dict(objs=exps)),
                        content_type='application/json')

plate_cache = None
def read_sdss_plates():
    global plate_cache
    if plate_cache is None:
        from astrometry.libkd.spherematch import tree_build_radec
        from astrometry.util.fits import fits_table
        import numpy as np
        T = fits_table(os.path.join(settings.DATA_DIR, 'sdss',
                                    'plates-dr16.fits'))
        T.rename('racen', 'ra')
        T.rename('deccen', 'dec')
        # Cut to the first entry for each PLATE
        nil,I = np.unique(T.plate, return_index=True)
        T.cut(I)
        tree = tree_build_radec(T.ra, T.dec)
        plate_cache = (T,tree)
    else:
        T,tree = plate_cache
    return T,tree

def sdss_plate_list(req):
    import json
    from astrometry.util.fits import fits_table
    import numpy as np

    north = float(req.GET['dechi'])
    south = float(req.GET['declo'])
    east  = float(req.GET['ralo'])
    west  = float(req.GET['rahi'])
    name = 'sdss'
    plate = req.GET.get('plate', None)

    T,tree = read_sdss_plates()
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
    else:
        ra = req.GET.get('ra', None)
        dec = req.GET.get('dec', None)
        if ra is not None and dec is not None:
            ra = float(ra)
            dec = float(dec)
            im = survey.get_image_object(c)
            wcs = im.get_wcs()
            ok,x,y = wcs.radec2pixelxy(ra, dec)
            size = int(req.GET.get('size', 100))
            x = x-size/2
            y = y-size/2
            w = h = size
            rect = (x,y,w,h)

    imgurl   = my_reverse(req, 'image_data', args=[layer_name, ccd])
    dqurl    = my_reverse(req, 'dq_data', args=[layer_name, ccd])
    ivurl    = my_reverse(req, 'iv_data', args=[layer_name, ccd])
    imgstamp = my_reverse(req, 'image_stamp', args=[layer_name, ccd])
    ivstamp = my_reverse(req, 'iv_stamp', args=[layer_name, ccd])
    dqstamp = my_reverse(req, 'dq_stamp', args=[layer_name, ccd])
    outlierstamp = my_reverse(req, 'outlier_stamp', args=[layer_name, ccd])
    skystamp = my_reverse(req, 'sky_stamp', args=[layer_name, ccd])
    skysubstamp = my_reverse(req, 'skysub_stamp', args=[layer_name, ccd])
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
Observed MJD {c.mjd_obs:.3f}, {c.date_obs} {c.ut} UT<br/>
PROPID {c.propid}.  RA,Dec boresight {c.ra_bore:.4f}, {c.dec_bore:.4f}
<ul>
<li>image: <a href="{imgurl}">{ccd}</a>
{ooitext}</li>
<li>weight or inverse-variance: <a href="{ivurl}">{ccd}</a></li>
<li>data quality (flags): <a href="{dqurl}">{ccd}</a></li>
<li>outlier mask display: <a href="{outlierstamp}">{ccd}</a></li>
<li>sky model display: <a href="{skystamp}">{ccd}</a></li>
<li>sky-subtracted image display: <a href="{skysubstamp}">{ccd}</a></li>
</ul>
<div>Image (~raw, not sky-subtracted)<br/>
Mouse: <span id="image_coords"></span>  Click: <span id="image_click"></span></div><br/>
<svg version="1.1" baseProfile="full" xmlns="https://www.w3.org/2000/svg"
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
<div>Inverse-variance map<br/>
Mouse: <span id="iv_coords"></span>  Click: <span id="iv_click"></span></div><br/>
<svg version="1.1" baseProfile="full" xmlns="https://www.w3.org/2000/svg"
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
<div>Data quality map (not including outlier-masks)<br/>
Mouse: <span id="dq_coords"></span>  Click: <span id="dq_click"></span></div><br/>
<svg version="1.1" baseProfile="full" xmlns="https://www.w3.org/2000/svg"
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
           outlierstamp=outlierstamp, skystamp=skystamp, skysubstamp=skysubstamp,
           static=settings.STATIC_URL, scale=image_stamp_scale)

    #return HttpResponse(about, content_type='application/xhtml+xml')
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
        #print('Cut', len(ccds), 'to', np.sum(ccds.photometric), 'CCDs on photometric column')
        ccds.cut(ccds.photometric)

    return ccds

def format_jpl_url(req, ra, dec, ccd):
    jpl_url = my_reverse(req, jpl_lookup)
    return ('%s?ra=%.4f&dec=%.4f&date=%s&camera=%s' %
            (jpl_url, ra, dec, ccd.date_obs + ' ' + ccd.ut, ccd.camera.strip()))


def ccds_overlapping_html(req, ccds, layer, ra=None, dec=None, ccd_link=True,
                          img_url=None, dq_url=None, iv_url=None, img_ooi_url=None):
    jplstr = ''
    if ra is not None:
        jplstr = '<th>JPL</th>'

    # callbacks
    if img_url is None:
        def img_url(req, layer, ccd, ccdtag):
            return my_reverse(req, 'image_data', args=(layer, ccdtag))
    if img_ooi_url is None:
        def img_ooi_url(req, layer, ccd, ccdtag):
            return my_reverse(req, 'image_data', args=(layer, ccdtag)) + '?type=ooi'
    if dq_url is None:
        def dq_url(req, layer, ccd, ccdtag):
            return my_reverse(req, 'dq_data', args=(layer, ccdtag))
    if iv_url is None:
        def iv_url(req, layer, ccd, ccdtag):
            return my_reverse(req, 'iv_data', args=(layer, ccdtag))

    html = ['<table class="ccds"><thead><tr><th>name</th><th>exptime</th><th>seeing</th><th>propid</th><th>date</th><th>image</th><th>image (ooi)</th><th>weight map</th><th>data quality map</th>%s</tr></thead><tbody>' % jplstr]
    for ccd in ccds:
        ccdname = '%s %i %s %s' % (ccd.camera.strip(), ccd.expnum,
                                   ccd.ccdname.strip(), ccd.filter.strip())
        ccdtag = ccdname.replace(' ','-')

        #http://decaps.skymaps.info/release/data/files/EXPOSURES/DR1/c4d_160825_030845_ooi_g_v1.fits.fz

        imgurl = img_url(req, layer, ccd, ccdtag)
        dqurl  = dq_url(req, layer, ccd, ccdtag)
        ivurl  = iv_url(req, layer, ccd, ccdtag)
        imgooiurl = img_ooi_url(req, layer, ccd, ccdtag)
        ooitext = ''
        if '_oki_' in ccd.image_filename:
            ooitext = '<a href="%s">ooi</a>' % imgooiurl
        jplstr = ''
        if ra is not None:
            jplstr = '<td><a href="%s">JPL</a></td>' % format_jpl_url(req, ra, dec, ccd)
        if ccd_link:
            ccd_html = '<a href="%s">%s</a>' % (my_reverse(req, ccd_detail, args=(layer, ccdtag)), ccdname)
        else:
            ccd_html = ccdname
        
        html.append(('<tr><td>%s</td><td>%.1f</td><td>%.2f</td>' +
                     '<td>%s</td><td>%s</td><td><a href="%s">%s</a></td><td>%s</td><td><a href="%s">oow</a></td><td><a href="%s">ood</a></td>%s</tr>') % (
                         ccd_html,
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
    #survey = get_survey(layername)
    layer = get_layer(layername)
    survey = layer.survey

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
        size = min(500, size)
        size = size // 2

    W,H = size*2, size*2

    # This is the WCS of the image cutout we're going to make
    pixscale = 0.262 / 3600.
    wcs = Tan(*[float(x) for x in [
        ra, dec, size+0.5, size+0.5, -pixscale, 0., 0., pixscale, W, H]])

    nil,north = wcs.pixelxy2radec(size+0.5, H)
    nil,south = wcs.pixelxy2radec(size+0.5, 1)
    west,nil  = wcs.pixelxy2radec(1, size+0.5)
    east,nil  = wcs.pixelxy2radec(W, size+0.5)

    #print('Getting ccds_touching_wcs from', survey)
    #CCDs = survey.ccds_touching_wcs(wcs)
    #print('Getting ccds_touching_wcs from layername =', layername, 'obj =', layer)
    CCDs = layer.ccds_touching_box(north, south, east, west)
    debug(len(CCDs), 'CCDs')
    CCDs = touchup_ccds(CCDs, survey)

    #print('CCDs:', CCDs.columns())

    showcut = 'cut' in req.GET
    if not showcut:
        if 'ccd_cuts' in CCDs.get_columns():
            CCDs.cut(CCDs.ccd_cuts == 0)

    print('CCDs:', len(CCDs))
    print('filters:', CCDs.filter)
    print('layer bands:', list(layer.get_bands()))

            #print('Layer\'s bands:', layer.get_bands())
    # Drop Y band images
    #CCDs.cut(np.isin(CCDs.filter, ['g','r','i','z']))
    CCDs.cut(np.isin(CCDs.filter, list(layer.get_bands())))
    #print('After cutting on bands:', len(CCDs), 'CCDs')

    filterorder = dict(g=0, r=1, i=2, z=3)

    CCDs = CCDs[np.lexsort((CCDs.ccdname, CCDs.expnum,
                            [filterorder.get(f,f) for f in CCDs.filter]))]

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
        ccds.append((c, dim, x, y))

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

    # Swap in DR10 links for images where we no longer have the original CP images
    from collections import Counter
    swap = []
    for c,d,x,y in ccds:
        swap.append(not(os.path.exists(d.imgfn)))
    if any(swap):
        swap_layers = {'ls-dr8': 'ls-dr10-all',
                       'decals-dr7': 'ls-dr10-all',
                       'decals-dr5': 'ls-dr10-all',
                       'ls-dr67': 'ls-dr10-all',
        }
        for (c,d,x,y),s in zip(ccds,swap):
            if s:
                c.layer = swap_layers.get(layername, layername)

    from django.shortcuts import render

    ccds_list = []
    for i,(ccd,_,x,y) in enumerate(ccds):
        fn = ccd.image_filename.replace(settings.DATA_DIR + '/', '')
        ccdlayer = getattr(ccd, 'layer', layername)

        mydomain = None
        domains = settings.SUBDOMAINS
        if len(domains):
            mydomain = domains[i % len(domains)]

        contents = layer.get_exposure_contents(req, ccdlayer, int(ccd.expnum), ccd.ccdname.strip(),
                                               ccd, mydomain, ra, dec, int(size*2))

        expurl = layer.get_ccd_detail_url(req, ccdlayer, ccd.camera.strip(), int(ccd.expnum),
                                          ccd.ccdname.strip(), ccd, x, y, size)
        cutstr = ''
        if 'ccd_cuts' in ccd.get_columns():
            if ccd.ccd_cuts != 0:
                cutstr = ' <span style="color:red">(cut)</span>'

        expstr = '%s %s %i %s' % (ccd.camera.strip(), ccd.filter.strip(), int(ccd.expnum),
                                  ccd.ccdname.strip())
        if expurl is not None:
            expstr = '<a href="%s">%s</a>' % (expurl, expstr)

        ccdstr = '<br/>'.join([
            'CCD %s, %.1f sec (x,y ~ %i,%i) %s' % (expstr, ccd.exptime, x, y, cutstr),
            '<small>(%s [%i])</small>' % (fn, ccd.image_hdu),
            '<small>(observed %s @ %s = MJD %.6f)</small>' % (ccd.date_obs, ccd.ut, ccd.mjd_obs),
            '<small>(proposal id %s)</small>' % (ccd.propid),
            '<small><a href="%s">Look up in JPL Small Bodies database</a></small>' % (
                format_jpl_url(req, ra, dec, ccd)),
            '<small><a href="%s">Direct link to JPL query</a></small>' % (
                jpl_direct_url(ra, dec, ccd)),
        ])
        ccds_list.append((ccdstr,) + tuple(contents))
                      
    return render(req, 'exposures.html',
                  dict(ra=ra, dec=dec, ccds=ccds_list, name=layername, layer=layername,
                       drname=getattr(survey, 'drname', layername),
                       brick=brick, brickx=brickx, bricky=bricky, size=W,
                       showcut=showcut, has_tarball=layer.has_exposure_tarball()))

def jpl_direct_url(ra, dec, ccd):
    from astrometry.util.starutil_numpy import ra2hmsstring, dec2dmsstring

    date = ccd.date_obs + 'T' + ccd.ut
    date = date.replace(' ', 'T')
    date = date[:19]
    print('Date:', date)

    camera = ccd.camera.strip()
    # JPL's observer codes
    obs_code = {
        'decam': 'W84',
        '90prime': 'V00',
        'mosaic': '695',
        'suprimecam': 'T09',
    }[camera]

    rastr = ra2hmsstring(ra, separator='-')
    decstr = dec2dmsstring(dec, separator='-')
    if decstr.startswith('+'):
        decstr = decstr[1:]
    if decstr.startswith('-'):
        decstr = 'M' + decstr[1:]

    # search radius in degrees
    r = '%.4f' % (10./3600)

    url = ('https://ssd-api.jpl.nasa.gov/sb_ident.api?two-pass=true&suppress-first-pass=true&'
           + 'req-elem=false&'
           + 'mpc-code=%s&' % obs_code
           + 'obs-time=%s&' % date
           + 'fov-ra-center=%s&' % rastr
           + 'fov-dec-center=%s&' % decstr
           + 'fov-ra-hwidth=%s&' % r
           + 'fov-dec-hwidth=%s' % r
           )
    print('URL', url)
    return url

def jpl_lookup(req):
    import sys

    import requests
    from astrometry.util.starutil_numpy import ra2hmsstring, dec2dmsstring

    date = req.GET.get('date')
    ra = float(req.GET.get('ra'))
    dec = float(req.GET.get('dec'))
    camera = req.GET.get('camera')

    # JPL's observer codes
    obs_code = {
        'decam': 'W84',
        '90prime': 'V00',
        'mosaic': '695',
    }[camera]

    rastr = ra2hmsstring(ra, separator='-')
    decstr = dec2dmsstring(dec, separator='-')
    if decstr.startswith('+'):
        decstr = decstr[1:]
    if decstr.startswith('-'):
        decstr = 'M' + decstr[1:]

    date = date.replace(' ', 'T')
    date = date[:19]
    print('Date:', date)
    # search radius in degrees
    r = '%.4f' % (10./3600)

    url = ('https://ssd-api.jpl.nasa.gov/sb_ident.api?two-pass=true&suppress-first-pass=true&'
           + 'req-elem=false&'
           + 'mpc-code=%s&' % obs_code
           + 'obs-time=%s&' % date
           + 'fov-ra-center=%s&' % rastr
           + 'fov-dec-center=%s&' % decstr
           + 'fov-ra-hwidth=%s&' % r
           + 'fov-dec-hwidth=%s' % r
           )
    print('URL', url)
    r = requests.get(url)

    print('Text result:', r.text)
    j = r.json()
    print('Json result:', j)
    warn = j.get('warning')
    if warn:
        return HttpResponse('<html><body><p>Result: warning: %s</p><p>Full response: <pre>%s</pre></p></body></html>' % (warn, r.text))
    fields = j['fields_second']
    data = j['data_second_pass']

    # Add link to objects.
    import re
    # 44505 (1998 XT38) --> 44505
    r1 = re.compile('(?P<num>\d+) \([\w\s]+\)')
    for i,d in enumerate(data):
        name = d[0]
        #https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=44505
        m = r1.match(name)
        if m is not None:
            d_url = 'https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=' + m['num']
            data[i][0] = '<a href="%s">%s</a>' % (d_url, name)
    
    from django.shortcuts import render
    return render(req, 'jpl-small-body-results.html',
                  { 'fields': fields,
                    'data': data,
                    'json': j })
    #return HttpResponse(r.text)

    
    #sb-kind=a&mpc-code=568&obs-time=2021-02-09_00:00:00&mag-required=true&two-pass=true&suppress-first-pass=true&req-elem=false&vmag-lim=20&fov-ra-lim=10-10-00%2C10-20-00&fov-dec-lim=10-00-00,10-30-00


    
    # latlongs = dict(decam=dict(lon='70.81489', lon_u='W',
    #                            lat='30.16606', lat_u='S',
    #                            alt='2215.0', alt_u='m'),
    #                 mosaic=dict(lon='111.6003', lon_u='W',
    #                             lat = '31.9634', lat_u='N',
    #                             alt='2120.0', alt_u='m'))
    # latlongs.update({'90prime': dict(lon='111.6', lon_u='W',
    #                                  lat='31.98', lat_u='N',
    #                                  alt='2120.0', alt_u='m')})
    # 
    # latlongargs = latlongs[camera]
    # 
    # 
    # # '2016-03-01 00:42'
    # s = requests.Session()
    # r = s.get('https://ssd.jpl.nasa.gov/sbfind.cgi')
    # #r2 = s.get('https://ssd.jpl.nasa.gov/sbfind.cgi?s_time=1')
    # print('JPL lookup: setting date', date)
    # r3 = s.post('https://ssd.jpl.nasa.gov/sbfind.cgi', data=dict(obs_time=date, time_zone='0', check_time='Use Specified Time'))
    # print('Reply code:', r3.status_code)
    # #r4 = s.get('https://ssd.jpl.nasa.gov/sbfind.cgi?s_loc=1')
    # print('JPL lookup: setting location', latlongargs)
    # latlongargs.update(s_pos="Use Specified Coordinates")
    # r5 = s.post('https://ssd.jpl.nasa.gov/sbfind.cgi', data=latlongargs)
    # print('Reply code:', r5.status_code)
    # #r6 = s.get('https://ssd.jpl.nasa.gov/sbfind.cgi?s_region=1')
    # print('JPL lookup: setting RA,Dec', (hms, dms))
    # r7 = s.post('https://ssd.jpl.nasa.gov/sbfind.cgi', data=dict(ra_1=hms, dec_1=dms,
    #                                                              ra_2='w0 0 45', dec_2='w0 0 45', sys='J2000', check_region_1="Use Specified R.A./Dec. Region"))
    # print('Reply code:', r7.status_code)
    # #r8 = s.get('https://ssd.jpl.nasa.gov/sbfind.cgi?s_constraint=1')
    # print('JPL lookup: clearing mag limit')
    # r9 = s.post('https://ssd.jpl.nasa.gov/sbfind.cgi', data=dict(group='all', limit='1000', mag_limit='', mag_required='yes', two_pass='yes', check_constraints="Use Specified Settings"))
    # print('Reply code:', r9.status_code)
    # print('JPL lookup: submitting search')
    # r10 = s.post('https://ssd.jpl.nasa.gov/sbfind.cgi', data=dict(search="Find Objects"))
    # txt = r10.text
    # txt = txt.replace('<head>', '<head><base href="https://ssd.jpl.nasa.gov/">')
    # return HttpResponse(txt)

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

    # Try reading sky models
    has_sky = True
    try:
        primhdr = im.read_image_primary_header()
        imghdr = im.read_image_header()
        sky = im.read_sky_model(primhdr=primhdr, imghdr=imghdr, **trargs)
    except Exception as e:
        print('Failed to read sky model:', e)
        #import traceback
        #traceback.print_exc()
        trargs.update(readsky=False)
        has_sky = False

        from tractor.basics import NanoMaggies
        zpscale = NanoMaggies.zeropointToScale(im.ccdzpt)
        hacksky = ccd.ccdskycounts * im.exptime / zpscale

    bandindex = dict(g=2, r=1, i=0, z=0, Y=0).get(im.band, -1)
    #rgbkw = dict(coadd_bw = True)
    rgbkw = {}

    if kind == 'image':
        # HACK for some DR5 images...
        if im.sig1 == 0:
            im.sig1 = 1.

        tim = im.get_tractor_image(invvar=False, dq=False, **trargs)
        from legacypipe.survey import get_rgb
        #print('im=',im)
        #print('tim=',tim)
        # hack a sky sub
        if not has_sky:
            tim.data -= hacksky
        rgb = get_rgb([tim.data], [im.band], **rgbkw) #, mnmx=(-1,100.), arcsinh=1.)
        if bandindex >= 0:
            img = rgb[:,:,bandindex]
        else:
            img = np.sum(rgb, axis=2)
        kwa.update(vmin=0, vmax=1)

    elif kind == 'weight':
        tim = im.get_tractor_image(pixels=False, dq=False, invvar=True, **trargs)
        if tim is None:
            # eg, all-zero invvar
            img = np.zeros((size,size), np.float32)
            padleft = padright = padtop = padbottom = 0
        else:
            img = tim.getInvvar()
        kwa.update(vmin=0)

    elif kind == 'weightedimage':
        tim = im.get_tractor_image(dq=False, invvar=True, **trargs)
        if tim is None:
            # eg, all-zero invvar
            img = np.zeros((size,size), np.float32)
            padleft = padright = padtop = padbottom = 0
        else:
            if not has_sky:
                tim.data -= hacksky
            img = tim.data * (tim.inverr > 0)
        from legacypipe.survey import get_rgb
        rgb = get_rgb([img], [im.band], **rgbkw) #, mnmx=(-1,100.), arcsinh=1.)
        if bandindex >= 0:
            img = rgb[:,:,bandindex]
        else:
            img = np.sum(rgb, axis=2)
        #img = rgb[:,:,bandindex]
        kwa.update(vmin=0, vmax=1)

    elif kind == 'dq':
        # HACK for some DR5 images...
        if im.sig1 == 0:
            im.sig1 = 1.
        tim = im.get_tractor_image(pixels=False, dq=True, invvar=False, **trargs)
        if tim is None:
            img = np.zeros((size,size), np.int16)
            padleft = padright = padtop = padbottom = 0
        else:
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

def sanitize_header(hdr):
    import fitsio
    ### HACK -- sanitize header due to
    # https://github.com/esheldon/fitsio/issues/357
    outhdr = fitsio.FITSHDR()
    for r in hdr.records():
        key = r.get('name','')
        if key is not None:
            if '[' in key or ']' in key:
                continue

        outhdr.add_record(r)
    return outhdr

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

    hdr = sanitize_header(hdr)

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

    hdr = sanitize_header(hdr)

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

    hdr = sanitize_header(hdr)

    os.unlink(tmpfn)
    fits = fitsio.FITS(tmpfn, 'rw')
    fits.write(None, header=primhdr, clobber=True)
    fits.write(pix,  header=hdr)
    fits.close()
    return send_file(tmpfn, 'image/fits', unlink=True, filename='iv-%s.fits.gz' % ccd)

def image_stamp(req, surveyname, ccd, iv=False, dq=False, sky=False, skysub=False,
                outliers=False):
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

    if skysub:
        tim = im.get_tractor_image(gaussPsf=True, hybridPsf=False,
                                   readsky=True, subsky=True,
                                   dq=False, invvar=False, pixels=True,
                                   trim_edges=False, nanomaggies=False)
        pix = tim.getImage()
    elif sky:
        primhdr = im.read_image_primary_header()
        imghdr = im.read_image_header()
        skymod = im.read_sky_model(primhdr=primhdr, imghdr=imghdr)
        skyimg = np.zeros((im.height, im.width), np.float32)
        skymod.addTo(skyimg)
        pix = skyimg
    elif outliers:
        from legacypipe.survey import bricks_touching_wcs
        from legacypipe.outliers import read_outlier_mask_file
        tim = im.get_tractor_image(gaussPsf=True, hybridPsf=False,
                                   readsky=False, subsky=False,
                                   dq=False, invvar=False, pixels=False,
                                   trim_edges=False, nanomaggies=False)
        tim.dq = np.zeros(tim.shape, np.int16)
        posneg_mask = np.zeros(tim.shape, np.uint8)
        chipwcs = tim.subwcs
        outlier_bricks = bricks_touching_wcs(chipwcs, survey=survey)
        for b in outlier_bricks:
            print('Reading outlier mask for brick', b.brickname,
                  ':', survey.find_file('outliers_mask', brick=b.brickname, output=False))
            ok = read_outlier_mask_file(survey, [tim], b.brickname, pos_neg_mask=posneg_mask,
                                        subimage=False, output=False)
        # OUTLIER_POS = 1
        # OUTLIER_NEG = 2
        # Create an image that can be used with the "RdBu' (red-white-blue) colormap,
        # 0 = NEG, 1 = nil, 2=POS
        # ie, posneg_mask value 0 -> 1
        #                       1 -> 2
        #                       2 -> 0
        #                       3 -> ?? 2?
        pixmap = np.array([1, 2, 0, 2])
        pix = pixmap[posneg_mask]

    kwa = dict(origin='lower')

    cmap = 'gray'
    if iv:
        fn = fn.replace('_ooi_', '_oow_')
        cmap = 'hot'
    elif dq:
        fn = fn.replace('_ooi_', '_ood_')
        cmap = 'tab10'
    elif skysub:
        fn = None
    elif sky:
        fn = None
    elif outliers:
        fn = None
        cmap = 'RdBu'

    if fn is not None:
        print('Reading', fn)
        pix = fitsio.read(fn, ext=c.image_hdu)
    H,W = pix.shape

    # BIN
    scale = 4
    sw,sh = W//scale, H//scale

    if dq:
        # Assume DQ codes (not bitmask)
        out = np.zeros((sh,sw), np.uint8)
        # Scale down, taking the max per block
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
        elif sky:
            mn,mx = None,None
        elif outliers:
            mn = 0
            mx = 2
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

def sky_stamp(req, surveyname, ccd):
    return image_stamp(req, surveyname, ccd, sky=True)
def skysub_stamp(req, surveyname, ccd):
    return image_stamp(req, surveyname, ccd, skysub=True)
def outlier_stamp(req, surveyname, ccd):
    return image_stamp(req, surveyname, ccd, outliers=True)


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

    # if name == 'cfis-r':
    #     layer = CFISLayer('cfis-r', 'R')
    # elif name == 'cfis-u':
    #     layer = CFISLayer('cfis-u', 'U')
    # elif name == 'cfis-dr2':
    #     layer = CFISLayer('cfis-dr2', '')
    # elif name == 'cfis-dr3-r':
    #     layer = CFISLayer('cfis-dr3-r', 'R')
    # elif name == 'cfis-dr3-u':
    #     layer = CFISLayer('cfis-dr3-u', 'U')
    # elif name == 'cfis-dr3-u':
    #     layer = CFISLayer('cfis-dr3-u', 'U')

    if name == 'pandas':
        layer = PandasLayer('pandas')

    elif name == 'ztf':
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
        image = DecapsLayer('decaps', 'image', survey)
        model = DecapsLayer('decaps-model', 'model', survey)
        resid = DecapsResidLayer(image, model,
                                  'decaps-resid', 'resid', survey, drname='decaps')
        layers['decaps'] = image
        layers['decaps-model'] = model
        layers['decaps-resid'] = resid
        layer = layers[name]

    elif name in ['decaps2', 'decaps2-model', 'decaps2-resid']:
        survey = get_survey('decaps2')
        image = Decaps2Layer('decaps2', 'image', survey)
        model = Decaps2Layer('decaps2-model', 'model', survey)
        resid = Decaps2ResidLayer(image, model,
                                  'decaps2-resid', 'resid', survey, drname='decaps2')
        layers['decaps2'] = image
        layers['decaps2-model'] = model
        layers['decaps2-resid'] = resid
        layer = layers[name]

    elif name in ['decaps2-riy', 'decaps2-model-riy', 'decaps2-resid-riy']:
        bands = 'riY'
        survey = get_survey('decaps2')
        image = Decaps2Layer('decaps2', 'image', survey)
        image.bands = bands
        image.tiledir += '-riy'
        model = Decaps2Layer('decaps2-model', 'model', survey)
        model.bands = bands
        model.tiledir += '-riy'
        resid = Decaps2ResidLayer(image, model,
                                  'decaps2-resid', 'resid', survey, drname='decaps2')
        resid.bands = bands
        resid.tiledir += '-riy'
        layers['decaps2-riy'] = image
        layers['decaps2-model-riy'] = model
        layers['decaps2-resid-riy'] = resid
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
    elif name == 'unwise-neo7':
        layer = RebrickedUnwise('unwise-neo7',
                                os.path.join(settings.DATA_DIR, 'unwise-neo7'))

    elif name == 'unwise-neo7-mask':
        layer = UnwiseMask('unwise-neo7-mask',
                           os.path.join(settings.DATA_DIR, 'unwise-neo7'))
        
    elif name == 'unwise-w3w4':
        layer = UnwiseW3W4('unwise-w3w4', os.path.join(settings.DATA_DIR, 'unwise-w3w4'))

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

    elif name == 'hsc-dr3':
        layer = HscLayer('hsc-dr3')

    elif name == 'wiro-C':
        survey = get_survey('wiro-C')
        layer = WiroCLayer('wiro-C', 'image', survey)

    elif name == 'wiro-D':
        survey = get_survey('wiro-D')
        layer = WiroDLayer('wiro-D', 'image', survey)

    elif name in [
            'cfht-cosmos-cahk']:
        basename = name
        bands = ['CaHK']
        survey = get_survey(basename)
        image = SuprimeIALayer(basename, 'image', survey, bands=bands)
        layers[basename] = image
        layer = image
    elif name in [
            'suprime-L427', 'suprime-L427-model', 'suprime-L427-resid',
            'suprime-L464', 'suprime-L464-model', 'suprime-L464-resid',
            'suprime-L484', 'suprime-L484-model', 'suprime-L484-resid',
            'suprime-L505', 'suprime-L505-model', 'suprime-L505-resid',
            'suprime-L527', 'suprime-L527-model', 'suprime-L527-resid',
    ]:
        basename = name.replace('-model','').replace('-resid','')
        bands = ['I-A-' + name.split('-')[1]]
        survey = get_survey(basename)
        image = SuprimeIALayer(basename, 'image', survey, bands=bands)
        model = SuprimeIALayer(basename, 'model', survey, bands=bands)
        resid = SuprimeIAResidLayer(image, model, basename, 'resid', survey, bands=bands)
        layers[basename] = image
        layers[basename + '-model'] = model
        layers[basename + '-resid'] = resid
        layer = layers[name]

    elif name in [
        'suprime-ia-v1', 'suprime-ia-v1-model', 'suprime-ia-v1-resid',
    ]:
        basename = name.replace('-model','').replace('-resid','')
        bands = ['I-A-L%i' % f for f in [427,464,484,505,527]]
        survey = get_survey(basename)
        image = SuprimeAllIALayer(basename, 'image', survey, bands=bands)
        model = SuprimeAllIALayer(basename, 'model', survey, bands=bands)
        resid = SuprimeAllIAResidLayer(image, model, basename, 'resid', survey, bands=bands)
        layers[basename] = image
        layers[basename + '-model'] = model
        layers[basename + '-resid'] = resid
        layer = layers[name]

    elif name == 'merian-n540':
        hsc = get_layer('hsc-dr2')
        layer = MerianLayer('merian', hsc)
    elif name == 'merian-n708':
        hsc = get_layer('hsc-dr2')
        layer = MerianLayer('merian', hsc)
        layer.bands = ['g', 'N708', 'z']

    elif name in ['ibis', 'ibis-color', 'ibis-color-ls', 'ibis-m411', 'ibis-m464']:
        other = None
        if name == 'ibis-color':
            other = get_layer('hsc-dr3')
        elif name == 'ibis-color-ls':
            other = get_layer('ls-dr10-south')

        layer = IbisColorLayer('ibis', other)

        if name == 'ibis-color-ls':
            layer.other_zpt = 22.5
            layer.r_scale = 5.0

        if name == 'ibis-m411':
            layer.bands = ['M411']
            layer.rgb_plane = 2
        elif name == 'ibis-m464':
            layer.bands = ['M464']
            layer.rgb_plane = 1

    elif name in ['ibis-3', 'ibis-3-wide']:
        survey = get_survey(name)
        layer = Ibis3Layer(name, 'image', survey)

    elif name in ['ibis-3-m411', 'ibis-3-m438', 'ibis-3-m464', 'ibis-3-m490', 'ibis-3-m517',]:
        survey = get_survey('ibis-3')
        layer = Ibis3Layer('ibis-3', 'image', survey)
        band = name[-4:].upper()
        layer.bands = [band]
        layer.rgb_plane = 2

    elif name in ['ibis-3-wide-m411', 'ibis-3-wide-m438', 'ibis-3-wide-m464',
                  'ibis-3-wide-m490', 'ibis-3-wide-m517',]:
        survey = get_survey('ibis-3-wide')
        layer = Ibis3Layer('ibis-3-wide', 'image', survey)
        band = name[-4:].upper()
        layer.bands = [band]
        layer.rgb_plane = 2
        layer.tiledir = os.path.join(settings.DATA_DIR, 'tiles', name)

    elif name == 'ls-dr10-segmentation':
        dr10 = get_layer('ls-dr10-model')
        layer = LsSegmentationLayer(dr10)

    elif name == 'outliers-ast':
        basename = 'asteroids-i'
        survey = get_survey(basename)
        layer = OutliersLayer(basename, 'outliers', survey)
    elif name == 'asteroids-i':
        basename = 'asteroids-i'
        survey = get_survey(basename)
        layer = AsteroidsLayer(basename, 'image', survey)

    elif name in ['ls-dr10', 'ls-dr10-model', 'ls-dr10-resid',
                  'ls-dr10-grz', 'ls-dr10-model-grz', 'ls-dr10-resid-grz',
                  'ls-dr10-gri',]:
        is_grz = name.endswith('-grz')
        is_gri = name.endswith('-gri')
        if is_grz:
            name = name.replace('-grz','')
            grzpart = '-grz'
            bands = 'grz'
        elif is_gri:
            name = name.replace('-gri','')
            grzpart = '-gri'
            bands = 'gri'
        else:
            grzpart = ''
            bands = 'griz'

        # suff: -model, -resid
        suff = name.replace('ls-dr10', '')
        north = get_layer('ls-dr9-north' + suff)
        south = get_layer('ls-dr10-south' + suff + grzpart)
        layer = LegacySurveySplitLayer(name + grzpart, north, south, 32.375, bottom_bands=bands)
        layer.bands = 'griz'
        layer.drname = 'Legacy Surveys DR10'
        # "name" is going to be used to set the "layer" cache below!
        name = name + grzpart

    elif name in ['ls-dr10-south', 'ls-dr10-south-model', 'ls-dr10-south-resid',
                  'ls-dr10-south-grz', 'ls-dr10-south-model-grz', 'ls-dr10-south-resid-grz',
                  'ls-dr10-south-gri']:
        if name.endswith('-grz'):
            bands = 'grz'
            grzpart = '-grz'
        elif name.endswith('-gri'):
            bands = 'gri'
            grzpart = '-gri'
        else:
            bands = 'griz'
            grzpart = ''
        basename = 'ls-dr10-south'
        survey = get_survey(basename)
        image = LsDr10Layer(basename + grzpart, 'image', survey, bands=bands,
                            drname=basename)
        model = LsDr10ModelLayer(basename + '-model' + grzpart, 'model', survey, bands=bands,
                                 drname=basename)
        resid = LsDr10ResidLayer(image, model, basename + '-resid' + grzpart, 'resid', survey, bands=bands,
                                 drname=basename)
        layers[basename            + grzpart] = image
        layers[basename + '-model' + grzpart] = model
        layers[basename + '-resid' + grzpart] = resid
        layer = layers[name]

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

def any_cat_table(req, name, **kwargs):
    name = clean_layer_name(name)
    layer = get_layer(name)
    if layer is None:
        return HttpResponse('no such layer')
    bb = get_radec_bbox(req)
    if bb is None:
        return HttpResponse('no ra,dec bbox')
    ralo,rahi,declo,dechi = bb
    brick = req.GET.get('brick', None)
    objid = req.GET.get('objid', None)
    if objid is not None:
        try:
            objid = int(objid)
        except:
            objid = None
    return layer.get_catalog_table(req, ralo, rahi, declo, dechi,
                                   brick=brick, objid=objid)

def get_radec_bbox(req):
    #print('get_radec_bbox()')
    try:
        ralo = float(req.GET.get('ralo'))
        rahi = float(req.GET.get('rahi'))
        declo = float(req.GET.get('declo'))
        dechi = float(req.GET.get('dechi'))
        #print('get_radec_bbox() ->', ralo,rahi,declo,dechi)
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
    flip = 'flip' in req.GET
    wcs = Tan(*args)
    pixscale = wcs.pixel_scale()
    x = y = 0

    layer = req.layer
    scale = int(np.floor(np.log2(pixscale / layer.pixscale)))
    scale = np.clip(scale, 0, layer.maxscale)
    zoom = 0

    imgs = layer.render_into_wcs(wcs, zoom, x, y, general_wcs=True, scale=scale)
    if imgs is None:
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(settings.STATIC_URL + 'blank.jpg')

    # FLIP VERTICAL AXIS?!
    if flip:
        flipimgs = []
        for img in imgs:
            if img is not None:
                flipimgs.append(np.flipud(img))
            else:
                flipimgs.append(img)
        imgs = flipimgs

    bands = layer.get_bands()
    rgb = layer.get_rgb(imgs, bands)

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

    # import numpy as np
    # c = get_layer('cfis-r')
    # B = c.get_bricks_for_scale(1)
    # print(len(B), 'bricks for scale', 1)
    # B.cut(B.dec > 29)
    # B.cut(np.lexsort((B.ra, B.dec)))
    # b1 = B[0]
    # b2 = B[1]
    # print('Bricks', b1.brickname, b2.brickname)
    # band = 'R'
    # wcs1 = c.get_scaled_wcs(b1, band, 1)
    # wcs2 = c.get_scaled_wcs(b2, band, 1)
    # print('WCS', wcs1, wcs2)
    # bounds = wcs1.radec_bounds()
    # print('WCS1 RA,Dec bounds', bounds)
    # bounds = wcs2.radec_bounds()
    # print('WCS2 RA,Dec bounds', bounds)
    # sys.exit(0)
    
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
    #r = c.get('/manga/1/cat.json?ralo=194.4925&rahi=194.5544&declo=29.0022&dechi=29.0325')
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
    #r = c.get('/cfis-r/1/14/16383/6759.jpg')
    #r = c.get('/cfis-r/1/15/14107/13466.jpg')
    #r = c.get('/cfis-r/1/14/7032/6732.jpg')
    #r = c.get('/cfis-r/1/13/3518/3368.jpg')
    #r = c.get('/cfis-u/1/14/16383/8214.jpg')
    #r = c.get('/cfis-dr2/1/cat.json?ralo=0.0988&rahi=0.2226&declo=-0.3704&dechi=-0.3014#IC 3478')
    #r = c.get('/cfis-dr2/1/cat.json?ralo=359.9691&rahi=0.0309&declo=31.9854&dechi=32.0147')
    #r = c.get('/cfis-dr3-r/1/6/21/28.jpg')
    #r = c.get('/cfis-dr3-r/1/6/20/26.jpg')
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
    #r = c.get('/targets-dr9-sv1-dark/1/cat.json?ralo=119.8540&rahi=120.3490&declo=37.6292&dechi=37.8477')
    #r = c.get('/targets-dr9-sv1-dark/1/cat.json?ralo=119.8828&rahi=120.3779&declo=37.6129&dechi=37.8315')
    #r = c.get('/ls-dr9-south/1/6/60/26.jpg')
    #r = c.get('/?layer=ls-dr9&zoom=12&tile=80256&fiber=4091')
    #r = c.get('/ls-dr9/1/3/1/3.jpg')
    #r = c.get('/')
    #r = c.get('/ls-dr9/1/5/0/12.jpg')
    #r = c.get('/namequery/?obj=TILE%2080254')
    #r = c.get('/targets-dr9-sv1-dark/1/cat.json?ralo=18.1525&rahi=18.6476&declo=28.2182&dechi=28.4614')
    #r = c.get('/cutout.jpg?ra=182.5248&dec=18.5415&layer=ls-dr9&pixscale=1.00')
    #r = c.get('/gaia-edr3/1/cat.json?ralo=200.8723&rahi=201.3674&declo=13.9584&dechi=14.2264')
    #r = c.get('/exposure_panels/mzls+bass-dr6/75120132/CCD1/?ra=230.6465&dec=56.2721&size=100')
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
    #r = c.get('/targets-dr9-sv3-dark/1/cat.json?ralo=349.2859&rahi=349.8304&declo=10.1487&dechi=10.4476#NGC 3716')
    #r = c.get('/ls-dr9.1.1-model/1/13/4767/4044.jpg')
    #r = c.get('/ls-dr9.1.1-model/1/12/2383/2022.jpg')
    #r = c.get('/ls-dr9.1.1-resid/1/12/2374/2020.jpg')
    #r = c.get('/targets-dr9-sv3-sec-dark/1/cat.json?ralo=149.7358&rahi=150.2803&declo=2.0732&dechi=2.3768')
    #r = c.get('/targets-dr9-sv3-sec-dark/1/cat.json?ralo=149.7358&rahi=150.2803&declo=2.0732&dechi=2.3768')
    #r = c.get('/ls-dr9-south/1/15/27206/20760.jpg')
    #r = c.get('/ls-dr9-south/1/12/3402/2596.jpg')
    #r = c.get('/ls-dr9-south/1/4/12/10.jpg')
    #r = c.get('/ls-dr9-south/1/5/26/19.jpg')
    #r = c.get('/ls-dr9-south/1/6/52/38.jpg')
    #r = c.get('/exposure_panels/decals-dr5/316739/N11/?ra=221.8517&dec=-7.6426&size=100')
    #r = c.get('/exposure_panels/decals-dr5/316741/N11/?ra=221.8520&dec=-7.6426&size=100&kind=dq')
    #r = c.get('/ls-dr9.1.1-model/1/13/4767/4044.jpg')
    #r = c.get('/ls-dr9.1.1-model/1/12/2383/2022.jpg')
    #r = c.get('/ls-dr9.1.1-resid/1/12/2374/2020.jpg')
    #r = c.get('/targets-dr9-sv3-sec-dark/1/cat.json?ralo=149.7358&rahi=150.2803&declo=2.0732&dechi=2.3768')
    #r = c.get('/?zoom=15&targetid=39627788403084375')
    #r = c.get('/sga/1/cat.json?ralo=184.8415&rahi=185.3366&declo=25.4764&dechi=25.7223')
    #r = c.get('/desi-spec-daily/1/cat.json?ralo=10.2550&rahi=10.2890&declo=21.2163&dechi=21.2337')
    #r = c.get('/decaps-model/2/14/10246/10688.jpg')
    #r = c.get('/sga/1/cat.json?ralo=184.8415&rahi=185.3366&declo=25.4764&dechi=25.7223')
    #r = c.get('/ccd/ls-dr9.1.1/decam-166877-S6.xhtml?ra=152.3613&dec=0.2671')
    #r = c.get('/outliers-ast/1/14/9557/8044.jpg')
    #r = c.get('/asteroids-i/1/15/19108/16061.jpg')
    #r = c.get('/exposures/?ra=150.0452&dec=3.5275&layer=asteroids-i')
    #r = c.get('/exposure_panels/asteroids-i/959877/S17/?ra=150.0452&dec=3.5275&size=100')
    #r = c.get('/jpl_lookup?ra=150.0452&dec=3.5275&date=2021-05-15 01:35:16.197199&camera=decam')
    #r = c.get('/cutout.jpg?ra=39.7001&dec=2.2170&layer=ls-dr9&pixscale=1.00&sga=')
    #r = c.get('/cutout.jpg?ra=39.7001&dec=2.2170&layer=ls-dr9&pixscale=1.00&sga-parent=')
    #r = c.get('/jpl_lookup?ra=138.9834&dec=17.8431&date=2016-01-15%2005:51:44.149541&camera=decam')
    #r = c.get('/ls-dr9-south/1/12/1995/1752.jpg')
    #r = c.get('/pandas/1/14/16363/6307.jpg')
    #r = c.get('/pandas/1/14/15897/6126.jpg')
    #r = c.get('/pandas/1/14/15903/6126.jpg')
    # tile 10489 / observed 20220324
    #r = c.get('/desi-tile/1/cat.json?ralo=216.5628&rahi=217.1074&declo=0.8761&dechi=1.1755&tile=10489')
    #r = c.get('/desi-spec-daily/1/cat.json?ralo=141.9359&rahi=142.0720&declo=30.0046&dechi=30.0694')
    #r = c.get('/?targetid=39627733692582430')
    #r = c.get('/pandas/1/13/8184/3174.jpg')
    #r = c.get('/decaps2/2/14/8191/11625.jpg')
    #r = c.get('/decaps2/2/13/4095/5812.jpg') # native
    #r = c.get('/decaps2/2/12/2047/2906.jpg') # s1
    #r = c.get('/decaps2/2/12/1023/1453.jpg')
    #r = c.get('/decaps2/2/12/2048/2905.jpg')
    #r = c.get('/decaps2-model/2/14/8230/12122.jpg')
    #r = c.get('/ls-dr10a/1/13/5233/4095.jpg')
    #r = c.get('/ls-dr10a/1/14/10467/8191.jpg')
    #r = c.get('/cutout.jpg?ra=194.7876&dec=-63.1429&layer=decaps2&pixscale=64')
    #r = c.get('/cutout.jpg?ra=194.7876&dec=-63.1429&layer=decaps2&pixscale=32&size=512')
    #r = c.get('/decaps2-riy/2/14/7530/11896.jpg')

    settings.READ_ONLY_BASEDIR = True

    #r = c.get('/decaps2/2/14/12110/9411.jpg')
    #r = c.get('/decaps2/2/13/6052/4719.jpg')
    #r = c.get('/decaps2/2/13/2415/5074.jpg')
    #r = c.get('/decaps2/2/12/1207/2536.jpg')
    #r = c.get('/decaps2-model/2/13/2415/5074.jpg')
    #r = c.get('/decaps2-model/2/12/1207/2536.jpg')
    #r = c.get('/decaps2-model/2/12/1207/2536.jpg')
    #r = c.get('/decaps2-resid-riy/1/2/2/2.jpg')
    #r = c.get('/')
    #r = c.get('/vlass1.2/1/9/261/223.jpg')
    #r = c.get('/vlass1.2/1/10/526/447.jpg')
    #r = c.get('/vlass1.2/1/13/4193/3581.jpg')
    #r = c.get('/cutout.fits?ra=46.8323&dec=-62.4296&layer=ls-dr9&pixscale=1.00')
    #r = c.get('/desi-tile/1/cat.json?ralo=22.8159&rahi=24.7961&declo=30.3444&dechi=31.2786&tile=3371')
    #r = c.get('/targets-dr9-main-dark/1/cat.json?ralo=359.9755&rahi=0.0374&declo=-9.5112&dechi=-9.4776')
    #r = c.get('/desi-spec-daily/1/cat.json?ralo=359.9755&rahi=0.0374&declo=-9.5112&dechi=-9.4776')

    #r = c.get('/vlass1.2/1/13/4193/3581.jpg')
    #r = c.get('/cutout.fits?ra=46.8323&dec=-62.4296&layer=ls-dr9&pixscale=1.00')
    #r = c.get('/cutout.fits?ra=46.8323&dec=-62.4296&layer=ls-dr9&pixscale=1.00')
    #r = c.get('/decaps2/2/14/6039/12119.jpg')
    #r = c.get('/decaps2/2/13/3018/6058.jpg')
    #r = c.get('/decaps2/2/12/1509/3028.jpg')
    #r = c.get('/decaps2/2/11/754/1514.jpg')
    #r = c.get('/ls-dr10/1/14/979/8573.jpg')
    #r = c.get('/usercatalog/1/cat.json?ralo=104.1755&rahi=104.4230&declo=20.3734&dechi=20.5008&cat=tmp02tajgo8')
    #r = c.get('/cutout.jpg?ra=91.1268&dec=-66.6530&layer=unwise-w3w4&pixscale=2.75&size=500')
    #r = c.get('/exposures/?ra=229.9982&dec=1.8043&layer=decals-dr7')
    #r = c.get('/exposure_panels/ls-dr9-south-all/449377/S29/?ra=229.9982&dec=1.8043&size=100')
    #r = c.get('/image-stamp/ls-dr8-south/decam-569657-S22.jpg')
    #r = c.get('/masks-dr9/1/cat.json?ralo=349.1639&rahi=349.4361&declo=-6.9862&dechi=-6.8378')
    #r = c.get('/ps1/1/14/10654/7197.jpg')
    #r = c.get('/data-for-radec/?ra=251.0332&dec=11.3582&layer=ls-dr9&ralo=251.0223&rahi=251.0428&declo=11.3480&dechi=11.3676')
    #r = c.get('/cutout.fits?ra=251.0332&dec=11.3582&layer=ls-dr9-south&subimage')
    #r = c.get('/ls-dr10-grz/1/7/103/61.jpg')
    #r = c.get('/ls-dr10-grz/1/7/115/58.jpg')
    #r = c.get('/ls-dr10-grz/1/3/7/3.jpg')
    #r = c.get('/ls-dr10-resid/1/13/6433/4792.jpg')
    #r = c.get('/ls-dr9-resid/1/13/6433/4792.jpg')
    #r = c.get('/ls-dr10-south-model/1/6/58/26.jpg')
    #r = c.get('/ls-dr10-south-grz/1/12/1353/1658.jpg')
    #r = c.get('/ls-dr10-south-model-grz/1/12/1353/1658.jpg')
    #r = c.get('/ls-dr10-south-model/1/12/1353/1658.jpg')
    #r = c.get('/data-for-radec/?ra=339.9781&dec=-16.1471&layer=ls-dr10&ralo=339.6822&rahi=340.2761&declo=-16.2991&dechi=-16.0039')
    #r = c.get('/ls-dr10-grz/1/14/11528/6633.jpg')
    #r = c.get('/ls-dr10-model/1/3/2/3.jpg')
    #r = c.get('/sdss/1/14/304/8314.jpg')
    #r = c.get('/ls-dr10/1/6/14/25.jpg')
    #r = c.get('/wiro-C/1/13/7403/4208.jpg')
    #r = c.get('/ls-dr10/1/13/4095/3316.cat.json')

    #r = c.get('/bricks/?ralo=278.7940&rahi=278.9178&declo=32.3512&dechi=32.4086&layer=ls-dr10-south-resid-grz')
    #r = c.get('/exposures/?ra=208.7595&dec=34.8814&layer=ls-dr10')
    #r = c.get('/cutout.fits?ra=208.9270&dec=32.375&layer=ls-dr10&pixscale=0.262&bands=iz')#&bands=griz')
    #r = c.get('/jpeg-cutout?ra=190.1086&dec=1.2005&layer=ls-dr10&pixscale=0.262&bands=griz')
    #r = c.get('/exposures/?ra=29.8320&dec=19.0114&layer=ls-dr10-grz')
    #r = c.get('/wiro-C/1/13/7397/4203.jpg')
    #r = c.get('/exposures/?ra=29.8320&dec=19.0114&layer=ls-dr10-grz')
    #r = c.get('/wiro-D/1/14/14801/8410.jpg')
    #r = c.get('/exposure_panels/ls-dr10/464032/N28/?ra=198.5474&dec=-14.5133&size=100')
    #r = c.get('/exposure_panels/ls-dr10/899372/S27/?ra=349.9997&dec=-2.2077&size=100&kind=weight')
    #r = c.get('/exposure_panels/ls-dr10/899372/S27/?ra=349.9997&dec=-2.2077&size=100')
    #r = c.get('/exposure_panels/ls-dr10/899372/S27/?ra=349.9997&dec=-2.2077&size=100&kind=weightedimage')
    #r = c.get('/exposures/?ra=189.8480&dec=9.0102&layer=ls-dr67')
    #r = c.get('/iv-data/ls-dr9-south/decam-563185-N3-z')
    #r = c.get('/cutout.fits?ra=186.5224&dec=11.8116&layer=ls-dr10&pixscale=1.00&bands=i')
    #r = c.get('/fits-cutout/?ra=139.02988862264112&dec=0.3222405358699295&pixscale=0.2&layer=ls-dr10&size=500&bands=i')
    #r = c.get('/fits-cutout/?ra=139.02988862264112&dec=0.3222405358699295&pixscale=0.2&layer=ls-dr10&size=50&bands=i')
    #r = c.get('/cutout.fits?ra=146.9895&dec=13.2777&layer=unwise-neo7-mask&pixscale=2.75&size=500')
    #r = c.get('/exposures/?ra=285.7324&dec=-63.7436&layer=ls-dr10', HTTP_HOST='decaps.legacysurvey.org')
    #r = c.get('/cutout.fits?ra=146.9895&dec=13.2777&layer=unwise-neo7-mask&pixscale=2.75&size=500')
    #r = c.get('/exposures/?ra=285.7324&dec=-63.7436&layer=ls-dr10', HTTP_HOST='decaps.legacysurvey.org')
    #r = c.get('/suprime-L464/1/15/19105/16183.jpg')
    #r = c.get('/cutout.fits?ra=50.3230&dec=-43.3705&pixscale=0.2&layer=ls-dr10&size=50&bands=i')
    #r = c.get('/cutout.fits?ra=359.8802978&dec=8.739146097&pixscale=0.262&layer=ls-dr10&size=50&bands=i')
    #r = c.get('/cutout.fits?ra=50.3230&dec=-43.3705&pixscale=0.2&layer=ls-dr10&size=50&bands=i')
    #r = c.get('/suprime-ia-v1/1/14/9557/8091.jpg')
    #r = c.get('/suprime-ia-v1/1/13/4779/4044.jpg')
    #r = c.get('/exposures/?ra=150.2467&dec=2.7740&layer=suprime-ia-v1')
    #r = c.get('/exposure_panels/suprime-ia-v1/460480/det4/?ra=150.2467&dec=2.7740&size=100')
    #r = c.get('/dr10-deep/1/14/9556/8091.jpg')
    #r = c.get('/dr10-deep/1/13/4776/4044.jpg')
    #r = c.get('/suprime-L505/1/14/9529/8067.jpg')
    #r = c.get('/exposures/?ra=247.0169&dec=51.7755&layer=ls-dr9-north')
    #r = c.get('/exposures/?ra=204.0414&dec=-62.9467&layer=decaps2')
    #r = c.get('/dr10-deep/1/14/14831/8415.jpg')
    #r = c.get('/exposures/?ra=187.4274&dec=11.4106&layer=sdss')
    #r = c.get('/merian-n540/1/14/9511/8123.jpg')
    #r = c.get('/merian-n708/1/14/9511/8123.jpg')
    #r = c.get('/hsc-dr3/1/14/7818/8185.jpg')
    #r = c.get('/cutout.fits?ra=190.1086&dec=1.2005&layer=ls-dr10&pixscale=0.262&bands=i')
    #r = c.get('/hsc-dr3/1/14/6219/8308.jpg')
    #r = c.get('/hsc-dr3/1/14/6220/8308.jpg')
    #r = c.get('/cutout.fits?ra=190.1086&dec=1.2005&layer=ls-dr10&pixscale=0.262&bands=i')
    #r = c.get('/cutout.fits?ra=190.1086&dec=1.2005&layer=ls-dr10-grz&pixscale=0.262&bands=griz')
    #r = c.get('/cutout.fits?ra=190.1086&dec=1.2005&layer=ls-dr10&pixscale=0.262&bands=griz')
    #r = c.get('/ls-dr10-south/1/15/17740/13629.jpg')
    #r = c.get('/ls-dr10/1/8/138/103.jpg')
    #r = c.get('/')
    #r = c.get('/desi-tiles/edr/1/cat.json?ralo=142.1851&rahi=158.0273&declo=-2.1857&dechi=6.5009')
    #r = c.get('/desi-spec-edr/1/cat.json?ralo=149.6482&rahi=150.6384&declo=3.5210&dechi=4.0636')
    #r = c.get('/desi-spec-edr/1/cat.json?ralo=149.5747&rahi=150.5649&declo=3.0891&dechi=3.6320')
    #r = c.get('/desi-spec-edr/1/cat.json?ralo=149.9105&rahi=150.9007&declo=3.6203&dechi=4.1629')
    #r = c.get('/desi-spec-edr/1/cat.json?ralo=150.0909&rahi=150.3385&declo=2.5967&dechi=2.7325')
    #r = c.get('/desi-spec-edr/1/cat.json?ralo=150.1528&rahi=150.2766&declo=2.6306&dechi=2.6985')
    #r = c.get('/suprime-L464/1/14/9558/8092.jpg')
    #r = c.get('/suprime-L427/1/12/2388/2021.jpg')
    #r = c.get('/desi-spectrum/edr/targetid39627883857055540')
    #r = c.get('/desi-spec-edr/1/cat.json?ralo=142.1631&rahi=158.0054&declo=-1.4500&dechi=7.2317')
    #r = c.get('/desi-spec-edr/1/cat.json?ralo=192.2168&rahi=223.9014&declo=-8.6896&dechi=8.6462')
    #r = c.get('/desi-spec-edr/1/cat.json?ralo=154.9292&rahi=186.6138&declo=21.5757&dechi=36.7037')
    #r = c.get('/desi-spectrum/edr/targetid39627848784286649')
    #r = c.get('/desi-edr')
    #r = c.get('/ls-dr10-mid/1/8/151/103.jpg')
    #r = c.get('/cutout.fits?ra=203.5598&dec=23.4015&layer=ls-dr9&pixscale=0.25&invvar')
    #r = c.get('/cutout.fits?ra=203.5598&dec=23.4015&layer=ls-dr9&pixscale=0.6&invvar')
    #r = c.get('/fits-cutout?ra=50.527333&dec=-15.400056&layer=ls-dr10&pixscale=0.262&bands=grz&size=687&invvar')
    #r = c.get('/cutout.fits?ra=146.9895&dec=13.2777&layer=unwise-neo7-mask&pixscale=2.75&size=500')
    #r = c.get('/cutout.jpg?ra=90.3138&dec=-67.7344&layer=ls-dr10-south-gri&pixscale=0.262&size=500')
    #r = c.get('/fits-cutout?ra=147.48496&dec=-0.23134231&size=2000&layer=ls-dr10&pixscale=0.262&bands=r')
    #r = c.get('/ls-dr10-mid/1/8/151/103.jpg')
    #r = c.get('/cutout.fits?ra=203.5598&dec=23.4015&layer=ls-dr9&pixscale=0.25&invvar')
    #r = c.get('/cutout.fits?ra=203.5598&dec=23.4015&layer=ls-dr9&pixscale=0.6&invvar')
    #r = c.get('/desi-spectrum/dr1/targetid39633497530305185')
    #r = c.get('/desi-spectrum/dr1/targetid-228610099')
    #r = c.get('/ls-dr9/1/14/8230/6841.jpg')
    #r = c.get('/cutout.jpg?ra=218.1068&dec=8.0789&layer=ls-dr10-segmentation&pixscale=0.262&size=500')
    #r = c.get('/cutout.fits?ra=218.1068&dec=8.0789&layer=ls-dr10-segmentation&pixscale=0.262&size=500')

    # Example 1 ???
    #r = c.get('/cutout.fits?ra=143.1155&dec=-0.6154&layer=ls-dr10-segmentation&pixscale=0.262&size=32')

    # Example 2
    #r = c.get('/cutout.fits?ra=137.490537&dec=-0.406962&layer=ls-dr10-segmentation&pixscale=0.262&size=32')
    # Example 3
    #r = c.get('/cutout.fits?ra=93.6233&dec=-33.5389&layer=ls-dr10-segmentation&pixscale=0.262&size=32')
    # Example 4
    #r = c.get('/cutout.fits?ra=9.173043&dec=14.645444&layer=ls-dr10-segmentation&pixscale=0.262&size=32')
    #
    #r = c.get('/cutout.fits?ra=203.5598&dec=23.4015&layer=ls-dr9&pixscale=0.262&invvar')

    #r = c.get('/sfd/2/7/41/55.jpg')
    #r = c.get('/cfht-cosmos-cahk/1/14/9556/8091.jpg')
    #r = c.get('/ibis-color/1/14/6300/8102.jpg')
    #r = c.get('/ibis-color/1/13/3150/4043.jpg')
    #r = c.get('/ibis-color-ls/1/13/3150/4043.jpg')

    #pixscale = 0.4
    #H = W = 3000
    pixscale = 0.25
    H = W = 1000
    #r = c.get('/cutout.jpg?ra=289.89030014944893&dec=86.06584587912832&layer=ps1&height=%i&width=%i&pixscale=%f' % (H, W, pixscale))
    #r = c.get('/exposures/?ra=188.9829&dec=-56.4978&layer=decaps2')
    #r = c.get('/exposures/?ra=221.8682&dec=2.3882&layer=ibis-color')
    #r = c.get('/desi-spectrum/edr/targetid39628256290279019')

    #r = c.get('/jpl_lookup?ra=169.4535&dec=12.7557&date=2017-03-05%2004:55:39.295493&camera=decam')

    #r = c.get('/ibis-3-wide/1/14/7281/8419.jpg')
    #r = c.get('/ibis-3-wide-m464/1/5/12/16.jpg')
    #r = c.get('/iv-data/ls-dr9/decam-705256-N1')
    r = c.get('/image-data/ls-dr9-north/mosaic-125708-CCD1-z')
    # Euclid colorization
    # for i in [3,]:#1,2]:
    #     wcs = Sip('wcs%i.fits' % i)
    #     layer = get_layer('ls-dr10-south-gri')
    #     imgs = layer.render_into_wcs(wcs, 16, None, None, general_wcs=True)
    #     rgb = layer.get_rgb(imgs, 'gri')
    #     save_jpeg('wcs%i.jpg' % i, rgb)
    # sys.exit(0)

    f = open('out.jpg', 'wb')
    for x in r:
        #print('Got', type(x), len(x))
        f.write(x)
    f.close()

    sys.exit(0)
    
    from PIL import Image, ImageDraw
    import numpy as np
    img = Image.open('out.jpg')

    major_axis_arcsec = 0.0093878839515533 * 3600. * 2.
    minor_axis_arcsec = 0.0005555555555556 * 3600. * 2.
    PA = -9.47295021253918

    overlay_height = int(np.abs(major_axis_arcsec / pixscale))
    overlay_width = int(np.abs(minor_axis_arcsec / pixscale))
    overlay = Image.new('RGBA', (overlay_width, overlay_height))
    draw = ImageDraw.ImageDraw(overlay)
    box_corners = (0, 0, overlay_width, overlay_height)
    ellipse_color = '#4444ff'
    ellipse_width = 3
    draw.ellipse(box_corners, fill=None, outline=ellipse_color, width=ellipse_width)

    rotated = overlay.rotate(PA, expand=True)
    rotated_width, rotated_height = rotated.size

    ellipse_x = W/2
    ellipse_y = H/2
    paste_shift_x = int(ellipse_x - rotated_width / 2)
    paste_shift_y = int(ellipse_y - rotated_height / 2)
    img.paste(rotated, (paste_shift_x, paste_shift_y), rotated)

    img.save('ell.jpg')
    
