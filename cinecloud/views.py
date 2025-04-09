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
from .hls_utils import convert_to_1080p,convert_to_480p,convert_to_720p,create_master_playlist
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import threading
import time
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
        
        # Lista para recopilar información sobre videos que necesitan procesamiento
        videos_to_process = []
        
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
                duration = 90

            send_progress_update(user.id, f"📥 Recibiendo video '{name}'...", 5)
            
            try:
                day = int(release_date_str)
                current_date = datetime.now()
                release_date = datetime(current_date.year, current_date.month, day)
            except:
                release_date = datetime.now().date()

            # Guardar el archivo en chunks para no agotar la memoria
            send_progress_update(user.id, f"💾 Guardando archivo '{video_file.name}'...", 10)
            
            # Crear un nombre de archivo único para evitar colisiones
            filename = f"{int(time.time())}_{video_file.name}"
            video_path = f'videos/{filename}'
            
            # Guardar el video en chunks de 4MB
            chunk_size = 4 * 1024 * 1024  # 4MB chunks
            with default_storage.open(video_path, 'wb+') as destination:
                for chunk in video_file.chunks(chunk_size=chunk_size):
                    destination.write(chunk)
                    
            full_video_path = default_storage.path(video_path)

            if thumbnail_file:
                send_progress_update(user.id, f"🖼️ Guardando thumbnail de '{name}'...", 15)
                # También guardar la miniatura en chunks si es grande
                thumbnail_filename = f"{int(time.time())}_{thumbnail_file.name}"
                thumbnail_path = f'thumbnails/{thumbnail_filename}'
                with default_storage.open(thumbnail_path, 'wb+') as destination:
                    for chunk in thumbnail_file.chunks():
                        destination.write(chunk)
            else:
                thumbnail_path = ""

            send_progress_update(user.id, f"🗂️ Registrando metadata en base de datos...", 20)

            output_dir = None
            video_id = None
            
            if media_type == 'Pelicula':
                if Pelicula.objects.filter(titulo=name).exists():
                    send_progress_update(user.id, f"⚠️ Película '{name}' ya existe. Saltando...", 25,"warning")
                    continue

                pelicula = Pelicula(
                    titulo=name,
                    descripcion=description,
                    fecha_estreno=release_date,
                    duracion=duration,
                    imagen=thumbnail_path,
                    video=video_path,
                )
                pelicula.save()
                
                output_dir = os.path.join(default_storage.location, f'hls/pelicula/{pelicula.titulo}')
                video_id = pelicula.id
                video_type = 'pelicula'

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
                    duracion=duration,
                    temporada=season,
                    numero=chapter,
                    processed=False  # Añadir este campo al modelo
                )
                if int(season) > serie.temporadas:
                    serie.temporadas = season
                    serie.save()
                episodio.save()
                
                output_dir = os.path.join(default_storage.location, f'hls/serie/{serie.titulo}/{episodio.titulo}')
                video_id = episodio.id
                video_type = 'episodio'
            
            # Añadir a la lista de videos para procesar
            videos_to_process.append({
                'user_id': user.id,
                'video_path': full_video_path,
                'output_dir': output_dir,
                'video_name': name,
                'video_type': video_type,
                'video_id': video_id
            })
            
            send_progress_update(user.id, f"🔄 Video '{name}' subido correctamente. Se procesará en breve...", 30)

        # Iniciar un thread para procesar los videos en segundo plano
        if videos_to_process:
            thread = threading.Thread(
                target=process_videos_in_background,
                args=(videos_to_process,)
            )
            thread.daemon = True  # El thread terminará cuando termine el programa principal
            thread.start()
        
        send_progress_update(user.id, f"🎉 Todos los videos han sido subidos. El procesamiento HLS ocurrirá en segundo plano.", 100)
        return JsonResponse({"message": "Videos uploaded. HLS processing will happen in the background."})
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        send_progress_update(user.id, f"❌ Error durante la subida: {str(e)}", 0,"error")
        return JsonResponse({"error": str(e)}, status=400)


# Función para procesar videos en segundo plano
def process_videos_in_background(videos_to_process):
    for video_info in videos_to_process:
        process_video_hls(**video_info)


# Función para procesar un video (reemplaza la tarea Celery)
def process_video_hls(user_id, video_path, output_dir, video_name, video_type, video_id):
    try:
        # Asegurarse de que el directorio de salida existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Procesar el video
        send_progress_update(user_id, f"⚙️ Procesando HLS de '{video_name}'...", 60)
        
        # Reducir la calidad del procesamiento para servidores menos potentes
        send_progress_update(user_id, f"⚙️ Convirtiendo a 480p '{video_name}'...", 70)
        convert_to_480p(video_path, output_dir)
        
        # Opcional: Puedes comentar alguna de estas conversiones si el servidor es muy limitado
        send_progress_update(user_id, f"⚙️ Convirtiendo a 720p '{video_name}'...", 80)
        convert_to_720p(video_path, output_dir)
        
        send_progress_update(user_id, f"⚙️ Convirtiendo a 1080p '{video_name}'...", 85)
        convert_to_1080p(video_path, output_dir)
        
        send_progress_update(user_id, f"⚙️ Creando playlist master de '{video_name}'...", 90)
        create_master_playlist(output_dir)
        
        # Actualizar estado en base de datos
        if video_type == 'pelicula':
            send_progress_update(user_id, f"✅ Película '{video_name}' procesada completamente", 100)
        else:
            send_progress_update(user_id, f"✅ Episodio '{video_name}' procesado completamente", 100)
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        send_progress_update(user_id, f"❌ Error procesando '{video_name}': {str(e)}", 0, "error")
        
        # # Marcar como fallido en la base de datos
        # if video_type == 'pelicula':
        #     Pelicula.objects.filter(id=video_id).update(processed=False, processing_error=str(e))
        # else:
        #     Episodio.objects.filter(id=video_id).update(processed=False, processing_error=str(e))

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