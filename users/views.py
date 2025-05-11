from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .serializers import UserSerializer, WatchedMovieSerializer, WatchedEpisodeSerializer
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import authentication_classes
from movies.models import Pelicula
from series.models import Episodio
from .models import WatchedMovie, WatchedEpisode

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    # Crear un nuevo usuario
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        user.username = user.username.lower()
        user.save()
        
        # Crear el token de autenticación para el usuario
        token = Token.objects.create(user=user)

        return Response({
            'token': token.key,  # El token se obtiene usando `token.key`
            'user': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    # Obtener los datos de inicio de sesión
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username.lower(), password=password)
    
    if user:
        # Obtener el token existente o crear uno nuevo
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,  # El token se obtiene usando `token.key`
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)

    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def prueba(request):
    return Response('Funciona')

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def authenticated(request):
    return Response(True)

@api_view(['GET'])
def isAdmin(request):
    user = request.user
    if user.is_authenticated:
        return Response(user.is_superuser)
    else:
        return Response(False)
    
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def watchedMovies(request):
    user = request.user
    watched_movies = WatchedMovie.objects.filter(user=user)
    serializer = WatchedMovieSerializer(watched_movies, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def watchedEpisodes(request):
    user = request.user
    watched_episodes = WatchedEpisode.objects.filter(user=user)
    serializer = WatchedEpisodeSerializer(watched_episodes, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def getWatchedMovie(request, movie_id):
    user = request.user
    try:
        watched_movie = WatchedMovie.objects.get(user=user, movie__id=movie_id)
        serializer = WatchedMovieSerializer(watched_movie)
        return Response(serializer.data)
    except WatchedMovie.DoesNotExist:
        return Response({'error': 'No se encontró la película vista'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def getWatchedEpisode(request, episode_id):
    user = request.user
    try:
        watched_episode = WatchedEpisode.objects.get(user=user, episode__id=episode_id)
        serializer = WatchedEpisodeSerializer(watched_episode)
        return Response(serializer.data)
    except WatchedEpisode.DoesNotExist:
        print(WatchedEpisode.objects.filter(user=user))
        return Response({'error': 'No se encontró el episodio visto'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_watched_movie(request):
    user = request.user
    movie_id = request.data.get('videoId')
    progress = int(request.data.get('progress', 0.0))
    if progress > 100:
        progress = 100
    if progress < 0:
        progress = 0
    if not movie_id:
        return Response({'error': 'Se necesita el id de la pelicula'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        movie = Pelicula.objects.get(id=movie_id)
    except Pelicula.DoesNotExist:
        return Response({'error': 'Pelicula no encotrada'}, status=status.HTTP_404_NOT_FOUND)
    watched_movie, created = WatchedMovie.objects.get_or_create(user=user, movie=movie)
    watched_movie.progress = progress
    watched_movie.save()    
    return Response({'message': 'Progreso de pelicula guardado'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_watched_episode(request):
    user = request.user
    episode_id = request.data.get('videoId')
    progress = int(request.data.get('progress', 0.0))
    if progress > 100:
        progress = 100
    if progress < 0:
        progress = 0
    if not episode_id:
        return Response({'error': 'Se necesita el id del episodio'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        episode = Episodio.objects.get(id=episode_id)
    except Episodio.DoesNotExist:
        return Response({'error': 'Episodio no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    watched_episode, created = WatchedEpisode.objects.get_or_create(user=user, episode=episode)
    watched_episode.progress = progress
    watched_episode.save()    
    print(watched_episode.progress)
    print(watched_episode.episode.titulo)
    print(watched_episode.episode.serie.titulo)
    print(watched_episode.user.username)
    print(watched_episode.user.id)
    return Response({'message': 'Progreso de episodio guardado'}, status=status.HTTP_201_CREATED)