from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os
from dotenv import load_dotenv

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        User = get_user_model()
        load_dotenv()
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username=os.environ.get('SUPERUSER_NAME', 'admin').lower(),
                password=os.environ.get('SUPERUSER_PASSWORD', 'admin'),
            )
            self.stdout.write(self.style.SUCCESS(f"Superusuario llamado {os.environ.get('SUPERUSER_NAME', 'admin').lower()} con contraseña {os.environ.get('SUPERUSER_PASSWORD', 'admin')} creado correctamente"))