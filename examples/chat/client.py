import pyengineio_client as eio
import logging

logging.basicConfig()
logging.getLogger('pyengineio_client').setLevel(logging.DEBUG)

socket = eio.connect('http://localhost:5000')

socket.write('hello')

while True:
    raw_input()
