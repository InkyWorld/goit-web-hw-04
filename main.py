import mimetypes
import urllib.parse
import json
import logging
import socket
import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from datetime import datetime


BASE_DIR = Path()
BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = '0.0.0.0'
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000


class MyFramework(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case '/':
                self.send_html(BASE_DIR / "templates" / "index.html")
            case '/message':
                self.send_html(BASE_DIR / "templates" / "message.html")
            case _:
                file = BASE_DIR.joinpath("assets", route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html(BASE_DIR / "templates" / 'error.html', 404)

    def do_POST(self):
        size = self.headers.get('Content-Length')
        data = self.rfile.read(int(size))

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
            client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))

        self.send_response(302)
        self.send_header('Location', '/message')
        self.end_headers()

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

    def send_static(self, filename, status_code=200):
        self.send_response(status_code)
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header('Content-Type', mime_type)
        else:
            self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())


def save_data_from_form(data):
    parse_data = urllib.parse.unquote_plus(data.decode())
    try:
        parse_dict = {key: value for key, value in [el.split('=') for el in parse_data.split('&')]}
        os.makedirs("storage", exist_ok=True)
        try:
            with open("storage/data.json", 'r', encoding='utf-8') as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data.update({timestamp: parse_dict})
        with open('storage/data.json', 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except ValueError as err:
        logging.error(err)
    except OSError as err:
        logging.error(err)


def run_http_server(host, port):
    server_address = (host, port)
    httpd = HTTPServer(server_address, MyFramework)
    logging.info(f'Starting HTTP server on {host}:{port}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        logging.info('HTTP server stopped')


def run_socket_server(host, port):
    server_address = (host, port)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind(server_address)
        logging.info(f'Starting socket server on {host}:{port}')
        try:
            while True:
                msg, address = server_socket.recvfrom(BUFFER_SIZE)
                save_data_from_form(msg)
        except KeyboardInterrupt:
            pass
        finally:
            server_socket.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(threadName)s %(message)s')

    server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    server.start()

    server_socket = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    server_socket.start()
