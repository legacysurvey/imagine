from django.conf.urls import patterns, include, url

from cat import views

urlpatterns = [
    url(r'^sql-box/', views.sql_box),
    url(r'^cone-search/', views.cone_search),
    url(r'^catalog_near/$', views.CoordSearchCatalogList.as_view()),
]
