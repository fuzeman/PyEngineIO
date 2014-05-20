import pyengineio_client as eio

import logging
import time

logging.basicConfig()
logging.getLogger('pyengineio_client').setLevel(logging.DEBUG)

socket = eio.connect('http://localhost:5000')

socket.write('hello')


@socket.on('message')
def on_message(message):
    print 'on_message'
    time.sleep(2)

    socket.write(message)

while True:
    raw_input()
