from django.conf.urls import patterns, include, url

from cat import views

urlpatterns = [
    url(r'^sql-box/', views.sql_box),
    url(r'^search/', views.cat_search),
]
