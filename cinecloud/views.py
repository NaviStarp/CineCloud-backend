from django.http import HttpResponse
from movies.models import Pelicula
from series.models import Serie, Episodio
import json
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.http import JsonResponse
from django.http import FileResponse
from django.conf import settings
from django.http import Http404
from django.db.models import F
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from .hls_utils import process_video
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Categoria
from .serializers import CategoriaSerializer
from rest_framework.response import Response
from django.core.signing import TimestampSigner, BadSignature
import time
from .settings import AUTH_USER_MODEL as Users
from django.urls import reverse
from django.utils.http import urlencode

def status(request):
    return HttpResponse("OK")

@api_view(['POST'])
@permission_classes([IsAuthenticated,IsAdminUser])
def upload_video(request):
    user = request.user        
    try:            
        video_count = 0
        for key in request.POST:
            if key.startswith('videos[') and '][name]' in key:
                video_count = max(video_count, int(key.split('[')[1].split(']')[0]) + 1)
            if key.startswith('rescale'):
                rescale = request.POST.get(key)
                print("RESCALE: ", rescale)
                print("TIPO DE RESCALE: ", type(rescale))
                if rescale == 'true':
                    rescale = True
                else:
                    rescale = False
        for index in range(video_count):
            name = request.POST.get(f'videos[{index}][name]')
            description = request.POST.get(f'videos[{index}][description]')
            release_date_str = request.POST.get(f'videos[{index}][releaseDate]')
            media_type = request.POST.get(f'videos[{index}][mediaType]')
            season = request.POST.get(f'videos[{index}][season]')
            chapter = request.POST.get(f'videos[{index}][chapter]')
            duration = request.POST.get(f'videos[{index}][duration]')
            series_name = request.POST.get(f'videos[{index}][seriesName]')
            series_description = request.POST.get(f'videos[{index}][seriesDescription]')
            series_releaseDate = request.POST.get(f'videos[{index}][seriesReleaseDate]')
            video_file = request.FILES.get(f'videos[{index}][video]')
            thumbnail_file = request.FILES.get(f'videos[{index}][thumbnail]')

            if not video_file or not name:
                continue
            if not duration:
                duration = 0

            send_progress_update(user.id, f"📥 Recibiendo video '{name}'...", 5)
            
            try:
                day = int(release_date_str)
                current_date = datetime.now()
                release_date = datetime(current_date.year, current_date.month, day)
            except:
                release_date = datetime.now().date()

            send_progress_update(user.id, f"💾 Guardando archivo '{video_file.name}'...", 10)
            video_path = default_storage.save(f'videos/{video_file.name}', ContentFile(video_file.read()))
            full_video_path = default_storage.path(video_path)

            if thumbnail_file:
                send_progress_update(user.id, f"🖼️ Guardando thumbnail de '{name}'...", 15)
                thumbnail_path = default_storage.save(f'thumbnails/{thumbnail_file.name}', ContentFile(thumbnail_file.read()))
            else:
                thumbnail_path = ""

            send_progress_update(user.id, f"🗂️ Registrando metadata en base de datos...", 20)
            if media_type == 'Pelicula':
                if Pelicula.objects.filter(titulo=name).exists():
                    send_progress_update(user.id, f"⚠️ Película '{name}' ya existe. Saltando...", 25,"warning")
                    continue
                video_hls = "/hls/pelicula/" + name
                print("RUTA DEL VIDEO : ", video_hls)
                pelicula = Pelicula(
                    titulo=name,
                    descripcion=description,
                    fecha_estreno=release_date,
                    duracion=duration,
                    imagen=thumbnail_path,
                    video=video_hls
                )
                pelicula.save()  # Save the pelicula object to assign an ID
                categorias_raw = request.POST.get(f'videos[{index}][categorias]')
                categorias_list = json.loads(categorias_raw) if categorias_raw else []
                categorias = Categoria.objects.filter(nombre__in=categorias_list)
                if categorias.exists():
                    pelicula.categorias.add(*categorias)  # Use add() to associate categories
                pelicula.save()
                print("CATEGORIAS: ", categorias_list)
                print("Categorias existentes: ", Categoria.objects.all())
                print("CATEGORIAS DE LA PELICULA: ", pelicula.categorias.all())
                output_dir = os.path.join(default_storage.location, f'hls/pelicula/{pelicula.titulo}')
                send_progress_update(user.id, f"⚙️ Procesando HLS de '{name}'...", 60)
                process_video(full_video_path,output_dir,rescale)
                send_progress_update(user.id, f"✅ Película '{name}' lista", 100)

            elif media_type == 'series':
                serie, created = Serie.objects.get_or_create(
                    titulo=series_name,
                    defaults={
                        "descripcion": series_description,
                        "fecha_estreno": series_releaseDate,
                        "temporadas": 1,
                        "imagen": thumbnail_path
                    }
                )
                if created:
                    serie.categorias.set(Categoria.objects.filter(nombre__in=request.POST.getlist(f'videos[{index}][categorias]')))
                    serie.save()
                if Episodio.objects.filter(titulo=name, serie=serie).exists():
                    send_progress_update(user.id, f"⚠️ Episodio '{name}' ya existe. Saltando...", 25,"warning")
                    continue
                video_hls = "/hls/serie/" + serie.titulo + "/" + name
                episodio = Episodio(
                    serie=serie,
                    titulo=name,
                    descripcion=description,
                    imagen=thumbnail_path,
                    video=video_hls,
                    duracion=duration,
                    temporada=season,
                    numero=chapter
                )
                if int(season) > serie.temporadas:
                    serie.temporadas = season
                    serie.save()
                episodio.save()
                send_progress_update(user.id, f"⚙️ Creando playlist master de '{name}'...", 35)
                send_progress_update(user.id, f"⚙️ Procesando HLS de episodio '{name}'...", 40)
                try:
                    output_dir = os.path.join(default_storage.location, f'hls/serie/{serie.titulo}/{episodio.titulo}')
                    process_video(full_video_path,output_dir,rescale)
                except Exception as e:
                    from django.db import transaction
                    print(f"Error al procesar el video: {e}")
                    transaction.rollback()
                    send_progress_update(user.id, f"❌ Error al procesar el video: {e}", 0,"error")
                    continue
                send_progress_update(user.id, f"✅ Episodio '{name}' procesado correctamente", 100)

        clean_videos()
        send_progress_update(user.id, f"🎉 Todos los videos han sido procesados", 100)
        return JsonResponse({"message": "Videos uploaded and processed"})
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        send_progress_update(user.id, f"❌ Error durante la subida: {str(e)}", 0,"error")
        return JsonResponse({"error": str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def newCategory(request):
    # Crea una nueva categoría
    data = request.data
    nombre = data.get('nombre')

    if not nombre:
        return JsonResponse({"error": "El nombre es obligatorio"}, status=400)

    try:
        categoria = Categoria(nombre=nombre)
        categoria.save()
        return JsonResponse({"message": "Categoría creada con éxito", "id": categoria.id}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def editCategory(request, pk):
    # Edita una categoría existente
    try:
        categoria = Categoria.objects.get(pk=pk)
    except Categoria.DoesNotExist:
        return JsonResponse({"error": "Categoría no encontrada"}, status=404)

    data = request.data
    nombre = data.get('nombre')

    if not nombre:
        return JsonResponse({"error": "El nombre es obligatorio"}, status=400)

    try:
        categoria.nombre = nombre
        categoria.save()
        return JsonResponse({"message": "Categoría editada con éxito"}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteCategory(request, pk):
    # Elimina una categoría existente
    try:
        categoria = Categoria.objects.get(pk=pk)
    except Categoria.DoesNotExist:
        return JsonResponse({"error": "Categoría no encontrada"}, status=404)

    try:
        categoria.delete()
        return JsonResponse({"message": "Categoría eliminada con éxito"}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
def getCategories(request):
    # Obtiene todas las categorías de películas
    categories = Categoria.objects.distinct()
    serializer = CategoriaSerializer(categories, many=True)
    return Response(serializer.data, status=200)

[IsAuthenticated]
def serveHLS(request, file_path):
    # Construye la ruta completa al archivo en la carpeta media
    file_path = os.path.join(settings.MEDIA_ROOT, 'hls', file_path)
    print(file_path)
    # Verifica si el archivo existe
    if not os.path.exists(file_path):
        raise Http404("Archivo no encontrado.")
    
    # Sirve el archivo
    return FileResponse(open(file_path, 'rb'))

def clean_videos():
    # Elimina los archivos de video antiguos
    video_dir = os.path.join(settings.MEDIA_ROOT, 'videos')
    for filename in os.listdir(video_dir):
        file_path = os.path.join(video_dir, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"Archivo eliminado: {file_path}")


def send_progress_update(user_id, message, progress, status="info"):
    channel_layer = get_channel_layer()
    print(f"Sending progress update to user {user_id}: {message}, {progress}, {status}")
    async_to_sync(channel_layer.group_send)(
        f"progress_{user_id}",
        {
            "type": "progress_message",
            "message": message,
            "progress": progress,
            "status": status
        }
    )

def mediaView(request):
    peliculas = list(Pelicula.objects.values('id', 'titulo', 'descripcion', 'fecha_estreno', 'duracion', 'imagen', 'video').annotate(categorias=F('categorias__nombre')).distinct())
    peliculas = [
        {
            **pelicula,
            "categorias": list(Pelicula.objects.filter(id=pelicula['id']).values_list('categorias__nombre', flat=True).distinct())
        }
        for pelicula in peliculas
    ]

    series = list(Serie.objects.values('id', 'titulo', 'descripcion', 'fecha_estreno', 'temporadas', 'imagen').annotate(categorias=F('categorias__nombre')).distinct())
    series = [
        {
            **serie,
            "categorias": list(Serie.objects.filter(id=serie['id']).values_list('categorias__nombre', flat=True).distinct())
        }
        for serie in series
    ]
    episodios = list(Episodio.objects.values('id', 'titulo', 'temporada', 'numero', 'descripcion', 'duracion', 'imagen', 'video').distinct())
    return JsonResponse({
        "peliculas": peliculas,
        "series": series,
        "episodios": episodios
    })

@api_view(['GET'])
def signed_media(request):
    path = request.GET.get('path')
    expires = request.GET.get('expires')
    signature = request.GET.get('signature')

    if not all([path, expires, signature]):
        raise Http404("Parámetros inválidos.")

    try:
        expected = f"{path}:{expires}"
        signer = TimestampSigner()
        signer.unsign(signature, max_age=int(expires) - int(time.time()))
    except BadSignature:
        raise Http404("Firma inválida o expirada.")

    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(file_path):
        raise Http404("Archivo no encontrado.")

    return FileResponse(open(file_path, 'rb'))

@api_view(['GET'])
def get_signed_url(request, file_path):
    expiry_seconds = int(request.GET.get('expiry_seconds', 3600))
    signer = TimestampSigner()
    expires = int(time.time()) + expiry_seconds
    value = f"{file_path}:{expires}"
    signature = signer.sign(value)
    
    url = reverse('signed_media')
    query = urlencode({
        'path': file_path,
        'expires': expires,
        'signature': signature,
    })
    return JsonResponse({"signed_url": f"{url}?{query}"})