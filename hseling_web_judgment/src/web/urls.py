from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.web_index, name='index'),
    url(r'^main$', views.web_main, name='main'),
    url(r'^upload$', views.web_upload_file, name='upload'),
    url(r'^status$', views.web_status, name='status'),
]
