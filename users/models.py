from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, username, password=None):
        if not username:
            raise ValueError('El nombre de usuario es obligatorio')
        user = self.model(username=username)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None):
        user = self.create_user(username, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Eliminamos watched_movies aquí ya que usamos la relación WatchedMovie
    # Eliminamos watched_episodes aquí ya que usamos la relación WatchedEpisode
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    
    def __str__(self):
        return self.username


class WatchedMovie(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watched_movies')
    movie = models.ForeignKey('movies.Pelicula', on_delete=models.CASCADE, related_name='watched_by_users')
    progress = models.FloatField(default=0.0)
    
    class Meta:
        unique_together = ('user', 'movie')
        verbose_name = 'Película vista'
        verbose_name_plural = 'Películas vistas'
    
    def __str__(self):
        return f"{self.user.username} - {self.movie}"


class WatchedEpisode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watched_episodes')
    episode = models.ForeignKey('series.Episodio', on_delete=models.CASCADE, related_name='watched_by_users')
    progress = models.FloatField(default=0.0)
    
    class Meta:
        unique_together = ('user', 'episode')
        verbose_name = 'Episodio visto'
        verbose_name_plural = 'Episodios vistos'
    
    def __str__(self):
        return f"{self.user.username} - {self.episode}"