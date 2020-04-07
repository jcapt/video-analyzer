from flask import Flask, send_from_directory, json
import glob
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/videos/<string:file_name>')
def stream(file_name):
    return send_from_directory(directory='./videos', filename=file_name)

@app.route('/live')
def live():
  return send_from_directory(directory='./', filename="index.html")

@app.route('/collected_streams')
def collected_streams():
  dirs = glob.glob("./videos/*.m3u8")
  return json.dumps(dirs)

app.run(host="0.0.0.0", port=3000)