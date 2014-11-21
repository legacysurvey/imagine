from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^image/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_image'),
    url(r'^cosmos-grz/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_cosmos_grz'),
    url(r'^cosmos-urz/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_cosmos_urz'),
    url(r'^decals/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_decals'),
    # fall-through
    url(r'', 'map.views.index'),
    )
