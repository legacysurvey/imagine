"""
WSGI config for decals project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "decals.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

# Debugging / profiling
# djangoapp = get_wsgi_application()
# def application(environ, start_response):
#     print 'Starting Django request'
#     import datetime
#     import time
#     t0 = datetime.datetime.now()
#     cpu0 = time.clock()
#     #print 'wsgi called:', t0
# 
#     import cProfile
#     fn = '/home/dstn/decals-web/pro/%s' % t0.isoformat()
#     cProfile.runctx('djangoapp(environ, start_response)', globals(), locals(), filename=fn)
#     #cProfile.run('rtn = djangoapp(environ, start_response)', fn)
#     print 'Wrote', fn
# 
#     rtn = djangoapp(environ, start_response)
# 
#     t1 = datetime.datetime.now()
#     cpu1 = time.clock()
#     #print 'got result :', t1
#     print 'Django call took :', (t1-t0).total_seconds(), 'sec wall,', (cpu1-cpu0), 'CPU'
#     return rtn
#
