from pyengineio.transports.base import Transport


class WebSocket(Transport):
    name = 'websocket'
    supports_framing = True
    supports_upgrades = True
