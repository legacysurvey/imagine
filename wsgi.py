from __future__ import print_function
"""
WSGI config for Legacy Survey viewers project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
# os.environ.setdefault('DECALS_DIR', '/project/projectdirs/cosmo/work/decam/versions/work')
# os.environ.setdefault('BOSS_PHOTOOBJ', '/project/projectdirs/cosmo/data/sdss/pre13/eboss/photoObj.v5b')
# os.environ.setdefault('PHOTO_RESOLVE', '/project/projectdirs/cosmo/data/sdss/pre13/eboss/resolve/2013-07-29')
os.environ.setdefault('PHOTO_REDUX', '')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "viewer.settings")

#import sys
#print 'sys.path:', sys.path

import django
from django.core.wsgi import get_wsgi_application

if False:
    application = get_wsgi_application()

else:
    import sys
    from astrometry.util.ttime import get_memusage

    class memory_wrapper(object):
        def __init__(self, app):
            self.app = app
        def __call__(self, *args, **kwargs):
            req = args[0]
            print('Req:', req['REMOTE_ADDR'], req['REQUEST_URI'], file=sys.stderr)
            #print('URL', req.get_full_path(), 'from', req.META['REMOTE_ADDR'],
            #      file=sys.stderr)
            #print('URL', req['REQUEST_URI'], file=sys.stderr)
            #mem0 = get_memusage(mmaps=False)
            result = self.app(*args, **kwargs)
            #mem1 = get_memusage(mmaps=False)
            #print('App', app, 'args', args, 'kwargs', kwargs, file=sys.stderr)
            # print('URL', req['REQUEST_URI'], file=sys.stderr)
            # for k in ['VmSize', 'VmRSS', 'VmData']: #mem0.keys():
            #     v0,u0 = mem0[k]
            #     v1,u1 = mem1[k]
            #     v0 = int(v0)
            #     v1 = int(v1)
            #     if u0 != u1:
            #         print('  ', k, ':', v0,u0, '->', v1,u1, file=sys.stderr)
            #     if v1 > v0:
            #         print('  %-8s: up %8i %s to %8i %s' % (k, (v1-v0), u0, v1, u0), file=sys.stderr)
            return result

    app = get_wsgi_application()
    application = memory_wrapper(app)

