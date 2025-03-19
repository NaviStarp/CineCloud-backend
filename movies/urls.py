from django.urls import path
from . import views

urlpatterns = [
    path('movies/', views.PeliculaViewSet.as_view(), name='movie-list'),
]