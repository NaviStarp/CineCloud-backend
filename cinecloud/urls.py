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
from series.views import SerieViewSet, EpisodioViewSet
from movies.views import PeliculaViewSet
from users.views import login,signup,prueba,authenticated
from .views import status,upload_video,mediaView,protected_media

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
    path('media/<path:file_path>/', protected_media, name='protected_media'),
]
