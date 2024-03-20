import os
import time
import math
import random
import string
import socket

import contextlib


import threading

# import gevent
# from gevent import monkey; monkey.patch_all(thread=False, subprocess=False)

import ffmpeg


def progress_parser(sock, final_duration, progress_callback):
    sock.settimeout(10)
    try:
        connection, client_address = sock.accept()
    except socket.timeout:
        print("Timeout occurred while waiting for a connection")
        return

    data = b''
    try:
        while True:
            more_data = connection.recv(16)
            if not more_data:
                break
            data += more_data
            lines = data.split(b'\n')
            for line in lines[:-1]:
                line = line.decode()
                parts = line.split('=')
                key = parts[0] if len(parts) > 0 else None
                value = parts[1] if len(parts) > 1 else None
                if key == 'out_time_ms':
                    duration = int(value) / 1000000 if value.isdigit() else 0
                    updateProgress(duration, final_duration, progress_callback)
            data = lines[-1]
    finally:
        connection.close()




@contextlib.contextmanager
def get_progress_listener(final_duration, progress_callback):
    HOST = 'localhost'  # Standard loopback interface address (localhost)
    PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
    sock = type("Closable", (object,), {"close": lambda self: "closed"})
    listener = type("Joinable", (object,), {"join": lambda self: "joined"})

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((HOST, PORT))
        socket_path = '{}:{:d}/{}/{}'.format(
            HOST, PORT, 'slideshowcreator',
            ''.join(random.choices(string.ascii_lowercase, k=8)))
        sock.listen(1)
        listener = threading.Thread(target=progress_parser, args=(sock, final_duration, progress_callback))
        listener.start()
        yield socket_path
    finally:
        with contextlib.suppress(Exception):
            listener.join()
        with contextlib.suppress(Exception):
            sock.close()



def default_progress_callback(value, label=None):
    if label:
        print(f'START REPORTING ON {label}')
    for _ in range(value):
        print('+', end = '')
    for _ in range(value, 100):
        print('-', end = '')
    print()


def updateProgress(done, total, progress_callback):
    calculated_progress = min(100, math.ceil((done / total)*100))
    print(f'CALCULATION IS DONE for {str(calculated_progress)}%: {str(done)} of {str(total)}')
    progress_callback(calculated_progress)
    return calculated_progress


def create_slideshow(images_path_dir, audio_path, output_mp4_path, progress_callback=default_progress_callback):
    start_time = time.time()

    images_path_arr = [
        os.path.join(images_path_dir, filename) for
        filename in os.listdir(images_path_dir) if
        filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp'))
    ]

    images_count = len(images_path_arr)
    audio_length = float(ffmpeg.probe(audio_path)['format']['duration'])
    image_rate = images_count / audio_length
    image_fps = image_rate*10

    my_audio = ffmpeg.input(audio_path)

    images_stream_arr = [
        ffmpeg.input(
            filename, r = image_rate
        ).filter(
            'scale', size='1920x1080', force_original_aspect_ratio='decrease'
        ).filter(
            'pad', width=1920, height=1080, x='(ow-iw)/2', y='(oh-ih)/2', color='black'
        ).filter(
            'setsar', ratio=1
        ).filter(
            'fps', fps = image_fps
        ) for filename in images_path_arr
    ]

    images_concat = ffmpeg.concat(*images_stream_arr)
    images_audio = ffmpeg.concat(images_concat, my_audio, v=1, a=1)

    video_output = ffmpeg.output(
        images_audio, output_mp4_path, **{'c:v': 'libx264', 'pix_fmt': 'yuv420p', 'color_range': 'pc', 'c:a': 'aac', 'r': 1}
    ).overwrite_output()

    with get_progress_listener(audio_length, progress_callback) as progress_socket:
        video_output.global_args(
            '-progress', 'http://{}'.format(progress_socket)
        ).run(
            quiet=True
        )


    slideshow_length = float(ffmpeg.probe(output_mp4_path)['format']['duration'])
    updateProgress(slideshow_length, audio_length, default_progress_callback)

    end_time = time.time()
    execution_time = end_time - start_time

    print(f'Execution time: {str(execution_time)} seconds')


if __name__ == "__main__":
    my_images_f = '/Users/betty/PythonProjects/image_resize/photos'
    my_audio_f = '/Users/betty/PythonProjects/slide_show/my_audio.mp3'
    my_slides_f = 'ffmpeg_raw.mp4'

    create_slideshow(my_images_f, my_audio_f, my_slides_f)

    print(f"MP4 slideshow '{my_slides_f}' has been created with images and audio.")
