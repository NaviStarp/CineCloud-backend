from django.urls import path
from . import views

urlpatterns = [
    path('series/', views.SerieViewSet.as_view(), name='serie-list'),
    path('episodes/', views.EpisodioViewSet.as_view(), name='episode-list'),
]