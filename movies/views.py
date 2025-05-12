from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Pelicula
import json
from cinecloud.models import Categoria
from django.shortcuts import render
from django.http import HttpResponseRedirect
from .forms import PeliculaForm
from .serializers import (
    PeliculaSerializer, 
)
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from rest_framework.authentication import TokenAuthentication
import os
from django.conf import settings

class PeliculaViewSet(viewsets.ModelViewSet):
    queryset = Pelicula.objects.all()
    serializer_class = PeliculaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fecha_estreno']
    search_fields = ['titulo', 'descripcion']
    ordering_fields = ['titulo', 'fecha_estreno', 'duracion']

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def getMovie(request, pk):
    try:
        pelicula = Pelicula.objects.prefetch_related('categorias').get(pk=pk)
    except Pelicula.DoesNotExist:
        return Response({'error': 'Pelicula not found'}, status=404)
    
    pelicula_data = PeliculaSerializer(pelicula).data
    pelicula_data['categorias'] = [categoria.nombre for categoria in pelicula.categorias.all()]
    
    return Response(pelicula_data)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def getMovies(request):
    peliculas = Pelicula.objects.all()
    serializer = PeliculaSerializer(peliculas, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated, IsAdminUser])
def editMovie(request, pk):
    try:
        pelicula = Pelicula.objects.get(pk=pk)
    except Pelicula.DoesNotExist:
        return Response({'error': 'Pelicula not found'}, status=404)

    data = request.data
    categorias = data.get('categorias')

    if categorias:
        if isinstance(categorias, str):
            try:
                categorias = json.loads(categorias)
            except json.JSONDecodeError:
                return Response({"error": "Invalid category format"}, status=400)

        categorias = [categoria.strip() for categoria in categorias]
        categorias_obj = Categoria.objects.filter(nombre__in=categorias)

        if categorias_obj.count() != len(set(categorias)):
            return Response({"error": "One or more categories do not exist"}, status=400)

    imagen = request.FILES.get('imagen')
    if imagen and pelicula.imagen and hasattr(pelicula.imagen, 'path') and os.path.isfile(pelicula.imagen.path):
        os.remove(pelicula.imagen.path)
        pelicula.imagen = imagen

    serializer = PeliculaSerializer(pelicula, data=data, partial=True)
    if serializer.is_valid():
        if categorias:
            serializer.validated_data['categorias'] = categorias_obj
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=400)


@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated,IsAdminUser])
def deleteMovie(request, pk):
    try:
        pelicula = Pelicula.objects.get(pk=pk)
    except Pelicula.DoesNotExist:
        return Response({'error': 'Pelicula not found'}, status=404)
    
    pelicula.delete()
    # Borrar el hls 
    hls_path = os.path.join(settings.MEDIA_ROOT, 'hls','pelicula', str(pelicula.titulo))
    print(hls_path)
    if os.path.exists(hls_path) and os.path.isdir(hls_path):
        for root, dirs, files in os.walk(hls_path, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))
        os.rmdir(hls_path)
    return Response(status=204)