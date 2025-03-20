from rest_framework import authentication
from rest_framework import exceptions
from .models import User
import jwt
from django.conf import settings

class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None
            
        try:
            # Extraer el token del encabezado
            parts = auth_header.split()
            if parts[0].lower() != 'bearer':
                return None
                
            token = parts[1]
            # Decodificar el token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            # Obtener el usuario
            user = User.objects.get(id=payload['id'])
            return (user, token)
        except (IndexError, jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist) as e:
            print(f"Error: {e}")  # Puedes ver el error en la consola
            return None
