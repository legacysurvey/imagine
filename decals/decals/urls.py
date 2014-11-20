from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^image/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_image'),
    url(r'^coadd/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_coadd'),
    # fall-through
    url(r'', 'map.views.index'),
    )
