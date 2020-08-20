from __future__ import print_function
if __name__ == '__main__':
    import sys
    sys.path.insert(0, 'django-1.9')
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'viewer.settings'
    import django

import os
import fitsio
import numpy as np

from map.utils import send_file
from map.views import needs_layer

from viewer import settings

try:
    # py2
    #from urllib2 import urlopen
    from urllib import urlencode
except:
    # py3
    #from urllib.request import urlopen
    from urllib.parse import urlencode

debug = print
if not settings.DEBUG_LOGGING:
    def debug(*args, **kwargs):
        pass

@needs_layer()
def _cutout(req, jpeg=True):
    from django.http import HttpResponseRedirect, HttpResponse
    if not settings.ENABLE_CUTOUTS:
        return HttpResponse('No cutouts enabled')

    # Sanjaya : redirect to NERSC
    if (settings.REDIRECT_CUTOUTS_DECAPS and
        req.layer_name in ['decaps', 'decaps-model', 'decaps-resid']):
        return HttpResponseRedirect('http://legacysurvey.org/viewer' + req.path + '?' + urlencode(req.GET))

    tempfiles = []
    if jpeg:
        rtn = req.layer.get_cutout(req, jpeg=True, tempfiles=tempfiles)
    else:
        rtn = req.layer.get_cutout(req, fits=True, tempfiles=tempfiles)
    for fn in tempfiles:
        os.unlink(fn)
    return rtn

def jpeg_cutout(req):
    return _cutout(req)

def fits_cutout(req):
    return _cutout(req, jpeg=False)

if __name__ == '__main__':
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'viewer.settings'

    class duck(object):
        pass

    req = duck()
    req.META = dict()
    req.GET = dict(layer='decals-dr3', ra=246.2093, dec=9.6062)

    r = jpeg_cutout(req)
    print('Result', r)
    
