import os
import ffmpeg
import concurrent.futures
import subprocess
import argparse

def detect_gpus():
    """Detecta GPUs disponibles usando bibliotecas de Python de manera multiplataforma"""
    gpu_info = {
        'nvidia': False,
        'amd': False
    }
    # Método 1: Verificar si GPUtil detecta GPUs
    if not gpu_info['nvidia']:
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            for gpu in gpus:
                if 'nvidia' in gpu.name.lower():
                    gpu_info['nvidia'] = True
                    print(f"GPU NVIDIA detectada via GPUtil: {gpu.name}")
                elif any(amd_keyword in gpu.name.lower() for amd_keyword in ['amd', 'radeon', 'vega', 'rx']):
                    gpu_info['amd'] = True
                    print(f"GPU AMD detectada via GPUtil: {gpu.name}")
        except ImportError:
            print("GPUtil no está instalado, intentando método alternativo...")
    
    # Si GPUtil no detectó GPUs, intentar con pynvml
    if not gpu_info['nvidia']:
        try:
            import pynvml
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                gpu_info['nvidia'] = True
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                print(f"GPU NVIDIA detectada via NVML: {pynvml.nvmlDeviceGetName(handle).decode()}")
            pynvml.nvmlShutdown()
        except ImportError:
            print("NVML no está instalado, intentando último método...")
    
    # Método de último recurso: verificar si los codificadores están disponibles en ffmpeg
    try:
        ffmpeg_encoders = subprocess.run(['ffmpeg', '-encoders'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        encoders_output = ffmpeg_encoders.stdout.decode()
        
        if 'h264_nvenc' in encoders_output and not gpu_info['nvidia']:
            gpu_info['nvidia'] = True
            print("Codificador NVIDIA detectado en ffmpeg")
            
        if 'h264_amf' in encoders_output and not gpu_info['amd']:
            gpu_info['amd'] = True
            print("Codificador AMD detectado en ffmpeg")
    except:
        print("No se pudo verificar codificadores disponibles en ffmpeg")
    
    return gpu_info

def get_video_encoder_settings():
    """Determina los ajustes de codificación según la disponibilidad de GPU"""
    gpu_info = detect_gpus()
    
    # Forzar la comprobación de NVIDIA primero
    if gpu_info['nvidia']:
        print("GPU NVIDIA detectada, usando aceleración por hardware NVENC")
        return {
            'codec': 'h264_nvenc',
            'preset': 'p4'
        }
    elif gpu_info['amd']:
        print("GPU AMD detectada, usando aceleración por hardware AMF")
        return {
            'codec': 'h264_amf',
            'quality': 'balanced'  # Para AMF usamos quality en lugar de preset
        }
    else:
        print("No se detectó GPU compatible, usando codificación por CPU")
        return {
            'codec': 'libx264',
            'preset': 'medium'
        }

def get_video_resolution(input_path):
    """Obtiene la resolución original del video usando ffprobe"""
    try:
        probe = ffmpeg.probe(input_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream is None:
            raise Exception("No se encontró una pista de video en el archivo")
            
        width = int(video_stream['width'])
        height = int(video_stream['height'])
        print(f"Resolución original del video: {width}x{height}")
        return width, height
    except Exception as e:
        print(f"Error al obtener la resolución del video: {str(e)}")
        # Valor predeterminado alto para procesar todas las resoluciones
        return 3840, 2160

def is_low_resolution(width, height):
    """Determina si el video tiene una resolución baja (menor que 480p)"""
    return height < 480 and width < 854

def apply_encoder_settings(stream, encoder_settings):
    """Aplica los ajustes del codificador a un stream de ffmpeg"""
    # Aplicar la configuración del codificador según el tipo
    output_args = {}
    
    # Configurar el codec de video
    output_args['c:v'] = encoder_settings['codec']
    
    # Añadir preset o quality según el codec
    if encoder_settings['codec'] == 'h264_nvenc':
        output_args['preset'] = encoder_settings['preset']
    elif encoder_settings['codec'] == 'h264_amf':
        output_args['quality'] = encoder_settings['quality']
    else:  # libx264
        output_args['preset'] = encoder_settings['preset']
    
    return output_args

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
    
    output_path = os.path.join(output_dir, f'{resolution_name}.m3u8')
    segment_pattern = os.path.join(output_dir, f'{resolution_name}_%03d.ts')
    
    try:
        # Configurar stream de entrada
        stream = ffmpeg.input(input_path)
        
        # Obtener configuración del codificador
        encoder_args = apply_encoder_settings(stream, encoder_settings)
        
        # Configurar los argumentos de salida
        output_args = {
            'b:v': bitrate,
            'c:a': 'aac',
            'b:a': '128k',
            'f': 'hls',
            'hls_time': '10',
            'hls_list_size': '0',
            'hls_segment_filename': segment_pattern,
            **encoder_args  # Integrar los argumentos del codificador
        }
        
        # Ejecutar el comando
        print(f"Procesando video original en segmentos HLS de 10 segundos...")
        print(f"Argumentos de salida: {output_args}")
        
        ffmpeg.output(stream, output_path, **output_args).run(capture_stdout=True, capture_stderr=True)
        return True, width, height, bitrate
    except ffmpeg._run.Error as e:
        print(f"Error durante la segmentación: {e.stderr.decode() if e.stderr else str(e)}")
        return False, width, height, bitrate

def convert_to_resolution(input_path, output_dir, resolution, bitrate, encoder_settings):
    """Convierte el video a una resolución específica usando el codificador disponible"""
    width, height = resolution
    resolution_name = f"{height}p"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f'{resolution_name}.m3u8')
    segment_pattern = os.path.join(output_dir, f'{resolution_name}_%03d.ts')
    
    try:
        # Configurar stream de entrada
        stream = ffmpeg.input(input_path)
        
        # Separar los streams de video y audio
        video_stream = stream.video
        audio_stream = stream.audio
        
        # Aplicar escala manteniendo la relación de aspecto (solo al video)
        scaled_stream = video_stream.filter('scale', width=width, height=height, force_original_aspect_ratio='decrease')
        padded_stream = scaled_stream.filter('pad', width=width, height=height, x='(ow-iw)/2', y='(oh-ih)/2')
        
        # Obtener configuración del codificador
        encoder_args = apply_encoder_settings(padded_stream, encoder_settings)
        
        # Configurar los argumentos de salida
        output_args = {
            'b:v': bitrate,
            'c:a': 'aac',
            'b:a': '128k',
            'f': 'hls',
            'hls_time': '10',
            'hls_list_size': '0',
            'hls_segment_filename': segment_pattern,
            **encoder_args  # Integrar los argumentos del codificador
        }
        
        
        ffmpeg.output(padded_stream, audio_stream, output_path, **output_args).run(capture_stdout=True, capture_stderr=True)
        return True
    except ffmpeg.Error as e:
        print(f"Error durante la conversión: {e.stderr.decode() if e.stderr else str(e)}")
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
    playlist_path = os.path.join(output_dir, 'playlist.m3u8')
    with open(playlist_path, 'w') as f:
        f.write(master_playlist)
    print(f"Master playlist creado en: {playlist_path}")

def process_video(input_path, output_dir, rescale):
    """Procesa el video para las resoluciones apropiadas según la resolución original"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        # Obtener la resolución original del video
        original_width, original_height = get_video_resolution(input_path)
        # Obtener la configuración del codificador
        encoder_settings = get_video_encoder_settings()
        
        # Verificar si es un video de baja resolución
        if is_low_resolution(original_width, original_height):
            success, width, height, bitrate = segment_original_video(input_path, output_dir, encoder_settings)
            if success:
                # Crear master playlist con la única resolución disponible
                create_master_playlist(output_dir, [(width, height, bitrate)])
                print("¡Segmentación del video original completada!")
            else:
                raise Exception("Error al segmentar el video de baja resolución.")
            return
            
        # Definir las resoluciones estándar y sus bitrates para videos normales
        standard_resolutions = []
        print("Rescalado activado" if rescale else "Rescalado desactivado")
        
        # Agregar resoluciones basadas en la resolución original
        if original_height >= 1080 and rescale:
            standard_resolutions.extend([
                (1920, 1080, '5000k'),
                (1280, 720, '3000k'),
                (854, 480, '1000k')
            ])
        elif original_height >= 720 and rescale:
            standard_resolutions.extend([
                (1280, 720, '3000k'),
                (854, 480, '1000k')
            ])
        elif original_height >= 480 and rescale:
            standard_resolutions.append(
                (854, 480, '1000k')
            )
            
        # Si no hay resoluciones estándar o el video es cuadrado/vertical, procesar solo la original
        if not standard_resolutions or original_width <= original_height:
            success, width, height, bitrate = segment_original_video(input_path, output_dir, encoder_settings)
            if success:
                create_master_playlist(output_dir, [(width, height, bitrate)])
            else:
                raise Exception("Error al segmentar el video con formato especial.")
            return
            
        # Ejecutar conversiones en paralelo
        successful_resolutions = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for width, height, bitrate in standard_resolutions:
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
                except Exception as e:
                    print(f"Una conversión falló: {str(e)}")
                    
        # Crear el archivo master playlist con las resoluciones que fueron convertidas exitosamente
        if successful_resolutions:
            create_master_playlist(output_dir, successful_resolutions)
        else:
            raise Exception("No se completó ninguna conversión exitosamente.")
            
    except Exception as e:
        print(f"Error durante el procesamiento del video: {str(e)}")
        raise  # Relanzar la excepción para que sea manejada por el llamador

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convertir video a HLS con múltiples resoluciones')
    parser.add_argument('input', help='Ruta del archivo de video de entrada')
    parser.add_argument('output', help='Directorio de salida para los archivos HLS')
    parser.add_argument('--force-nvidia', action='store_true', help='Forzar uso de codificador NVIDIA')
    parser.add_argument('--force-amd', action='store_true', help='Forzar uso de codificador AMD')
    parser.add_argument('--force-cpu', action='store_true', help='Forzar uso de codificador CPU')
    parser.add_argument('--install-deps', action='store_true', help='Instalar dependencias necesarias')
    args = parser.parse_args()
    
    # Instalación de dependencias si se solicita
    if args.install_deps:
        print("Instalando dependencias necesarias...")
        try:
            import pip
            pip.main(['install', 'GPUtil', 'pynvml'])
            print("Dependencias instaladas correctamente")
        except Exception as e:
            print(f"Error al instalar dependencias: {str(e)}")
            print("Instalando solo dependencias esenciales...")
            try:
                import pip
                pip.main(['install', 'GPUtil'])
            except:
                print("No se pudieron instalar dependencias. El script intentará funcionar sin ellas.")
    
    print(f"Procesando archivo: {args.input}")
    print(f"Directorio de salida: {args.output}")
    
    # Opción para forzar el uso de un codificador específico
    if args.force_nvidia:
        print("Forzando uso de codificador NVIDIA")
        encoder_settings = {
            'codec': 'h264_nvenc',
            'preset': 'p4'
        }
        process_video(args.input, args.output)
    elif args.force_amd:
        print("Forzando uso de codificador AMD")
        encoder_settings = {
            'codec': 'h264_amf',
            'quality': 'balanced'
        }
        process_video(args.input, args.output)
    elif args.force_cpu:
        print("Forzando uso de codificador CPU")
        encoder_settings = {
            'codec': 'libx264',
            'preset': 'medium'
        }
        process_video(args.input, args.output)
    else:
        process_video(args.input, args.output)