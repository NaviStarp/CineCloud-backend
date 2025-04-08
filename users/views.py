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