# models.py
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
    watched_movies = models.ManyToManyField(
        'movies.Pelicula',
        related_name='watched_by_users',
        blank=True
    )
    watched_episodes = models.ManyToManyField(
        'series.Episodio',
        through='WatchedEpisode',
        related_name='watched_by_users',
        blank=True
    )

    USERNAME_FIELD = 'username'

    def __str__(self):
        return self.username

class WatchedMovie(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    movie = models.ForeignKey('movies.Pelicula', on_delete=models.CASCADE)
    progress = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('user', 'movie')

class WatchedEpisode(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    episode = models.ForeignKey('series.Episodio', on_delete=models.CASCADE)
    progress = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('user', 'episode')
