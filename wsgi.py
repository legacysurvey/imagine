"""
WSGI config for decals project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "decals.settings")

import sys
#print 'sys.path:', sys.path
sys.path.insert(0, '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.6')
sys.path.insert(0, '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.6/site-packages')
sys.path.insert(0, '/global/project/projectdirs/cosmo/webapp/viewer/venv')
sys.path.insert(0, '/global/project/projectdirs/cosmo/webapp/viewer')

class App(object):
    def __init__(self):
        self.app = None
        self.err = 'err'
        try:
            from django.core.wsgi import get_wsgi_application
            self.app = get_wsgi_application()
        except:
            import traceback
            self.err = traceback.format_exc()

    def __call__(self, env, start):
        if self.app is not None:
            self.err = 'loaded app!'
            try:
                for x in self.app(env,start):
                    yield x
                return
            except:
                import traceback
                self.err += traceback.format_exc()
        start('200 OK', [('Content-Type', 'text/plain')])
        yield self.err

application = App()

            

# def application(environ, start_response):
#     start_response('200 OK', [('Content-Type', 'text/plain')])
#     txt = 'Hello World -- sys.path is:\n'
#     for pth in sys.path:
#         txt = txt + pth + ' -- ' + str(os.path.exists(pth)) + '\n'
# 
#     try:
#         import django
#         txt += 'django: ' + str(django) + '\n'
#         from django.core.wsgi import get_wsgi_application
#         txt += 'get_wsgi_app:' + str(get_wsgi_application) + '\n'
#         app = get_wsgi_application()
#         txt += 'app:' + str(app) + '\n'
#     except:
#         import traceback
#         txt += 'Oops:\n' + traceback.format_exc()
#         
#     yield txt

#from django.core.wsgi import get_wsgi_application
#application = get_wsgi_application()


    
