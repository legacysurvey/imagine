"""
WSGI config for decals project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "decals.settings")

from django.core.wsgi import get_wsgi_application

#application = get_wsgi_application()

djangoapp = get_wsgi_application()

def application(environ, start_response):
    import datetime
    t0 = datetime.datetime.now()
    #print 'wsgi called:', t0
    rtn = djangoapp(environ, start_response)
    t1 = datetime.datetime.now()
    #print 'got result :', t1
    print 'Django call took :', (t1-t0).total_seconds(), 'sec'
    return rtn
