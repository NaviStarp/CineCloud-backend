# Cinecloud Backend

Cinecloud Backend es una aplicación desarrollada en Django que proporciona funcionalidades avanzadas para la autenticación de usuarios, renderización de contenido multimedia y transmisión en streaming de videos clasificados como películas y series. Este sistema está diseñado para ofrecer una experiencia fluida y segura, permitiendo a los usuarios acceder a contenido de alta calidad de manera eficiente. Además, su arquitectura modular facilita la escalabilidad y el mantenimiento del proyecto, adaptándose a las necesidades de crecimiento y evolución de la plataforma.

## Requisitos previos

Antes de comenzar, asegúrate de tener instalado:

- **Python** (v3.8 o superior)
- **Docker Compose** (para el despliegue de la base de datos)
- **FFmpeg** (Procesamiento de video, necesario para la transcodificación y manipulación de archivos multimedia)

## Instalación

Sigue estos pasos para configurar el proyecto en tu entorno local:

1. **Clona el repositorio:**

    ```bash
    git clone https://github.com/NaviStarp/CineCloud-backend.git
    cd CineCloud-backend
    ```

2. **Instala las dependencias:**

    ```bash
    pip install -r requirements.txt
    ```

3. **Inicia la base de datos con Docker Compose:**

    ```bash
    cd database
    docker-compose up -d
    cd ..
    ```
## Despliegue con Docker (Facil)

Para desplegar la aplicación utilizando Docker:

```bash
docker-compose up
```

## Iniciar el servidor de desarrollo

Para iniciar un servidor de desarrollo local:

```bash
python manage.py runserver
```

El servidor estará disponible en [http://localhost:8000/](http://localhost:8000/).

Para especificar un puerto diferente:

```bash
python manage.py runserver 8001
```

## Iniciar el servidor de producción
Para iniciar un servidor de producción:
```bash
uvicorn --host 0.0.0.0 --port 8000 cinecloud.asgi:application 
```
## Inicio automatico (Linux)
```bash
./start.sh
```
## Creación de usuario administrador
```bash
python manage.py createsuperuser
```githu

## Estructura del proyecto

```plaintext
├── cinecloud           # Aplicación principal del proyecto
│   ├── asgi.py         # Configuración ASGI para canales WebSocket
│   ├── consumers.py    # Consumidores WebSocket
│   ├── hls_utils.py    # Utilidades para streaming HLS
│   ├── models.py       # Modelos generales de la aplicación
│   ├── routing.py      # Enrutamiento para canales WebSocket
│   ├── serializers.py  # Serializadores para la API REST
│   ├── settings.py     # Configuración del proyecto
│   ├── urls.py         # URLs del proyecto
│   ├── views.py        # Vistas generales
│   └── wsgi.py         # Configuración WSGI
├── movies              # Aplicación para gestión de películas
├── series              # Aplicación para gestión de series
├── users               # Aplicación para gestión de usuarios
├── database            # Configuración de base de datos
├── manage.py           # Script de administración de Django
├── requirements.txt    # Dependencias del proyecto
├── Dockerfile          # Configuración para Docker
├── docker-compose.yml  # Configuración para Docker Compose
└── start.sh            # Script de inicio
```

## Aplicaciones del sistema

- **cinecloud**: Aplicación principal que integra todas las funcionalidades.
- **movies**: Gestión de películas, categorías y metadatos relacionados.
- **series**: Gestión de series, temporadas, episodios y metadatos relacionados.
- **users**: Sistema de autenticación, perfiles de usuario y preferencias.


## Problemas comunes

### Error de conexión a la base de datos
**Causa**: El contenedor de la base de datos no está en ejecución.  
**Solución**: Verifica que Docker esté ejecutando el contenedor de la base de datos con el siguiente comando:

```bash
docker ps
```

### Error al instalar dependencias
**Causa**: Conflictos de versiones de Python o entorno mal configurado.  
**Solución**: Asegúrate de estar utilizando la versión correcta de Python (v3.8 o superior) y considera crear un entorno virtual nuevo.

---

## Nota sobre el entorno virtual

Para evitar conflictos de dependencias, es fundamental trabajar dentro de un entorno virtual. Este proyecto está configurado para usar un entorno virtual llamado `.venv`. Sigue estos pasos para configurarlo y activarlo:

1. **Crear el entorno virtual** (si aún no existe):

    ```bash
    python -m venv .venv
    ```

2. **Activar el entorno virtual**:

    ```bash
    source .venv/bin/activate
    ```

3. **Instalar las dependencias dentro del entorno virtual**:

    ```bash
    pip install -r requirements.txt
    ```

Recuerda siempre activar el entorno virtual antes de ejecutar cualquier comando relacionado con el proyecto.


## Recursos adicionales

- [Documentación oficial de Django](https://docs.djangoproject.com/)
- [Documentación de Django REST framework](https://www.django-rest-framework.org/)
- [Documentación de Django Channels](https://channels.readthedocs.io/)
