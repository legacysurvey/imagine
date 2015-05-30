from django.conf.urls import patterns, include, url
from django.conf import settings

urlpatterns = patterns('',
    url(r'^api/search/(?P<query>.+)', 'search.views.api_search'),
    url(r'^search/form', 'search.views.search_form'),
    #url(r'^search/result', 'search.views.search_result'),
    )
