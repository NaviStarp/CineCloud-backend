from .models import Categoria
from rest_framework import serializers
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        cantidad = instance.pelicula_set.count() + instance.serie_set.count()
        representation['cantidad'] = cantidad
        return representation