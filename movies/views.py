from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Pelicula
from django.shortcuts import render
from django.http import HttpResponseRedirect
from .forms import PeliculaForm
from .serializers import (
    PeliculaSerializer, 
)
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication


class PeliculaViewSet(viewsets.ModelViewSet):
    queryset = Pelicula.objects.all()
    serializer_class = PeliculaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fecha_estreno']
    search_fields = ['titulo', 'descripcion']
    ordering_fields = ['titulo', 'fecha_estreno', 'duracion']
    @action(detail=False, methods=['post'])
    def upload_pelicula(self, request):
        serializer = PeliculaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    def upload_pelicula_view(request):
        if request.method == 'POST':
            form = PeliculaForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect('/success/')
        else:
            form = PeliculaForm()
        return render(request, 'upload_pelicula.html', {'form': form})

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
# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
def getMovies(request):
    peliculas = Pelicula.objects.all()
    serializer = PeliculaSerializer(peliculas, many=True)
    return Response(serializer.data)