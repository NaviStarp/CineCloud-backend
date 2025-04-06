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
            
            print(f"Detected {video_count} videos in request")
            
            # Process each video entry
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
                    print(f"Missing required data for video {index}")
                    continue
                
                try:
                    day = int(release_date_str)
                    current_date = datetime.now()
                    release_date = datetime(current_date.year, current_date.month, day)
                except (ValueError, TypeError):
                    try:
                        release_date = parse_date(release_date_str) if release_date_str else datetime.now().date()
                    except:
                        release_date = datetime.now().date()
                
                if video_file:
                    video_path = default_storage.save(f'videos/{video_file.name}.mp4', ContentFile(video_file.read()))
                else:
                    video_path = ""
                    
                if thumbnail_file:
                    thumbnail_path = default_storage.save(f'thumbnails/{thumbnail_file.name}', ContentFile(thumbnail_file.read()))
                else:
                    thumbnail_path = ""
                if Pelicula.objects.filter(titulo=name).exists():
                    print(f"Movie with name {name} already exists")
                    continue
                if Episodio.objects.filter(titulo=name).exists() and Serie.objects.filter(titulo=series_name).exists():
                    print(f"Episode with name {name} already exists")
                    continue
                if media_type == 'Pelicula':
                    pelicula = Pelicula(
                        titulo=name,
                        descripcion=description,
                        fecha_estreno=release_date,
                        duracion=90,
                        imagen=thumbnail_path,
                        video=video_path
                    )
                    print(f"Saving movie: {name}")
                    pelicula.save()
                    
                elif media_type == 'series':
                    serie, created = Serie.objects.get_or_create(titulo=series_name, defaults={
                        "descripcion": series_description,
                        "fecha_estreno": series_releaseDate,
                        "temporadas": 1,
                        "imagen": thumbnail_path
                        })
                    episodio = Episodio(
                        serie=serie,
                        titulo=name,
                        descripcion=description,
                        # fecha_estreno=release_date,
                        # duracion=30,
                        imagen=thumbnail_path,
                        video=video_path,
                        temporada=season,
                        numero=chapter
                    )
                    if  int(episodio.temporada) > serie.temporadas:
                        serie.temporadas = episodio.temporada
                        serie.save()
                    print(f"Saving episode: {name} for series: {series_name}")
                    episodio.save()
            
            return JsonResponse({"message": "Videos uploaded successfully"})
            
        except Exception as e:
            import traceback
            print("Error uploading videos:", str(e))
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Invalid request method"}, status=405)

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