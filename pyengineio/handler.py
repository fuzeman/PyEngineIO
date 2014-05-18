from gevent.wsgi import WSGIHandler


class EngineIO_Handler(WSGIHandler):
    def __init__(self, *args, **kwargs):
        super(EngineIO_Handler, self).__init__(*args, **kwargs)

    def handle_one_response(self):
        pass
