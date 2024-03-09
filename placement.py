import os
import glob
import time
import uuid
import math
import socket

import contextlib

import gevent
from gevent import monkey; monkey.patch_all(thread=False, subprocess=False)

import ffmpeg



def progress_parser(sock, final_duration, progress_callback):
    connection, client_address = sock.accept()
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
    try:
        socket_path = os.path.join(os.getcwd(), '{}.sock'.format(uuid.uuid4()))
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(socket_path)
        sock.listen(1)
        listener = gevent.spawn(progress_parser, sock, final_duration, progress_callback)
        yield socket_path
    finally:
        try:
            listener.join()
        except:
            pass
        try:
            os.remove(socket_path)
        except:
            pass


def default_progress_callback(value, label=None):
    if label:
        print(f'START REPORTING ON {label}')
    for _ in range(value):
        print('+', end = '')
    for _ in range(value, 100):
        print('-', end = '')
    print()


def updateProgress(done, total, progress_callback):
    calculated_progress = math.floor((done / total)*100)
    print(f'CALCULATION IS DONE for {str(calculated_progress)}%: {str(done)} of {str(total)}')
    progress_callback(calculated_progress)
    return done+1


def create_slideshow(images_path_dir, audio_path, output_mp4_path, progress_callback=default_progress_callback):
    start_time = time.time()

    images_path_glob = os.path.join(images_path_dir, '*.jpeg')
    images_count = len(glob.glob(images_path_glob))
    audio_length = float(ffmpeg.probe(audio_path)['format']['duration'])
    image_rate = images_count / audio_length

    my_images = ffmpeg.input(
                    images_path_glob, pattern_type='glob', framerate=image_rate
                ).filter(
                    'scale', size='1920x1080', force_original_aspect_ratio='decrease'
                ).filter(
                    'pad', width=1920, height=1080, x='(ow-iw)/2', y='(oh-ih)/2', color='black'
                )
    my_audio = ffmpeg.input(audio_path)

    with get_progress_listener(audio_length, progress_callback) as progress_socket:
        ffmpeg.concat(
                my_images, my_audio, v=1, a=1
            ).output(
                output_mp4_path, **{'c:v': 'libx264', 'pix_fmt': 'yuv420p', 'color_range': 'pc', 'c:a': 'aac'} #'r': 24
            ).global_args('-progress', 'unix://{}'.format(progress_socket)
            ).overwrite_output().run(quiet=True)


    slideshow_length = float(ffmpeg.probe(output_mp4_path)['format']['duration'])
    updateProgress(slideshow_length, audio_length, default_progress_callback)
    end_time = time.time()
    execution_time = end_time - start_time

    print(f'Execution time: {str(execution_time)} seconds')



if __name__ == "__main__":
    my_images_f = '/Users/betty/PythonProjects/image_resize/photos'
    my_audio_f = 'my_audio.mp3'
    my_slides_f = 'ffmpeg_raw.mp4'

    create_slideshow(my_images_f, my_audio_f, my_slides_f)

    print(f"MP4 slideshow '{my_slides_f}' has been created with images and audio.")
