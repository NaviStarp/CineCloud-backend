from .models import Categoria
from rest_framework import serializers
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['nombre'] 
