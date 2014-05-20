import pyengineio_client as eio

import logging
import time

logging.basicConfig(level=logging.DEBUG)

socket = eio.connect('http://localhost:5000')

socket.write('hello')


@socket.on('message')
def on_message(message):
    print 'on_message', message

    #time.sleep(2)
    #socket.write(message)

while True:
    raw_input()
