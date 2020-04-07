'''Example streaming ffmpeg numpy processing.

Demonstrates using ffmpeg to decode video input, process the frames in
python, and then encode video output using ffmpeg.

This example uses two ffmpeg processes - one to decode the input video
and one to encode an output video - while the raw frame processing is
done in python with numpy.

At a high level, the signal graph looks like this:

  (input video) -> [ffmpeg process 1] -> [python] -> [ffmpeg process 2] -> (output video)

This example reads/writes video files on the local filesystem, but the
same pattern can be used for other kinds of input/output (e.g. webcam,
rtmp, etc.).

The simplest processing example simply darkens each frame by
multiplying the frame's numpy array by a constant value; see
``process_frame_simple``.

A more sophisticated example processes each frame with tensorflow using
the "deep dream" tensorflow tutorial; activate this mode by calling
the script with the optional `--dream` argument.  (Make sure tensorflow
is installed before running)
'''
from __future__ import print_function
import argparse
import ffmpeg
import logging
import numpy as np
import os
import subprocess
import zipfile
import uuid

from detect_objects import run_inference


parser = argparse.ArgumentParser(description='Example streaming ffmpeg numpy processing')
parser.add_argument('in_filename', help='Input filename')

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_video_size(filename):
    logger.info('Getting video size for {!r}'.format(filename))
    probe = ffmpeg.probe(filename)
    video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    width = int(video_info['width'])
    height = int(video_info['height'])
    return width, height


def start_ffmpeg_process1(in_filename):
    logger.info('Starting ffmpeg process1')
    args = (
        ffmpeg
        .input(in_filename)
        .output('pipe:', format='rawvideo', pix_fmt='rgb24')
        .compile()
    )
    return subprocess.Popen(args, stdout=subprocess.PIPE)


def start_ffmpeg_process2(width, height):
    logger.info('Starting ffmpeg process2')
    args = (
        ffmpeg
        .input('pipe:', format='rawvideo', pix_fmt='rgb24', s='{}x{}'.format(width, height))
        .output(f'videos/playlist-{str(uuid.uuid4())}.m3u8', format='hls', start_number=0, hls_time=5, hls_list_size=0)
        .overwrite_output()
        .compile()
    )
    return subprocess.Popen(args, stdin=subprocess.PIPE)


def read_frame(process1, width, height):
    logger.debug('Reading frame')

    # Note: RGB24 == 3 bytes per pixel.
    frame_size = width * height * 3
    in_bytes = process1.stdout.read(frame_size)
    if len(in_bytes) == 0:
        frame = None
    else:
        assert len(in_bytes) == frame_size
        frame = (
            np
            .frombuffer(in_bytes, np.uint8)
            .reshape([height, width, 3])
        )
    return frame


def process_frame_simple(frame):
    return run_inference(frame)


def write_frame(process2, frame):
    logger.debug('Writing frame')
    process2.stdin.write(
        frame
        .astype(np.uint8)
        .tobytes()
    )


def run(in_filename, process_frame):
    width, height = get_video_size(in_filename)
    process1 = start_ffmpeg_process1(in_filename)
    process2 = start_ffmpeg_process2(width, height)
    while True:
        in_frame = read_frame(process1, width, height)
        if in_frame is None:
            logger.info('End of input stream')
            break

        logger.debug('Processing frame')
        out_frame = process_frame(in_frame)
        write_frame(process2, out_frame)

    logger.info('Waiting for ffmpeg process1')
    process1.wait()

    logger.info('Waiting for ffmpeg process2')
    process2.stdin.close()
    process2.wait()

    logger.info('Done')


if __name__ == '__main__':
    args = parser.parse_args()
    run(args.in_filename, process_frame_simple)