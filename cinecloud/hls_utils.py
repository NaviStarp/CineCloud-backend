import os
import subprocess
import concurrent.futures
import json
import re

def has_nvidia_gpu():
    """Verifica si hay una GPU NVIDIA disponible con soporte para NVENC"""
    try:
        subprocess.run(['nvidia-smi'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = subprocess.run(['ffmpeg', '-encoders'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return 'h264_nvenc' in result.stdout.decode()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_video_encoder_settings():
    """Determina los ajustes de codificación según la disponibilidad de GPU"""
    if has_nvidia_gpu():
        print("GPU NVIDIA detectada, usando aceleración por hardware")
        return {
            'encoder': 'h264_nvenc',
            'preset': '-preset',
            'preset_value': 'p4'
        }
    else:
        print("No se detectó GPU NVIDIA, usando codificación por CPU")
        return {
            'encoder': 'libx264',
            'preset': '-preset',
            'preset_value': 'medium'
        }

def get_video_resolution(input_path):
    """Obtiene la resolución original del video usando ffprobe"""
    try:
        command = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0', 
            '-show_entries', 'stream=width,height', '-of', 'json', input_path
        ]
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = json.loads(result.stdout)
        width = int(data['streams'][0]['width'])
        height = int(data['streams'][0]['height'])
        print(f"Resolución original del video: {width}x{height}")
        return width, height
    except Exception as e:
        print(f"Error al obtener la resolución del video: {str(e)}")
        # Valor predeterminado alto para procesar todas las resoluciones
        return 3840, 2160

def convert_to_resolution(input_path, output_dir, resolution, bitrate, encoder_settings):
    """Convierte el video a una resolución específica usando el codificador disponible"""
    width, height = resolution
    resolution_name = f"{height}p"
    os.makedirs(output_dir, exist_ok=True)
    
    command = [
        'ffmpeg', '-i', input_path,
        '-vf', f'scale=w={width}:h={height}',
        '-c:v', encoder_settings['encoder'], 
        encoder_settings['preset'], encoder_settings['preset_value'],
        '-b:v', bitrate,
        '-c:a', 'aac', '-b:a', '128k',
        '-f', 'hls', '-hls_time', '10', '-hls_list_size', '0',
        '-hls_segment_filename', os.path.join(output_dir, f'{resolution_name}_%03d.ts'),
        os.path.join(output_dir, f'{resolution_name}.m3u8')
    ]
    
    print(f"Procesando {resolution_name}...")
    print(f"Comando: {' '.join(command)}")
    try:
        subprocess.run(command, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error durante la conversión: {e.stderr.decode()}")
        return False

def create_master_playlist(output_dir, available_resolutions):
    """Crea el archivo master playlist.m3u8 con las resoluciones disponibles"""
    master_playlist = "#EXTM3U\n"
    
    # Ordenar resoluciones de mayor a menor para el playlist
    resolutions_sorted = sorted(available_resolutions, key=lambda x: x[1], reverse=True)
    
    for width, height, bitrate in resolutions_sorted:
        master_playlist += f"#EXT-X-STREAM-INF:BANDWIDTH={bitrate.replace('k', '000')},RESOLUTION={width}x{height}\n"
        master_playlist += f"{height}p.m3u8\n"
    
    os.makedirs(output_dir, exist_ok=True)
    print("Creando playlist master...")
    with open(os.path.join(output_dir, 'playlist.m3u8'), 'w') as f:
        f.write(master_playlist)

def process_video(input_path, output_dir):
    """Procesa el video para las resoluciones apropiadas según la resolución original"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Obtener la resolución original del video
    original_width, original_height = get_video_resolution(input_path)
    
    # Obtener la configuración del codificador
    encoder_settings = get_video_encoder_settings()
    
    # Definir las resoluciones estándar y sus bitrates
    standard_resolutions = [
        (1920, 1080, '5000k'),  # 1080p
        (1280, 720, '3000k'),   # 720p
        (854, 480, '1000k')     # 480p
    ]
    
    # Filtrar las resoluciones que son menores o iguales a la original
    valid_resolutions = []
    conversions_to_run = []
    
    for width, height, bitrate in standard_resolutions:
        if width <= original_width and height <= original_height:
            valid_resolutions.append((width, height, bitrate))
            conversions_to_run.append((width, height, bitrate))
        elif height < original_height:
            # Si la altura es menor pero el ancho es mayor, ajustamos el ancho manteniendo la relación de aspecto
            scaled_width = int((width * original_height) / height)
            if scaled_width <= original_width:
                valid_resolutions.append((scaled_width, height, bitrate))
                conversions_to_run.append((scaled_width, height, bitrate))
    
    # Verificar si el video original ya está en una de nuestras resoluciones estándar
    is_original_standard = any(width == original_width and height == original_height for width, height, _ in standard_resolutions)
    
    # Si el original no está en una resolución estándar, agregar su resolución a la lista
    if not is_original_standard:
        # Encontrar el bitrate más apropiado basado en la resolución
        if original_height >= 1080:
            original_bitrate = '5000k'
        elif original_height >= 720:
            original_bitrate = '3000k'
        else:
            original_bitrate = '1000k'
        
        valid_resolutions.append((original_width, original_height, original_bitrate))
        # No necesitamos convertir el original a sí mismo
    
    # Si no hay resoluciones válidas, usar la original
    if not valid_resolutions:
        valid_resolutions.append((original_width, original_height, '3000k'))
    
    # Ejecutar conversiones en paralelo
    successful_resolutions = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for width, height, bitrate in conversions_to_run:
            future = executor.submit(convert_to_resolution, input_path, output_dir, (width, height), bitrate, encoder_settings)
            futures.append((future, (width, height, bitrate)))
        
        # Esperar a que todas las conversiones terminen
        for future, resolution in futures:
            try:
                success = future.result()
                if success:
                    successful_resolutions.append(resolution)
            except Exception as e:
                print(f"Una conversión falló: {str(e)}")
    
    # Crear el archivo master playlist con las resoluciones que fueron convertidas exitosamente
    create_master_playlist(output_dir, successful_resolutions)
    
    print("¡Conversión completa!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Convertir video a HLS con múltiples resoluciones')
    parser.add_argument('input', help='Ruta del archivo de video de entrada')
    parser.add_argument('output', help='Directorio de salida para los archivos HLS')
    args = parser.parse_args()
    
    process_video(args.input, args.output)