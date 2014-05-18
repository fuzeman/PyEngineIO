import pyengineio_client as eio
import logging

logging.basicConfig()
logging.getLogger('pyengineio_client').setLevel(logging.DEBUG)

eio.connect('http://localhost:5000')

while True:
    raw_input()
