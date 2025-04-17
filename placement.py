import logging
import mimetypes
import os
import time
from typing import Callable, Optional

import math
import socket

import contextlib

import threading

import ffmpeg

logger = logging.getLogger(__name__)


def progress_parser(sock: socket.socket, final_duration: float, progress_callback: Callable):
    sock.settimeout(10)
    try:
        connection, client_address = sock.accept()
    except socket.timeout:
        logger.error("Timeout occurred while waiting for a connection")
        return

    data = b''
    try:
        while True:
            more_data = connection.recv(16)
            if not more_data:
                break
            data += more_data
            bin_lines = data.split(b'\n')
            for bin_line in bin_lines[:-1]:
                line = bin_line.decode()
                parts = line.split('=')
                key = parts[0] if len(parts) > 0 else None
                value = parts[1] if len(parts) > 1 else None
                if key == 'out_time_ms':
                    duration = int(value) / 1000000 if value.isdigit() else 0
                    update_progress(duration, final_duration, progress_callback)
            data = bin_lines[-1]
    finally:
        connection.close()




@contextlib.contextmanager
def get_progress_listener(final_duration: float, progress_callback: Callable):
    sock = type("Closable", (object,), {"close": lambda self: "closed"})
    listener = type("Joinable", (object,), {"join": lambda self: "joined"})

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        listen_on = '{}:{:d}'.format(*sock.getsockname())
        sock.listen(1)
        listener = threading.Thread(target=progress_parser, args=(sock, final_duration, progress_callback))
        listener.start()
        yield listen_on
    finally:
        with contextlib.suppress(Exception):
            listener.join()
        with contextlib.suppress(Exception):
            sock.close()



def default_progress_callback(value: int, label: Optional[str]=None):
    if label:
        logger.debug(f'START REPORTING ON {label}')
    for _ in range(value):
        print('+', end = '')
    for _ in range(value, 100):
        print('-', end = '')
    print()


def update_progress(done: float, total: float, progress_callback: Callable) -> int:
    calculated_progress = min(100, math.ceil((done / total)*100))
    logger.debug(f'CALCULATION IS DONE for {calculated_progress}%: {done} of {total}')
    progress_callback(calculated_progress)
    return calculated_progress


def is_valid_image(file_path):
    logger.debug(f'checking {file_path}')
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type.startswith('image'):
        logger.debug(f'{file_path} is a valid image by mimetype')
        return True
    # If mimetype didn't recognize, try probing with ffmpeg
    try:
        probe_info = ffmpeg.probe(file_path)
        if probe_info['streams'][0]['codec_type'] == 'video':
            logger.debug(f'{file_path} is a valid image by probe_info')
            return True
    except ffmpeg.Error:
        pass
    logger.warning(f'{file_path} is not a valid image')
    return False


def create_slideshow(images_path_dir: str, audio_path: str, output_mp4_path: str,
                         progress_callback: Callable = default_progress_callback):
    start_time = time.time()

    images_path_arr = [
        filepath for filename in os.listdir(images_path_dir) if
        is_valid_image(filepath := os.path.join(images_path_dir, filename))
    ]

    images_count = len(images_path_arr)
    audio_length = float(ffmpeg.probe(audio_path)['format']['duration'])
    image_rate = images_count / audio_length
    image_fps = image_rate*10

    logger.info(f'Audio length: {audio_length}, Images count: {images_count}')
    logger.debug(f'Image rate: {image_rate}, Image fps: {image_fps}')

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
        images_audio, output_mp4_path,
        **{'c:v': 'libx264', 'pix_fmt': 'yuv420p', 'color_range': 'pc', 'c:a': 'aac', 'r': 1}
    ).overwrite_output()

    with get_progress_listener(audio_length, progress_callback) as progress_socket:
        video_output.global_args(
            '-progress', 'http://{}'.format(progress_socket)
        ).run(
            quiet=True
        )


    slideshow_length = float(ffmpeg.probe(output_mp4_path)['format']['duration'])
    logger.info(f'Created slideshow length: {slideshow_length}')
    update_progress(slideshow_length, audio_length, progress_callback)

    end_time = time.time()
    execution_time = end_time - start_time

    print(f'Execution time: {execution_time} seconds')


if __name__ == "__main__":
    my_images_f = '/Users/betty/PythonProjects/image_resize/photos'
    my_audio_f = '/Users/betty/PythonProjects/slide_show/my_audio.mp3'
    my_slides_f = 'ffmpeg_raw.mp4'

    create_slideshow(my_images_f, my_audio_f, my_slides_f)

    print(f"MP4 slideshow '{my_slides_f}' has been created with images and audio.")
