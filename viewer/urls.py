from django.conf.urls import include, url

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    url(r'', include('cat.urls')),
    url(r'', include('map.urls')),
]
