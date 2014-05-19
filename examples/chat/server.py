from flask import Flask
from pyengineio.engine import EngineIO
from pyengineio.server import EngineIO_Server
import logging
import time

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
eio = EngineIO()

@app.route('/')
def index():
    return 'index'

@eio.on('connection')
def on_connection(socket):
    print 'on_connection', socket

    @socket.on('message')
    def on_message(message):
        print 'on_message'
        time.sleep(2)

        socket.write(message)

if __name__ == '__main__':
    server = EngineIO_Server(('', 5000), app, eio)
    server.serve_forever()
