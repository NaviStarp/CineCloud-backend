from django.http import HttpResponse
from movies.models import Pelicula
from series.models import Serie, Episodio
import json
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
def status(request):
    return HttpResponse("OK")

@csrf_exempt
def upload_video(request):  
    print("Request: ", request)
    if request.method == 'POST':
        try:
            videos = request.POST.getlist('videos')
            print("Videos : " +  videos)
            for index, video_data in enumerate(videos):
                name = video_data.get('name')
                description = video_data.get('description')
                release_date = parse_date(video_data.get('releaseDate'))
                media_type = video_data.get('mediaType')
                season = video_data.get('season')
                chapter = video_data.get('chapter')
                series_name = video_data.get('seriesName')

                video_file = request.FILES.get(f'videos[{index}][video]')
                thumbnail_file = request.FILES.get(f'videos[{index}][thumbnail]')

                # Guardar archivos en almacenamiento
                video_path = default_storage.save(f'videos/{video_file.name}', ContentFile(video_file.read()))
                thumbnail_path = default_storage.save(f'thumbnails/{thumbnail_file.name}', ContentFile(thumbnail_file.read()))

                if media_type == 'Pelicula':
                    pelicula = Pelicula(
                        titulo=name,
                        descripcion=description,
                        fecha_estreno=release_date,
                        imagen=thumbnail_path,
                        video=video_path
                    )
                    print(pelicula)
                    pelicula.save()
                elif media_type == 'series':
                    serie, _ = Serie.objects.get_or_create(titulo=series_name)
                    episodio = Episodio(
                        serie=serie,
                        titulo=name,
                        descripcion=description,
                        fecha_estreno=release_date,
                        imagen=thumbnail_path,
                        video=video_path,
                        temporada=season,
                        capitulo=chapter
                    )
                    print(episodio)
                    episodio.save()

            return JsonResponse({"message": "Videos uploaded successfully"})
        except Exception as e:
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