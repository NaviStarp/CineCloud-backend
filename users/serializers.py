from rest_framework import serializers
from .models import User, WatchedMovie, WatchedEpisode
from movies.models import Pelicula
from series.models import Episodio

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}}
        
    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        
    def update(self, instance, validated_data):
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
            validated_data.pop('password')
        return super().update(instance, validated_data)


class WatchedMovieSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = WatchedMovie
        fields = ['id', 'progress']

class WatchedEpisodeSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = WatchedEpisode
        fields = ['id', 'progress']