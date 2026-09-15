from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("status", views.status, name="status"),
    path("video", views.video, name="video"),
    path("progress", views.progress, name="progress"),
]
