from django.conf.urls import patterns, include, url

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = (
    patterns(
    '',
    url(r'', include('map.urls')),
    ))
# + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# + static('/viewer/static/', document_root=settings.STATIC_ROOT)
# )


#print 'urlpatterns:', urlpatterns

