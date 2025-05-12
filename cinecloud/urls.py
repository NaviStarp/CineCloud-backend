"""
URL configuration for cinecloud project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from rest_framework.routers import DefaultRouter
from series.views import getSeries,getEpisodiosPorSerie,newSeries,getSerieDetails,deleteSerie,editSerie
from movies.views import getMovie,getMovies,deleteMovie,editMovie
from users.views import login,signup,prueba,authenticated,isAdmin,add_watched_episode,add_watched_movie,watchedMovies,watchedEpisodes,getWatchedEpisode,getWatchedMovie
from .views import status,upload_video,mediaView,signed_media,getCategories,newCategory,get_signed_url
from django.conf import settings
from django.urls import re_path
from django.views.static import serve

router = DefaultRouter()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('signup/', signup),
    path('login/', login),
    path('prueba/', prueba),
    path('token/test/',authenticated ),
    path('isAdmin/', isAdmin),
    path('status/',status),
    path('media/upload/', upload_video),
    path('media/', mediaView),
    path('categories/', getCategories),
    path('categories/new/', newCategory, name='newCategory'),
    path('series/new/',newSeries, name='new_series'),
    path('media-signed/', signed_media, name='signed_media'),
    path('get-signed-url/<path:file_path>/', get_signed_url, name='get_signed_url'),
    re_path(r'^hls/(?P<path>.*)$', serve, {'document_root': 'media/hls'}),
    path('movies/', getMovies, name='get_movies'),
    path('movies/<int:pk>/', getMovie, name='get_movie),'),
    path('movies/progress/', watchedMovies, name='get_movies'),
    path('movies/progress/<int:movie_id>/', getWatchedMovie, name='get_watched_movie'),
    path('movies/edit/<int:pk>/', editMovie, name='edit_movie'),
    path('movies/delete/<int:pk>/', deleteMovie, name='delete_movie'),
    path('movies/progress/save/', add_watched_movie, name='save_movie'),
    path('series/',getSeries, name='get_series'),
    path('series/progress/<int:episode_id>/', getWatchedEpisode, name='get_episodes'),
    path('series/progress/', watchedEpisodes, name='get_episodes_progress'),
    path('series/<int:pk>/',getSerieDetails, name='get_serie_details'),
    path('series/edit/<int:pk>/', editSerie, name='edit_serie'),
    path('series/delete/<int:pk>/', deleteSerie, name='delete_serie'),
    path('series/progress/save/', add_watched_episode, name='save_episode'),
    path('series/<int:pk>/episodios/', getEpisodiosPorSerie, name='get_episodios_por_serie'),
]
