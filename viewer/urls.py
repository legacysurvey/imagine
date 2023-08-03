from django.urls import re_path, include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    re_path(r'', include('map.urls')),
]
