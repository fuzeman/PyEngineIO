from flask import Flask
from pyengineio.server import EngineIO_Server
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

@app.route('/')
def index():
    return 'index'

if __name__ == '__main__':
    server = EngineIO_Server(('', 5000), app)
    server.serve_forever()
