from django.urls import re_path, include

from django.conf import settings
from django.conf.urls.static import static

from viewer import login

urlpatterns = [
    re_path(r'^login/?$', login.login),
    re_path(r'^logout/?$',  login.logout, name='logout'),
    re_path(r'^logged-in/?$', login.loggedin),
    #url(r'^signedin/?', login.signedin),
    re_path('', include('social_django.urls', namespace='social')),
    re_path(r'', include('map.urls')),
]
