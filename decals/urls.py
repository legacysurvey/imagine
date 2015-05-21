from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    '',
    #url(r'^viewer/', include('map.urls')),
    url(r'', include('search.urls')),
    url(r'', include('map.urls')),
    )
