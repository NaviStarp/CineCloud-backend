import os
import subprocess
import concurrent.futures
import json
import re
import sys

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

def is_low_resolution(width, height):
    """Determina si el video tiene una resolución baja (menor que 480p)"""
    return height < 480 and width < 854

def segment_original_video(input_path, output_dir, encoder_settings):
    """Divide el video original en segmentos HLS sin cambiar la resolución"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Obtener la resolución original
    width, height = get_video_resolution(input_path)
    resolution_name = f"{height}p"
    
    # Obtener un bitrate adecuado según la resolución
    if height >= 1080:
        bitrate = '5000k'
    elif height >= 720:
        bitrate = '3000k'
    elif height >= 480:
        bitrate = '1000k'
    else:
        bitrate = '800k'
    
    command = [
        'ffmpeg', '-i', input_path,
        '-c:v', encoder_settings['encoder'], 
        encoder_settings['preset'], encoder_settings['preset_value'],
        '-b:v', bitrate,
        '-c:a', 'aac', '-b:a', '128k',
        '-f', 'hls', '-hls_time', '10', '-hls_list_size', '0',
        '-hls_segment_filename', os.path.join(output_dir, f'{resolution_name}_%03d.ts'),
        os.path.join(output_dir, f'{resolution_name}.m3u8')
    ]
    
    print(f"Procesando video original en segmentos HLS de 10 segundos...")
    print(f"Comando: {' '.join(command)}")
    try:
        subprocess.run(command, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        return True, width, height, bitrate
    except subprocess.CalledProcessError as e:
        print(f"Error durante la segmentación: {e.stderr.decode()}")
        return False, width, height, bitrate

def convert_to_resolution(input_path, output_dir, resolution, bitrate, encoder_settings):
    """Convierte el video a una resolución específica usando el codificador disponible"""
    width, height = resolution
    resolution_name = f"{height}p"
    os.makedirs(output_dir, exist_ok=True)
    
    command = [
        'ffmpeg', '-i', input_path,
        '-vf', f'scale=w={width}:h={height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
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
        # Convertir el bitrate a un valor numérico en bits por segundo
        bitrate_value = int(bitrate.replace('k', '000'))
        
        master_playlist += f"#EXT-X-STREAM-INF:BANDWIDTH={bitrate_value},RESOLUTION={width}x{height}\n"
        master_playlist += f"{height}p.m3u8\n"
    
    os.makedirs(output_dir, exist_ok=True)
    print("Creando playlist master...")
    with open(os.path.join(output_dir, 'playlist.m3u8'), 'w') as f:
        f.write(master_playlist)
    print(f"Master playlist creado en: {os.path.join(output_dir, 'playlist.m3u8')}")

def process_video(input_path, output_dir):
    """Procesa el video para las resoluciones apropiadas según la resolución original"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # Obtener la resolución original del video
        original_width, original_height = get_video_resolution(input_path)
        
        # Obtener la configuración del codificador
        encoder_settings = get_video_encoder_settings()
        
        # Verificar si es un video de baja resolución
        if is_low_resolution(original_width, original_height):
            print("Video de baja resolución detectado. Solo se segmentará sin cambiar la resolución.")
            success, width, height, bitrate = segment_original_video(input_path, output_dir, encoder_settings)
            if success:
                # Crear master playlist con la única resolución disponible
                create_master_playlist(output_dir, [(width, height, bitrate)])
                print("¡Segmentación del video original completada!")
            return
        
        # Definir las resoluciones estándar y sus bitrates para videos normales
        standard_resolutions = []
        
        # Agregar resoluciones basadas en la resolución original
        if original_height >= 1080:
            standard_resolutions.extend([
                (1920, 1080, '5000k'),
                (1280, 720, '3000k'),
                (854, 480, '1000k')
            ])
        elif original_height >= 720:
            standard_resolutions.extend([
                (1280, 720, '3000k'),
                (854, 480, '1000k')
            ])
        elif original_height >= 480:
            standard_resolutions.append(
                (854, 480, '1000k')
            )
        
        print(f"Resoluciones estándar a procesar: {standard_resolutions}")
        
        # Si no hay resoluciones estándar o el video es cuadrado/vertical, procesar solo la original
        if not standard_resolutions or original_width <= original_height:
            print("Video con formato especial (cuadrado o vertical) detectado, procesando solo la resolución original")
            original_bitrate = '3000k' if original_height >= 720 else '1000k'
            success, width, height, bitrate = segment_original_video(input_path, output_dir, encoder_settings)
            if success:
                create_master_playlist(output_dir, [(width, height, bitrate)])
                print("¡Segmentación del video original completada!")
            return
        
        # Ejecutar conversiones en paralelo
        print("Iniciando procesamiento de múltiples resoluciones...")
        successful_resolutions = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for width, height, bitrate in standard_resolutions:
                print(f"Iniciando conversión a {width}x{height} con bitrate {bitrate}")
                future = executor.submit(
                    convert_to_resolution, 
                    input_path, 
                    output_dir, 
                    (width, height), 
                    bitrate, 
                    encoder_settings
                )
                futures.append((future, (width, height, bitrate)))
            
            # Esperar a que todas las conversiones terminen
            for future, resolution in futures:
                try:
                    success = future.result()
                    if success:
                        successful_resolutions.append(resolution)
                        print(f"Conversión exitosa a resolución: {resolution[0]}x{resolution[1]}")
                except Exception as e:
                    print(f"Una conversión falló: {str(e)}")
        
        # Crear el archivo master playlist con las resoluciones que fueron convertidas exitosamente
        if successful_resolutions:
            create_master_playlist(output_dir, successful_resolutions)
            print(f"¡Conversión completa con {len(successful_resolutions)} resoluciones generadas!")
        else:
            print("No se completó ninguna conversión exitosamente. Intentando con el video original...")
            success, width, height, bitrate = segment_original_video(input_path, output_dir, encoder_settings)
            if success:
                create_master_playlist(output_dir, [(width, height, bitrate)])
                print("¡Segmentación del video original completada!")
    except Exception as e:
        print(f"Error durante el procesamiento del video: {str(e)}")
        # Intentar procesar solo la resolución original como último recurso
        try:
            print("Intentando procesar solo la resolución original como último recurso...")
            encoder_settings = get_video_encoder_settings()
            success, width, height, bitrate = segment_original_video(input_path, output_dir, encoder_settings)
            if success:
                create_master_playlist(output_dir, [(width, height, bitrate)])
                print("¡Procesamiento de emergencia completado!")
        except Exception as final_error:
            print(f"Error fatal durante el procesamiento: {str(final_error)}")
            sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Convertir video a HLS con múltiples resoluciones')
    parser.add_argument('input', help='Ruta del archivo de video de entrada')
    parser.add_argument('output', help='Directorio de salida para los archivos HLS')
    args = parser.parse_args()
    
    print(f"Procesando archivo: {args.input}")
    print(f"Directorio de salida: {args.output}")
    
    process_video(args.input, args.output)