from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import os

@receiver(post_migrate)
def create_default_superuser(sender, **kwargs):
    User = get_user_model()
    
    if not User.objects.filter(is_superuser=True).exists():
        DJANGO_SUPERUSER_USERNAME = os.environ.get('SUPERUSER_NAME', 'admin')
        DJANGO_SUPERUSER_PASSWORD = os.environ.get('SUPERUSER_PASSWORD', 'adminpassword')

        User.objects.create_superuser(
            username=DJANGO_SUPERUSER_USERNAME,
            password=DJANGO_SUPERUSER_PASSWORD
        )
        print('Superuser created successfully!')