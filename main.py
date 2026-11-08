import socket
import sys
import webbrowser

from werkzeug.serving import ThreadedWSGIServer

from app.web import app


class ValidatorServer(ThreadedWSGIServer):
    allow_reuse_address = False
    allow_reuse_port = False

    def server_bind(self):
        if sys.platform == 'win32':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


if __name__ == '__main__':
    with ValidatorServer('127.0.0.1', 5000, app) as server:
        print('http://127.0.0.1:5000/  (Ctrl+C to stop)', flush=True)
        if '--browser' in sys.argv:
            webbrowser.open('http://127.0.0.1:5000/')
        server.serve_forever()
