from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .serializers import UserSerializer
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
    watched_movies = user.watched_movies.all()
    serializer = UserSerializer(watched_movies, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def watchedEpisodes(request):
    user = request.user
    watched_episodes = user.watched_episodes.all()
    serializer = UserSerializer(watched_episodes, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_watched_movie(request):
    user = request.user
    movie_id = request.data.get('movie_id')
    progress = request.data.get('progress', 0.0)
    try:
        movie = Pelicula.objects.get(id=movie_id)
    except Pelicula.DoesNotExist:
        return Response({'error': 'Movie not found'}, status=status.HTTP_404_NOT_FOUND)
    watched_movie, created = WatchedMovie.objects.get_or_create(user=user, movie=movie)
    watched_movie.progress = progress
    watched_movie.save()    
    return Response({'message': 'Progreso de pelicula guardado'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_watched_episode(request):
    user = request.user
    episode_id = request.data.get('episode_id')
    progress = request.data.get('progress', 0.0)
    try:
        episode = Episodio.objects.get(id=episode_id)
    except Episodio.DoesNotExist:
        return Response({'error': 'Episodio no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    watched_episode, created = WatchedEpisode.objects.get_or_create(user=user, episode=episode)
    watched_episode.progress = progress
    watched_episode.save()    
    return Response({'message': 'Progreso de episodio guardado'}, status=status.HTTP_201_CREATED)