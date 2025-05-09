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
from django.urls import path,include
from rest_framework.routers import DefaultRouter
from series.views import SerieViewSet, EpisodioViewSet,getSeries,getEpisodiosPorSerie,newSeries,getSerieDetails
from movies.views import PeliculaViewSet,getMovie,getMovies
from users.views import login,signup,prueba,authenticated,isAdmin,add_watched_episode,add_watched_movie
from .views import status,upload_video,mediaView,protected_media,serveHLS,getCategories,newCategory
from django.conf import settings
from django.conf.urls.static import static
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
    path('media/<path:file_path>/', protected_media, name='protected_media'),
    re_path(r'^hls/(?P<path>.*)$', serve, {'document_root': 'media/hls'}),
    path('movies/', getMovies, name='get_movies'),
    path('movies/<int:pk>/', getMovie, name='get_movie),'),
    path('movies/save/', add_watched_movie, name='save_movie'),
    path('series/',getSeries, name='get_series'),
    path('series/<int:pk>/',getSerieDetails, name='serie_detail'),
    path('series/<int:pk>/episodios/', getEpisodiosPorSerie, name='get_episodios_por_serie'),
    path('episodes/save/', add_watched_episode, name='save_episode'),
]
