import os
import sys
import time
import logging
import ffmpeg
import concurrent.futures
import subprocess
import argparse
import traceback
from typing import Dict, Tuple, List, Optional, Any, Union
from pathlib import Path

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('hls_utils.log')
    ]
)
logger = logging.getLogger('hls_utils')

# Constantes
MAX_RETRIES = 3
RETRY_DELAY = 2  # segundos

class EncoderSettings:
    """Clase para manejar la configuración de codificadores"""
    def __init__(self, codec: str, preset: Optional[str] = None, quality: Optional[str] = None):
        self.codec = codec
        self.preset = preset
        self.quality = quality

    def get_output_args(self) -> Dict[str, str]:
        """Devuelve los argumentos para ffmpeg según el codec configurado"""
        output_args = {'c:v': self.codec}
        
        if self.codec == 'h264_nvenc' and self.preset:
            output_args['preset'] = self.preset
        elif self.codec == 'h264_amf' and self.quality:
            output_args['quality'] = self.quality
        elif self.codec == 'libx264' and self.preset:
            output_args['preset'] = self.preset
        
        return output_args

def safe_execute(func, *args, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY, **kwargs):
    """Ejecuta una función con reintentos en caso de fallo"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Mostrar el error detallado si es un error de ffmpeg
            if hasattr(e, 'stderr') and e.stderr:
                logger.error(f"Error de ffmpeg: {e.stderr.decode('utf-8', errors='replace')}")
            
            if attempt < max_retries - 1:
                logger.warning(f"Intento {attempt+1} fallido: {str(e)}. Reintentando en {retry_delay} segundos...")
                time.sleep(retry_delay)
                # Aumentamos el tiempo de espera para cada reintento
                retry_delay *= 1.5
            else:
                logger.error(f"Todos los intentos fallaron: {str(e)}")
                logger.error(traceback.format_exc())
                raise

def detect_gpus() -> Dict[str, bool]:
    """Detecta GPUs disponibles usando bibliotecas de Python de manera multiplataforma"""
    gpu_info = {
        'nvidia': False,
        'amd': False
    }
    
    # Primero comprobamos si ffmpeg tiene los codificadores disponibles
    # Esta es la manera más confiable de verificar si podemos usar aceleración por hardware
    ffmpeg_check = _detect_gpus_with_ffmpeg()
    gpu_info['nvidia'] = ffmpeg_check.get('nvidia', False)
    gpu_info['amd'] = ffmpeg_check.get('amd', False)
    
    # Solo si no se detectaron codificadores en ffmpeg, intentamos otros métodos
    if not (gpu_info['nvidia'] or gpu_info['amd']):
        detection_methods = [
            _detect_gpus_with_gputil,
            _detect_gpus_with_pynvml
        ]
        
        for method in detection_methods:
            try:
                method_gpu_info = method()
                gpu_info['nvidia'] = gpu_info['nvidia'] or method_gpu_info.get('nvidia', False)
                gpu_info['amd'] = gpu_info['amd'] or method_gpu_info.get('amd', False)
                
                # Si ya detectamos ambas GPUs, podemos salir
                if gpu_info['nvidia'] and gpu_info['amd']:
                    break
            except Exception as e:
                logger.debug(f"Método de detección de GPU falló: {str(e)}")
    
    return gpu_info

def _detect_gpus_with_gputil() -> Dict[str, bool]:
    """Detecta GPUs usando la biblioteca GPUtil"""
    gpu_info = {'nvidia': False, 'amd': False}
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        for gpu in gpus:
            if 'nvidia' in gpu.name.lower():
                gpu_info['nvidia'] = True
                logger.info(f"GPU NVIDIA detectada via GPUtil: {gpu.name}")
            elif any(amd_keyword in gpu.name.lower() for amd_keyword in ['amd', 'radeon', 'vega', 'rx']):
                gpu_info['amd'] = True
                logger.info(f"GPU AMD detectada via GPUtil: {gpu.name}")
    except ImportError:
        logger.debug("GPUtil no está instalado")
    except Exception as e:
        logger.debug(f"Error al detectar GPUs con GPUtil: {str(e)}")
    return gpu_info

def _detect_gpus_with_pynvml() -> Dict[str, bool]:
    """Detecta GPUs NVIDIA usando la biblioteca pynvml"""
    gpu_info = {'nvidia': False, 'amd': False}
    try:
        import pynvml
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count > 0:
            gpu_info['nvidia'] = True
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            logger.info(f"GPU NVIDIA detectada via NVML: {pynvml.nvmlDeviceGetName(handle).decode()}")
        pynvml.nvmlShutdown()
    except ImportError:
        logger.debug("NVML no está instalado")
    except Exception as e:
        logger.debug(f"Error al detectar GPUs con NVML: {str(e)}")
    return gpu_info

def _detect_gpus_with_ffmpeg() -> Dict[str, bool]:
    """Detecta GPUs verificando si los codificadores están disponibles en ffmpeg"""
    gpu_info = {'nvidia': False, 'amd': False}
    try:
        ffmpeg_encoders = subprocess.run(
            ['ffmpeg', '-encoders'], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            timeout=10  # Timeout para evitar bloqueos
        )
        encoders_output = ffmpeg_encoders.stdout.decode()
        
        # Verificar si el codificador realmente está disponible
        if 'h264_nvenc' in encoders_output:
            # Prueba adicional para verificar que realmente funciona
            test_cmd = [
                'ffmpeg', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=duration=1:size=128x96:rate=1', 
                '-c:v', 'h264_nvenc', '-f', 'null', '-'
            ]
            try:
                test_result = subprocess.run(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
                if test_result.returncode == 0:
                    gpu_info['nvidia'] = True
                    logger.info("Codificador NVIDIA h264_nvenc verificado y funcionando")
                else:
                    logger.warning(f"Codificador NVIDIA h264_nvenc detectado pero no funciona correctamente: {test_result.stderr.decode()}")
            except Exception as e:
                logger.warning(f"Codificador NVIDIA h264_nvenc detectado pero falló la prueba: {str(e)}")
            
        if 'h264_amf' in encoders_output:
            # Prueba adicional para AMD
            test_cmd = [
                'ffmpeg', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=duration=1:size=128x96:rate=1', 
                '-c:v', 'h264_amf', '-f', 'null', '-'
            ]
            try:
                test_result = subprocess.run(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
                if test_result.returncode == 0:
                    gpu_info['amd'] = True
                    logger.info("Codificador AMD h264_amf verificado y funcionando")
                else:
                    logger.warning(f"Codificador AMD h264_amf detectado pero no funciona correctamente: {test_result.stderr.decode()}")
            except Exception as e:
                logger.warning(f"Codificador AMD h264_amf detectado pero falló la prueba: {str(e)}")
    except subprocess.TimeoutExpired:
        logger.warning("Timeout al ejecutar ffmpeg -encoders")
    except Exception as e:
        logger.debug(f"Error al verificar codificadores en ffmpeg: {str(e)}")
    return gpu_info

def get_video_encoder_settings(force_nvidia=False, force_amd=False, force_cpu=False) -> EncoderSettings:
    """Determina los ajustes de codificación según la disponibilidad de GPU"""
    if force_cpu:
        logger.info("Forzando uso de codificador CPU")
        return EncoderSettings(codec='libx264', preset='medium')
    
    # Si hay forzado específico, primero intentar verificar que funcione realmente
    if force_nvidia:
        logger.info("Comprobando disponibilidad de codificador NVIDIA forzado")
        gpu_info = _detect_gpus_with_ffmpeg()
        if gpu_info['nvidia']:
            logger.info("Forzando uso de codificador NVIDIA (verificado)")
            return EncoderSettings(codec='h264_nvenc', preset='p4')
        else:
            logger.warning("Codificador NVIDIA forzado no está disponible, usando CPU")
            return EncoderSettings(codec='libx264', preset='medium')
    
    if force_amd:
        logger.info("Comprobando disponibilidad de codificador AMD forzado")
        gpu_info = _detect_gpus_with_ffmpeg()
        if gpu_info['amd']:
            logger.info("Forzando uso de codificador AMD (verificado)")
            return EncoderSettings(codec='h264_amf', quality='balanced')
        else:
            logger.warning("Codificador AMD forzado no está disponible, usando CPU")
            return EncoderSettings(codec='libx264', preset='medium')
    
    # Si no se fuerza ningún codificador, detectar automáticamente
    gpu_info = detect_gpus()
    
    if gpu_info['nvidia']:
        logger.info("GPU NVIDIA detectada, usando aceleración por hardware NVENC")
        return EncoderSettings(codec='h264_nvenc', preset='p4')
    elif gpu_info['amd']:
        logger.info("GPU AMD detectada, usando aceleración por hardware AMF")
        return EncoderSettings(codec='h264_amf', quality='balanced')
    else:
        logger.info("No se detectó GPU compatible, usando codificación por CPU")
        return EncoderSettings(codec='libx264', preset='medium')

def get_video_resolution(input_path: str) -> Tuple[int, int]:
    """Obtiene la resolución original del video usando ffprobe"""
    try:
        probe = ffmpeg.probe(input_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream is None:
            raise ValueError("No se encontró una pista de video en el archivo")
            
        width = int(video_stream['width'])
        height = int(video_stream['height'])
        logger.info(f"Resolución original del video: {width}x{height}")
        return width, height
    except Exception as e:
        logger.error(f"Error al obtener la resolución del video: {str(e)}")
        logger.error(traceback.format_exc())
        # Valor predeterminado alto para procesar todas las resoluciones
        logger.warning("Usando resolución predeterminada de 1920x1080")
        return 1920, 1080

def is_low_resolution(width: int, height: int) -> bool:
    """Determina si el video tiene una resolución baja (menor que 480p)"""
    return height < 480 and width < 854

def is_valid_video_file(input_path: str) -> bool:
    """Verifica si el archivo de entrada es un video válido"""
    try:
        probe = ffmpeg.probe(input_path, select_streams='v')
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        return video_stream is not None
    except Exception as e:
        logger.error(f"Error al validar el archivo de video: {str(e)}")
        return False

def segment_original_video(
    input_path: str, 
    output_dir: str, 
    encoder_settings: EncoderSettings
) -> Tuple[bool, int, int, str]:
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
        encoder_args = encoder_settings.get_output_args()
        
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
        logger.info(f"Procesando video original en segmentos HLS de 10 segundos...")
        logger.info(f"Argumentos de salida: {output_args}")
        
        def segment_video():
            # Generar el comando para poder imprimirlo en caso de error
            cmd = ffmpeg.output(stream, output_path, **output_args)
            logger.debug(f"Comando ffmpeg: {cmd.compile()}")
            
            try:
                stdout, stderr = cmd.run(
                    capture_stdout=True, 
                    capture_stderr=True,
                    overwrite_output=True
                )
                return stdout, stderr
            except ffmpeg.Error as e:
                # Mostrar la salida de error completa de ffmpeg
                if e.stderr:
                    logger.error(f"Error de ffmpeg: {e.stderr.decode('utf-8', errors='replace')}")
                raise
        
        # Ejecutar con reintentos
        safe_execute(segment_video)
        return True, width, height, bitrate
    except Exception as e:
        logger.error(f"Error durante la segmentación: {str(e)}")
        logger.error(traceback.format_exc())
        return False, width, height, bitrate

def convert_to_resolution(
    input_path: str, 
    output_dir: str, 
    resolution: Tuple[int, int], 
    bitrate: str, 
    encoder_settings: EncoderSettings
) -> bool:
    """Convierte el video a una resolución específica usando el codificador disponible"""
    width, height = resolution
    resolution_name = f"{height}p"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f'{resolution_name}.m3u8')
    segment_pattern = os.path.join(output_dir, f'{resolution_name}_%03d.ts')
    
    try:
        # Configurar stream de entrada
        stream = ffmpeg.input(input_path)
        
        # Verificar si el stream de entrada tiene audio
        has_audio = False
        try:
            probe = ffmpeg.probe(input_path)
            for stream_info in probe['streams']:
                if stream_info['codec_type'] == 'audio':
                    has_audio = True
                    break
        except Exception as e:
            logger.warning(f"No se pudo verificar la presencia de audio: {str(e)}")
        
        # Separar los streams de video y audio si hay audio
        video_stream = stream.video
        
        # Aplicar escala manteniendo la relación de aspecto (solo al video)
        scaled_stream = video_stream.filter('scale', width=width, height=height, force_original_aspect_ratio='decrease')
        padded_stream = scaled_stream.filter('pad', width=width, height=height, x='(ow-iw)/2', y='(oh-ih)/2')
        
        # Obtener configuración del codificador
        encoder_args = encoder_settings.get_output_args()
        
        # Configurar los argumentos de salida
        output_args = {
            'b:v': bitrate,
            'f': 'hls',
            'hls_time': '10',
            'hls_list_size': '0',
            'hls_segment_filename': segment_pattern,
            **encoder_args  # Integrar los argumentos del codificador
        }
        
        # Añadir configuración de audio si existe
        if has_audio:
            audio_stream = stream.audio
            output_args['c:a'] = 'aac'
            output_args['b:a'] = '128k'
            
            def convert_with_audio():
                cmd = ffmpeg.output(padded_stream, audio_stream, output_path, **output_args)
                logger.debug(f"Comando ffmpeg: {cmd.compile()}")
                
                try:
                    stdout, stderr = cmd.run(
                        capture_stdout=True, 
                        capture_stderr=True,
                        overwrite_output=True
                    )
                    return stdout, stderr
                except ffmpeg.Error as e:
                    if e.stderr:
                        logger.error(f"Error de ffmpeg: {e.stderr.decode('utf-8', errors='replace')}")
                    raise
            
            # Ejecutar con reintentos
            safe_execute(convert_with_audio)
        else:
            logger.warning(f"No se detectó audio en el video. Procesando solo video.")
            
            def convert_without_audio():
                cmd = ffmpeg.output(padded_stream, output_path, **output_args)
                logger.debug(f"Comando ffmpeg: {cmd.compile()}")
                
                try:
                    stdout, stderr = cmd.run(
                        capture_stdout=True, 
                        capture_stderr=True,
                        overwrite_output=True
                    )
                    return stdout, stderr
                except ffmpeg.Error as e:
                    if e.stderr:
                        logger.error(f"Error de ffmpeg: {e.stderr.decode('utf-8', errors='replace')}")
                    raise
            
            # Ejecutar con reintentos
            safe_execute(convert_without_audio)
        
        return True
    except Exception as e:
        logger.error(f"Error durante la conversión a {resolution_name}: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def create_master_playlist(
    output_dir: str, 
    available_resolutions: List[Tuple[int, int, str]]
) -> bool:
    """Crea el archivo master playlist.m3u8 con las resoluciones disponibles"""
    if not available_resolutions:
        logger.error("No hay resoluciones disponibles para crear el master playlist")
        return False
    
    master_playlist = "#EXTM3U\n"
    
    # Ordenar resoluciones de mayor a menor para el playlist
    resolutions_sorted = sorted(available_resolutions, key=lambda x: x[1], reverse=True)
    
    for width, height, bitrate in resolutions_sorted:
        # Convertir el bitrate a un valor numérico en bits por segundo
        bitrate_value = int(bitrate.replace('k', '000'))
        
        # Verificar que el archivo de la resolución específica existe
        resolution_file = os.path.join(output_dir, f'{height}p.m3u8')
        if not os.path.exists(resolution_file):
            logger.warning(f"El archivo {resolution_file} no existe, se omitirá del master playlist")
            continue
        
        master_playlist += f"#EXT-X-STREAM-INF:BANDWIDTH={bitrate_value},RESOLUTION={width}x{height}\n"
        master_playlist += f"{height}p.m3u8\n"
    
    os.makedirs(output_dir, exist_ok=True)
    logger.info("Creando playlist master...")
    playlist_path = os.path.join(output_dir, 'playlist.m3u8')
    
    try:
        with open(playlist_path, 'w') as f:
            f.write(master_playlist)
        logger.info(f"Master playlist creado en: {playlist_path}")
        return True
    except Exception as e:
        logger.error(f"Error al crear el master playlist: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def fallback_to_original(
    input_path: str, 
    output_dir: str, 
    encoder_settings: EncoderSettings
) -> bool:
    """Función de respaldo que intenta procesar el video en su resolución original"""
    logger.warning("Usando método de respaldo para procesar el video con libx264 (CPU)")
    try:
        # Usar explícitamente el codificador de CPU
        cpu_encoder = EncoderSettings(codec='libx264', preset='medium')
        
        success, width, height, bitrate = segment_original_video(input_path, output_dir, cpu_encoder)
        if success:
            create_master_playlist(output_dir, [(width, height, bitrate)])
            logger.info("El método de respaldo se completó correctamente")
            return True
        else:
            # Intentar con el codificador más básico posible
            logger.warning("Intentando con codificador de último recurso...")
            basic_encoder = EncoderSettings(codec='libx264', preset='ultrafast')
            success, width, height, bitrate = segment_original_video(input_path, output_dir, basic_encoder)
            if success:
                create_master_playlist(output_dir, [(width, height, bitrate)])
                logger.info("El método de respaldo con codificador básico se completó correctamente")
                return True
            else:
                logger.error("El método de respaldo falló al segmentar el video incluso con codificador básico")
                return False
    except Exception as e:
        logger.error(f"Error durante el procesamiento de respaldo: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def process_video(
    input_path: str, 
    output_dir: str, 
    rescale: bool = True,
    force_nvidia: bool = False,
    force_amd: bool = False,
    force_cpu: bool = False
) -> bool:
    """Procesa el video para las resoluciones apropiadas según la resolución original"""
    try:
        # Validar que el archivo de entrada existe
        if not os.path.exists(input_path):
            logger.error(f"El archivo de entrada no existe: {input_path}")
            return False
        
        # Validar que el archivo de entrada es un video válido
        if not is_valid_video_file(input_path):
            logger.error(f"El archivo no es un video válido: {input_path}")
            return False
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Obtener la resolución original del video
        original_width, original_height = get_video_resolution(input_path)
        
        # Obtener la configuración del codificador
        encoder_settings = get_video_encoder_settings(force_nvidia, force_amd, force_cpu)
        
        # Si el usuario forzó CPU, asegurarnos de usar libx264
        if force_cpu:
            encoder_settings = EncoderSettings(codec='libx264', preset='medium')
        
        # Verificar si es un video de baja resolución
        if is_low_resolution(original_width, original_height):
            logger.info("Video de baja resolución detectado, procesando solo en resolución original")
            success, width, height, bitrate = segment_original_video(input_path, output_dir, encoder_settings)
            if success:
                # Crear master playlist con la única resolución disponible
                create_master_playlist(output_dir, [(width, height, bitrate)])
                logger.info("¡Segmentación del video original completada!")
                return True
            else:
                logger.error("Error al segmentar el video de baja resolución. Intentando método alternativo.")
                return fallback_to_original(input_path, output_dir, encoder_settings)
            
        # Definir las resoluciones estándar y sus bitrates para videos normales
        standard_resolutions = []
        logger.info("Rescalado activado" if rescale else "Rescalado desactivado")
        
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
            logger.info("Video con formato especial o rescalado desactivado, procesando solo en resolución original")
            success, width, height, bitrate = segment_original_video(input_path, output_dir, encoder_settings)
            if success:
                create_master_playlist(output_dir, [(width, height, bitrate)])
                return True
            else:
                logger.error("Error al segmentar el video con formato especial. Intentando método alternativo.")
                return fallback_to_original(input_path, output_dir, encoder_settings)
            
        # Ejecutar conversiones en paralelo
        successful_resolutions = []
        failed_conversions = []
        
        # Determinar el número óptimo de workers según el hardware disponible
        max_workers = min(3, os.cpu_count() or 2)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
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
                    else:
                        failed_conversions.append(resolution)
                except Exception as e:
                    logger.error(f"Error en la conversión a {resolution[1]}p: {str(e)}")
                    failed_conversions.append(resolution)
        
        # Registro de resultados
        if successful_resolutions:
            logger.info(f"Conversiones exitosas: {', '.join([f'{r[1]}p' for r in successful_resolutions])}")
        if failed_conversions:
            logger.warning(f"Conversiones fallidas: {', '.join([f'{r[1]}p' for r in failed_conversions])}")
            
        # Si todas las conversiones fallaron, intentar con el video original
        if not successful_resolutions:
            logger.warning("Todas las conversiones fallaron. Procesando solo el video original.")
            
            # Intentar con el codificador de CPU para mayor compatibilidad
            cpu_encoder = EncoderSettings(codec='libx264', preset='medium')
            logger.info("Cambiando a codificador CPU para mayor compatibilidad")
            
            success, width, height, bitrate = segment_original_video(input_path, output_dir, cpu_encoder)
            if success:
                create_master_playlist(output_dir, [(width, height, bitrate)])
                return True
            else:
                logger.error("No se pudo procesar el video ni siquiera en su resolución original con CPU.")
                return fallback_to_original(input_path, output_dir, cpu_encoder)
                
        # Crear el archivo master playlist con las resoluciones que fueron convertidas exitosamente
        if successful_resolutions:
            success = create_master_playlist(output_dir, successful_resolutions)
            return success
        else:
            logger.error("No se completó ninguna conversión exitosamente.")
            return False
            
    except Exception as e:
        logger.error(f"Error durante el procesamiento del video: {str(e)}")
        logger.error(traceback.format_exc())
        # Intentar método de respaldo
        return fallback_to_original(input_path, output_dir, get_video_encoder_settings(force_nvidia, force_amd, force_cpu))

def verify_ffmpeg_installed() -> bool:
    """Verifica que ffmpeg esté instalado en el sistema"""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False
        
def install_dependencies():
    """Intenta instalar las dependencias de Python necesarias"""
    try:
        import pip
        logger.info("Instalando dependencias...")
        pip.main(['install', '--upgrade', 'GPUtil', 'pynvml'])
        logger.info("Dependencias instaladas correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al instalar dependencias: {str(e)}")
        try:
            logger.info("Intentando instalar solo dependencias esenciales...")
            import pip
            pip.main(['install', '--upgrade', 'GPUtil'])
            return True
        except:
            logger.error("No se pudieron instalar dependencias")
            return False

def main():
    parser = argparse.ArgumentParser(description='Convertir video a HLS con múltiples resoluciones')
    parser.add_argument('input', help='Ruta del archivo de video de entrada')
    parser.add_argument('output', help='Directorio de salida para los archivos HLS')
    parser.add_argument('--force-nvidia', action='store_true', help='Forzar uso de codificador NVIDIA')
    parser.add_argument('--force-amd', action='store_true', help='Forzar uso de codificador AMD')
    parser.add_argument('--force-cpu', action='store_true', help='Forzar uso de codificador CPU')
    parser.add_argument('--no-rescale', action='store_true', help='No rescalar a resoluciones estándar')
    parser.add_argument('--install-deps', action='store_true', help='Instalar dependencias necesarias')
    parser.add_argument('--verbose', '-v', action='store_true', help='Mostrar información detallada')
    
    args = parser.parse_args()
    
    # Configurar nivel de logging según verbosidad
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Verificar si ffmpeg está instalado
    if not verify_ffmpeg_installed():
        logger.error("ffmpeg no está instalado en el sistema. Este programa requiere ffmpeg para funcionar.")
        return 1
    
    # Instalación de dependencias si se solicita
    if args.install_deps:
        if not install_dependencies():
            logger.warning("No se pudieron instalar todas las dependencias. El script intentará funcionar sin ellas.")
    
    # Normalizar y validar rutas
    input_path = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)
    
    logger.info(f"Procesando archivo: {input_path}")
    logger.info(f"Directorio de salida: {output_dir}")
    
    # Procesar el video con parámetros especificados
    success = process_video(
        input_path=input_path,
        output_dir=output_dir,
        rescale=not args.no_rescale,
        force_nvidia=args.force_nvidia,
        force_amd=args.force_amd,
        force_cpu=args.force_cpu
    )
    
    if success:
        logger.info("¡Procesamiento de video completado con éxito!")
        return 0
    else:
        logger.error("El procesamiento de video falló.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
