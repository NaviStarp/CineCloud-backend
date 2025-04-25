from rest_framework import serializers
from .models import Serie, Episodio

class EpisodioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Episodio
        fields = '__all__'


class EpisodioSimpleSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar episodios dentro de una serie"""
    class Meta:
        model = Episodio
        fields = ['id', 'titulo', 'temporada', 'numero', 'descripcion', 'imagen']


class SerieSerializer(serializers.ModelSerializer):
    episodios = EpisodioSimpleSerializer(many=True, read_only=True)
    
    class Meta:
        model = Serie
        fields = '__all__'
        depth = 1


class SerieSimpleSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar series sin episodios"""
    class Meta:
        model = Serie
        fields = ['id', 'titulo', 'descripcion', 'fecha_estreno', 'temporadas', 'imagen']