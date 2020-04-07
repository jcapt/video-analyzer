import ffmpeg

url = 'http://kamery.szr.bialystok.pl:81/kam1/'

stream = ffmpeg.input(url)
stream = ffmpeg.hflip(stream)
stream = ffmpeg.output(stream, 'output.mp4')
ffmpeg.run(stream)
