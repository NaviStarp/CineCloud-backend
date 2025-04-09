import os
import subprocess

def convert_to_1080p(input_path, output_dir):
    """Convierte el video a calidad 1080p HLS"""
    os.makedirs(output_dir, exist_ok=True)
    command = [
        'ffmpeg', '-i', input_path,
        '-vf', 'scale=w=1920:h=1080',
        '-c:v', 'libx264', '-b:v', '5000k',
        '-c:a', 'aac', '-b:a', '128k',
        '-f', 'hls', '-hls_time', '10', '-hls_list_size', '0',
        '-hls_segment_filename', os.path.join(output_dir, '1080p_%03d.ts'),
        os.path.join(output_dir, '1080p.m3u8')
    ]
    print("Procesando 1080p...")
    try:
        subprocess.run(command, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion: {e.stderr.decode()}")
        raise
def convert_to_720p(input_path, output_dir):
    """Convierte el video a calidad 720p HLS"""
    os.makedirs(output_dir, exist_ok=True)
    """Convierte el video a calidad 720p HLS"""
    command = [
        'ffmpeg', '-i', input_path,
        '-vf', 'scale=w=1280:h=720',
        '-c:v', 'libx264', '-b:v', '3000k',
        '-c:a', 'aac', '-b:a', '128k',
        '-f', 'hls', '-hls_time', '10', '-hls_list_size', '0',
        '-hls_segment_filename', os.path.join(output_dir, '720p_%03d.ts'),
        os.path.join(output_dir, '720p.m3u8')
    ]
    print("Procesando 720p...")
def convert_to_480p(input_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    """Convierte el video a calidad 480p HLS"""
    command = [
        'ffmpeg', '-i', input_path,
        '-vf', 'scale=w=854:h=480',
        '-c:v', 'libx264', '-b:v', '1000k',
        '-c:a', 'aac', '-b:a', '128k',
        '-f', 'hls', '-hls_time', '10', '-hls_list_size', '0',
        '-hls_segment_filename', os.path.join(output_dir, '480p_%03d.ts'),
        os.path.join(output_dir, '480p.m3u8')
    ]
    print("Procesando 480p...")
    subprocess.run(command, check=True)

def create_master_playlist(output_dir):
    """Crea el archivo master playlist.m3u8"""
    master_playlist = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080
1080p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720
720p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=854x480
480p.m3u8
"""
    print("Creando playlist master...")
    with open(os.path.join(output_dir, 'playlist.m3u8'), 'w') as f:
        f.write(master_playlist)