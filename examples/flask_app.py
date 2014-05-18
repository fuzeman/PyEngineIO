from flask import Flask
from gevent.wsgi import WSGIServer

from pyengineio.handler import EngineIO_Handler
import pyengineio as eio

app = Flask(__name__)
eio.attach(app)

@app.route('/')
def index():
    return 'index'

if __name__ == '__main__':
    server = WSGIServer(('', 5000), app, handler_class=EngineIO_Handler)
    server.serve_forever()
