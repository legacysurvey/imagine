from __future__ import print_function
if __name__ == '__main__':
    import sys
    sys.path.insert(0, 'django-1.9')
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'
    import django

import os
import fitsio
import numpy as np

from map.utils import send_file

from map.views import dr2_rgb, layer_name_map

from decals import settings

debug = print
if not settings.DEBUG_LOGGING:
    def debug(*args, **kwargs):
        pass

def jpeg_cutout(req):
    name = req.GET.get('layer', 'decals-dr3')
    name = layer_name_map(name)
    #print('jpeg_cutout: name', name)
    from map.views import get_layer
    layer = get_layer(name)
    #print('layer:', layer)
    if layer is not None:
        tempfiles = []
        rtn = layer.get_cutout(req, jpeg=True, tempfiles=tempfiles)
        for fn in tempfiles:
            print('Deleting temp file', fn)
            os.unlink(fn)
        return rtn

    if name == 'decals-dr1j':
        return jpeg_cutout_decals_dr1j(req)

def fits_cutout(req):
    name = req.GET.get('layer', 'decals-dr3')
    name = layer_name_map(name)
    from map.views import get_layer
    layer = get_layer(name)
    if layer is not None:
        tempfiles = []
        rtn = layer.get_cutout(req, fits=True, tempfiles=tempfiles)
        for fn in tempfiles:
            print('Deleting temp file', fn)
            os.unlink(fn)
        return rtn
    if name == 'decals-dr1j':
        return fits_cutout_decals_dr1j(req)

if __name__ == '__main__':
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'

    class duck(object):
        pass

    req = duck()
    req.META = dict()
    req.GET = dict(layer='decals-dr3', ra=246.2093, dec=9.6062)

    r = jpeg_cutout(req)
    print('Result', r)
    
