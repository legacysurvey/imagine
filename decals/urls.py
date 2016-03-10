from django.conf.urls import patterns, include, url

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = (
    patterns(
    '',
    # url(r'', include('search.urls')),
    url(r'', include('cat.urls')),
    url(r'', include('map.urls')),
    ))
