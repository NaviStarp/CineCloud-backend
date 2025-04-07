import os
import subprocess

def process_video_to_hls_multi_quality(input_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    command = [
        'ffmpeg', '-i', input_path,
        '-filter_complex',
        "[0:v]split=3[v1][v2][v3];" +
        "[v1]scale=w=1920:h=1080[v1out];" +
        "[v2]scale=w=1280:h=720[v2out];" +
        "[v3]scale=w=854:h=480[v3out]",
        '-map', '[v1out]', '-c:v:0', 'libx264', '-b:v:0', '5000k',
        '-f', 'hls', '-hls_time', '10', '-hls_list_size', '0',
        '-hls_segment_filename', os.path.join(output_dir, '1080p_%03d.ts'), os.path.join(output_dir, '1080p.m3u8'),
        '-map', '[v2out]', '-c:v:1', 'libx264', '-b:v:1', '3000k',
        '-f', 'hls', '-hls_time', '10', '-hls_list_size', '0',
        '-hls_segment_filename', os.path.join(output_dir, '720p_%03d.ts'), os.path.join(output_dir, '720p.m3u8'),
        '-map', '[v3out]', '-c:v:2', 'libx264', '-b:v:2', '1000k',
        '-f', 'hls', '-hls_time', '10', '-hls_list_size', '0',
        '-hls_segment_filename', os.path.join(output_dir, '480p_%03d.ts'), os.path.join(output_dir, '480p.m3u8'),
    ]

    subprocess.run(command, check=True)
    master_playlist = """#EXTM3U
    #EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080
    1080p.m3u8
    #EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720
    720p.m3u8
    #EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=854x480
    480p.m3u8
    """

    with open(os.path.join(output_dir, 'playlist.m3u8'), 'w') as f:
        f.write(master_playlist)
