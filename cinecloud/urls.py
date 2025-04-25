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
from series.views import SerieViewSet, EpisodioViewSet,getSeries,getEpisodiosPorSerie,newSeries
from movies.views import PeliculaViewSet
from users.views import login,signup,prueba,authenticated
from .views import status,upload_video,mediaView,protected_media,serveHLS,getCategories,newCategory
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from django.views.static import serve

router = DefaultRouter()
router.register(r'peliculas', PeliculaViewSet)
router.register(r'series', SerieViewSet)
router.register(r'episodios', EpisodioViewSet)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('signup/', signup),
    path('login/', login),
    path('prueba/', prueba),
    path('token/test/',authenticated ),
    path('status/',status),
    path('media/upload/', upload_video),
    path('media/', mediaView),
    path('categories/', getCategories),
    path('categories/new/', newCategory, name='newCategory'),
    path('series/new/',newSeries, name='new_series'),
    path('media/<path:file_path>/', protected_media, name='protected_media'),
    # path('hls/<path:file_path>/', serveHLS, name='serve_hls'),
    re_path(r'^hls/(?P<path>.*)$', serve, {'document_root': 'media/hls'}),
    path('series/',getSeries, name='get_series'),
    path('series/<int:pk>/', getEpisodiosPorSerie, name='get_episodios_por_serie')
]
