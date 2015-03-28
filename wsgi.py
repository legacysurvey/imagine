"""
WSGI config for decals project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""



import os
os.environ.setdefault('DECALS_DIR', '/project/projectdirs/cosmo/work/decam/versions/work')
os.environ.setdefault('BOSS_PHOTOOBJ', '/project/projectdirs/cosmo/data/sdss/pre13/eboss/photoObj.v5b')
os.environ.setdefault('PHOTO_RESOLVE', '/project/projectdirs/cosmo/data/sdss/pre13/eboss/resolve/2013-07-29')
os.environ.setdefault('PHOTO_REDUX', '')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "decals.settings")

import sys

sys.path = []
for d in [
    '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.6',
    '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.6/site-packages',
    '/global/project/projectdirs/cosmo/webapp/viewer/venv',
    '/global/project/projectdirs/cosmo/webapp/viewer',
    '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.6/site-packages/matplotlib-1.4.3-py2.6-linux-x86_64.egg',
    ]:
    if not d in sys.path:
        sys.path.insert(0, d)

print 'meta', sys.meta_path
print 'modules', sys.modules.keys()
import django
#django = reload(django)
print django.__file__
for p in sys.path:
    print os.path.exists(p), os.path.exists(os.path.join(p, 'django')), p

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# class App(object):
#     def __init__(self):
#         self.app = None
#         self.err = 'err'
#         try:
#             from django.core.wsgi import get_wsgi_application
#             self.app = get_wsgi_application()
#         except:
#             import traceback
#             self.err = traceback.format_exc()
# 
#     def __call__(self, env, start):
#         if self.app is not None:
#             self.err = 'loaded app!'
#             try:
#                 for x in self.app(env,start):
#                     yield x
#                 return
#             except:
#                 import traceback
#                 self.err += traceback.format_exc()
#         start('200 OK', [('Content-Type', 'text/plain')])
#         yield self.err
# 
# application = App()

            

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



    
