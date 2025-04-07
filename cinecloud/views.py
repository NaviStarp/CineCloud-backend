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

def status(request):
    return HttpResponse("OK")

@csrf_exempt
def upload_video(request):
    if request.method == 'POST':
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
                
                try:
                    day = int(release_date_str)
                    current_date = datetime.now()
                    release_date = datetime(current_date.year, current_date.month, day)
                except:
                    release_date = datetime.now().date()
                
                video_path = default_storage.save(f'videos/{video_file.name}', ContentFile(video_file.read()))
                full_video_path = default_storage.path(video_path)

                if thumbnail_file:
                    thumbnail_path = default_storage.save(f'thumbnails/{thumbnail_file.name}', ContentFile(thumbnail_file.read()))
                else:
                    thumbnail_path = ""

                if media_type == 'Pelicula':
                    if Pelicula.objects.filter(titulo=name).exists():
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

                    # Procesar a HLS
                    output_dir = os.path.join(default_storage.location, f'hls/pelicula/{pelicula.titulo}')
                    process_video_to_hls_multi_quality(full_video_path, output_dir)

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

                    # Procesar a HLS
                    output_dir = os.path.join(default_storage.location, f'hls/serie/{serie.titulo}/{episodio.titulo}')
                    process_video_to_hls_multi_quality(full_video_path, output_dir)

            return JsonResponse({"message": "Videos uploaded and processed"})
        
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

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