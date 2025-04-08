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
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import subprocess
from .hls_utils import process_video_to_hls_multi_quality
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .settings import AUTH_USER_MODEL as Users
def status(request):
    return HttpResponse("OK")

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_video(request):
    user = request.user        
    try:            
        video_count = 0
        for key in request.POST:
            if key.startswith('videos[') and '][name]' in key:
                video_count = max(video_count, int(key.split('[')[1].split(']')[0]) + 1)
        
        for index in range(video_count):
            name = request.POST.get(f'videos[{index}][name]')
            description = request.POST.get(f'videos[{index}][description]')
            release_date_str = request.POST.get(f'videos[{index}][releaseDate]')
            media_type = request.POST.get(f'videos[{index}][mediaType]')
            season = request.POST.get(f'videos[{index}][season]')
            chapter = request.POST.get(f'videos[{index}][chapter]')
            series_name = request.POST.get(f'videos[{index}][seriesName]')
            series_description = request.POST.get(f'videos[{index}][seriesDescription]')
            series_releaseDate = request.POST.get(f'videos[{index}][seriesReleaseDate]')
            video_file = request.FILES.get(f'videos[{index}][video]')
            thumbnail_file = request.FILES.get(f'videos[{index}][thumbnail]')

            if not video_file or not name:
                continue

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

                pelicula = Pelicula(
                    titulo=name,
                    descripcion=description,
                    fecha_estreno=release_date,
                    duracion=90,
                    imagen=thumbnail_path,
                    video=video_path
                )
                pelicula.save()

                send_progress_update(user.id, f"⚙️ Procesando HLS de '{name}'...", 60)
                output_dir = os.path.join(default_storage.location, f'hls/pelicula/{pelicula.titulo}')
                process_video_to_hls_multi_quality(full_video_path, output_dir)

                send_progress_update(user.id, f"✅ Película '{name}' lista", 100)

            elif media_type == 'series':
                serie, _ = Serie.objects.get_or_create(
                    titulo=series_name,
                    defaults={
                        "descripcion": series_description,
                        "fecha_estreno": series_releaseDate,
                        "temporadas": 1,
                        "imagen": thumbnail_path
                    }
                )
                if Episodio.objects.filter(titulo=name, serie=serie).exists():
                    send_progress_update(user.id, f"⚠️ Episodio '{name}' ya existe. Saltando...", 25,"warning")
                    continue

                episodio = Episodio(
                    serie=serie,
                    titulo=name,
                    descripcion=description,
                    imagen=thumbnail_path,
                    video=video_path,
                    temporada=season,
                    numero=chapter
                )
                if int(season) > serie.temporadas:
                    serie.temporadas = season
                    serie.save()
                episodio.save()

                send_progress_update(user.id, f"⚙️ Procesando HLS de episodio '{name}'...", 60)
                output_dir = os.path.join(default_storage.location, f'hls/serie/{serie.titulo}/{episodio.titulo}')
                process_video_to_hls_multi_quality(full_video_path, output_dir)

                send_progress_update(user.id, f"✅ Episodio '{name}' procesado correctamente", 100)

        send_progress_update(user.id, f"🎉 Todos los videos han sido procesados", 100)
        return JsonResponse({"message": "Videos uploaded and processed"})
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        send_progress_update(user.id, f"❌ Error durante la subida: {str(e)}", 0,"error")
        return JsonResponse({"error": str(e)}, status=400)


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

def send_progress_update(user_id, message, progress, status="info"):
    channel_layer = get_channel_layer()
    print(f"Sending message to user {user_id}: {message} with progress {progress}, status: {status}")
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
    print("Peliculas: ", Pelicula.objects.all())
    peliculas = list(Pelicula.objects.values())
    series = list(Serie.objects.values())
    episodios = list(Episodio.objects.values())

    return JsonResponse({
        "peliculas": peliculas,
        "series": series,
        "episodios": episodios
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_media(request, file_path):
    # Construye la ruta completa al archivo en la carpeta media
    file_path = os.path.join(settings.MEDIA_ROOT, file_path)
    # Verifica si el archivo existe
    if not os.path.exists(file_path):
        raise Http404("Archivo no encontrado.")
    
    # Sirve el archivo
    return FileResponse(open(file_path, 'rb'))