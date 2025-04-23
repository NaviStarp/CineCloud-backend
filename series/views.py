from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import  Serie, Episodio
from .serializers import (
    SerieSerializer, 
    SerieSimpleSerializer,
    EpisodioSerializer
)
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import authentication_classes



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def newSeries(request):
    data = request.data
    titulo = data.get('titulo')
    descripcion = data.get('descripcion')
    fecha_estreno = data.get('fecha_estreno')
    temporadas = data.get('temporadas')
    imagen = request.FILES.get('imagen')

    if not all([titulo, descripcion, fecha_estreno, temporadas, imagen]):
        return Response({"error": "Todos los campos son obligatorios"}, status=400)

    try:
        nueva_serie = Serie.objects.create(
            titulo=titulo,
            descripcion=descripcion,
            fecha_estreno=fecha_estreno,
            temporadas=temporadas,
            imagen=imagen
        )
        serializer = SerieSerializer(nueva_serie)
        return Response(serializer.data, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

class SerieViewSet(viewsets.ModelViewSet):
    queryset = Serie.objects.all()
    serializer_class = SerieSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fecha_estreno', 'temporadas']
    search_fields = ['titulo', 'descripcion']
    ordering_fields = ['titulo', 'fecha_estreno', 'temporadas']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SerieSimpleSerializer
        return SerieSerializer
    
    @action(detail=True, methods=['get'])
    def temporadas(self, request, pk=None):
        serie = self.get_object()
        temporadas = set(serie.episodios.values_list('temporada', flat=True))
        return Response(sorted(temporadas))
    
    @action(detail=True, methods=['get'])
    def episodios_por_temporada(self, request, pk=None):
        serie = self.get_object()
        temporada = request.query_params.get('temporada', None)
        
        if temporada is not None:
            episodios = serie.episodios.filter(temporada=temporada).order_by('numero')
            serializer = EpisodioSerializer(episodios, many=True)
            return Response(serializer.data)
        else:
            return Response({"error": "Debes especificar una temporada"}, status=400)


class EpisodioViewSet(viewsets.ModelViewSet):
    queryset = Episodio.objects.all()
    serializer_class = EpisodioSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['serie', 'temporada', 'numero']
    search_fields = ['titulo', 'descripcion']
    ordering_fields = ['temporada', 'numero']

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def getSeries(request):
    series = Serie.objects.all()
    serializer = SerieSerializer(series, many=True)
    return Response(serializer.data)




@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def getEpisodiosPorSerie(request, pk):
    serie = Serie.objects.get(pk=pk)
    episodios = serie.episodios.all()
    serializer = EpisodioSerializer(episodios, many=True)
    return Response(serializer.data)