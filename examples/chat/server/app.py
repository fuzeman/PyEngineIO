from pyengineio import Engine, Server

from flask import Flask, render_template
import logging
import time

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
eio = Engine()


@app.route('/')
def index():
    return render_template('index.html')


@eio.on('connection')
def on_connection(socket):
    print 'on_connection', socket

    @socket.on('message')
    def on_message(message):
        print 'on_message', message

        #time.sleep(2)
        socket.write(message)

if __name__ == '__main__':
    server = Server(('', 5000), app, eio)
    server.serve_forever()
