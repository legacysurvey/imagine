from django.conf.urls import include, url

from django.conf import settings
from django.conf.urls.static import static

from viewer import login

urlpatterns = [
    url(r'^login/?$', login.login),
    url(r'^logout/?$',  login.logout, name='logout'),
    url(r'^logged-in/?$', login.loggedin),
    #url(r'^signedin/?', login.signedin),
    url('', include('social_django.urls', namespace='social')),

    #url(r'', include('cat.urls')),
    url(r'', include('map.urls')),
]
