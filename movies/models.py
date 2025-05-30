from django.db import models
from django.urls import reverse
from cinecloud.models import Categoria 

class Pelicula(models.Model):
    # Fields
    titulo = models.CharField(max_length=255,unique=True)
    descripcion = models.TextField(null=True, blank=True)
    fecha_estreno = models.DateField()
    categorias = models.ManyToManyField(Categoria, blank=True)
    duracion = models.IntegerField(help_text="Duración en minutos")
    video = models.FileField(upload_to='peliculas/')
    imagen = models.ImageField(upload_to='peliculas/')
    
    class Meta:
        verbose_name = "Película"
        verbose_name_plural = "Películas"
    
    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return reverse("pelicula_detail", kwargs={"pk": self.pk})
