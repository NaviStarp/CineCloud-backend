from django.db import models
from django.urls import reverse
from datetime import timedelta

class Serie(models.Model):
    # Fields
    titulo = models.CharField(max_length=255, unique=True)
    descripcion = models.TextField()
    fecha_estreno = models.DateField()
    temporadas = models.IntegerField(null=True, blank=True) # Temporal
    imagen = models.ImageField(upload_to='series/')
    
    class Meta:
        verbose_name = "Serie"
        verbose_name_plural = "Series"
    
    def __str__(self):
        return self.titulo
    
    def get_absolute_url(self):
        return reverse("serie_detail", kwargs={"pk": self.pk})


class Episodio(models.Model):
    # Fields
    serie = models.ForeignKey(Serie, related_name='episodios', on_delete=models.CASCADE)
    titulo = models.CharField(max_length=255)
    temporada = models.IntegerField()
    numero = models.IntegerField(help_text="Número de episodio")
    descripcion = models.TextField()
    video = models.FileField(upload_to='episodios/')
    imagen = models.ImageField(upload_to='episodios/', blank=True, null=True)
    
    class Meta:
        verbose_name = "Episodio"
        verbose_name_plural = "Episodios"
        ordering = ['temporada', 'numero']
    
    def __str__(self):
        return f"{self.serie.titulo} - T{self.temporada}E{self.numero} - {self.titulo}"