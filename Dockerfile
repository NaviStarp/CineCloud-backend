# Use the official Python runtime image
FROM python:3.13

# Create the app directory
RUN mkdir /app

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Configurar variables de entorno
# Evita que Python escriba archivos pyc en el disco
ENV PYTHONDONTWRITEBYTECODE=1
# Evita que Python almacene en búfer stdout y stderr
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Actualizar pip
RUN pip install --upgrade pip

# Copiar el archivo de requisitos e instalar dependencias
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto Django al contenedor
COPY . /app/

# Exponer el puerto de Django
EXPOSE 8000

# Ejecutar comandos directamente 
CMD sh -c "python manage.py makemigrations && python manage.py migrate && python manage.py create_admin && uvicorn cinecloud.asgi:application --host 0.0.0.0 --port 8000 --reload"