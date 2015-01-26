from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^image/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_image'),
    url(r'^cosmos-grz/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_cosmos_grz'),
    url(r'^cosmos-urz/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_cosmos_urz'),
    url(r'^decals/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_decals'),
    url(r'^decals-pr/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_decals_pr'),
    url(r'^decals-model/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_decals_model'),
    url(r'^des-stripe82/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_des_stripe82'),
    url(r'^des-pr/(\d*)/(\d*)/(\d*).jpg', 'map.views.map_des_pr'),
    # catalog
    url(r'decals/(\d*)/(\d*)/(\d*).cat.json', 'map.views.cat_decals'),
    # brick list
    url(r'bricks/', 'map.views.brick_list'),

    # fall-through
    url(r'', 'map.views.index'),
    )
