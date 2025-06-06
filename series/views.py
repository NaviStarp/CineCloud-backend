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
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import authentication_classes
from cinecloud.models import Categoria
import os
from django.conf import settings


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def newSeries(request):
    data = request.data
    titulo = data.get('titulo')
    descripcion = data.get('descripcion')
    fecha_estreno = data.get('fecha_estreno')
    
    # Validar formato de fecha
    from datetime import datetime
    try:
        if fecha_estreno and fecha_estreno != '':
            # Validar que el formato sea 'YYYY-MM-DD'
            datetime.strptime(fecha_estreno, '%Y-%m-%d')
        else:
            if not fecha_estreno or fecha_estreno == '':
                fecha_estreno = datetime.now().strftime('%Y-%m-%d')
    except ValueError:
        fecha_estreno = datetime.now().strftime('%Y-%m-%d')
    temporadas = data.get('temporadas')
    categorias = data.get('categorias')
    imagen = request.FILES.get('imagen')
    
    # Validar campos requeridos
    if not titulo:
        return Response({"error": "El campo 'titulo' es requerido"}, status=400)
    
    # Convertir temporadas a entero si es necesario
    try:
        temporadas = int(temporadas) if temporadas is not None else 0
    except (ValueError, TypeError):
        return Response({"error": "El valor de temporadas debe ser un número"}, status=400)
    
    # Procesar categorías
    categorias_obj = None
    if categorias:
        import json
        # Si categorias es una cadena, intentar convertirla a lista
        if isinstance(categorias, str):
            try:
                categorias = json.loads(categorias)
            except json.JSONDecodeError:
                return Response({"error": "Formato de categorías inválido"}, status=400)
        
        # Verificar que todas las categorías existan
        categorias_obj = Categoria.objects.filter(nombre__in=categorias)
        print(categorias_obj.values_list('nombre', flat=True))
        if categorias_obj.count() != len(categorias):
            return Response({"error": "Una o más categorías no existen"}, status=400)
    
    try:
        # Crear la serie
        nueva_serie = Serie.objects.create(
            titulo=titulo,
            descripcion=descripcion,
            fecha_estreno=fecha_estreno,
            temporadas=temporadas,
            imagen=imagen
        )
        
        # Asignar categorías si existen
        if categorias_obj:
            nueva_serie.categorias.set(categorias_obj)
        
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
# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
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

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def getSerieDetails(request, pk):
    try:
        serie = Serie.objects.prefetch_related('categorias').get(pk=pk)
    except Serie.DoesNotExist:
        return Response({'error': 'Serie not found'}, status=404)
    
    serie_data = SerieSerializer(serie).data
    serie_data['categorias'] = [categoria.nombre for categoria in serie.categorias.all()]
    
    return Response(serie_data)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated, IsAdminUser])
def editSerie(request, pk):
    try:
        serie = Serie.objects.get(pk=pk)
    except Serie.DoesNotExist:
        return Response({'error': 'Serie not found'}, status=404)

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
    if imagen and serie.imagen and hasattr(serie.imagen, 'path') and os.path.isfile(serie.imagen.path):
        os.remove(serie.imagen.path)
        serie.imagen = imagen

    serializer = SerieSerializer(serie, data=data, partial=True)
    if serializer.is_valid():
        if categorias:
            serializer.validated_data['categorias'] = categorias_obj
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=400)

@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated,IsAdminUser])
def deleteSerie(request, pk):
    try:
        serie = Serie.objects.get(pk=pk)
    except Serie.DoesNotExist:
        return Response({'error': 'Serie not found'}, status=404)
    
    serie.delete()
    # Borrar el hls
    hls_path = os.path.join(settings.MEDIA_ROOT, 'hls', 'serie', str(serie.titulo))
    print(hls_path)
    if os.path.exists(hls_path) and os.path.isdir(hls_path):
        for root, dirs, files in os.walk(hls_path, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))
        os.rmdir(hls_path)
    return Response(status=204)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated, IsAdminUser])
def editEpisode(request, id):
    try:
        episodio = Episodio.objects.get(id=id)
    except Episodio.DoesNotExist:
        return Response({'error': 'Episodio not found'}, status=404)

    data = request.data
    imagen = request.FILES.get('imagen')
    if imagen and episodio.imagen and hasattr(episodio.imagen, 'path') and os.path.isfile(episodio.imagen.path):
        os.remove(episodio.imagen.path)
        episodio.imagen = imagen

    serializer = EpisodioSerializer(episodio, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=400)



@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated,IsAdminUser])
def deleteEpisode(request, id):
    try:
        episodio = Episodio.objects.get(id=id)
    except Episodio.DoesNotExist:
        return Response({'error': 'Episodio not found'}, status=404)
    
    episodio.delete()
    hls_path = os.path.join(settings.MEDIA_ROOT, 'hls', episodio.serie.titulo, str(episodio.titulo))
    print(hls_path)
    if os.path.exists(hls_path) and os.path.isdir(hls_path):
        for root, dirs, files in os.walk(hls_path, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))
        os.rmdir(hls_path)
    return Response(status=204)