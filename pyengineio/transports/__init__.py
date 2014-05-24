from pyengineio.transports.polling_jsonp import JSONP_Polling
from pyengineio.transports.polling_xhr import XHR_Polling
from pyengineio.transports.ws import WebSocket

TRANSPORTS = {
    'polling-xhr': XHR_Polling,
    'polling-jsonp': JSONP_Polling,
    'websocket': WebSocket
}

__all__ = ['XHR_Polling', 'WebSocket']
