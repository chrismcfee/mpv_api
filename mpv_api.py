from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import socket
import ssl
import base64
import os  # Import os module to read environment variables
from dotenv import load_dotenv
#config = dotenv_values(".env")
load_dotenv()  # take environment variables from .env.
MPV_SOCKET = '/tmp/mpvsocket'  # Adjust this path as needed
USERNAME=os.getenv('MPV_USERNAME')
PASSWORD=os.getenv('MPV_PASSWORD')

# Read username and password from environment variables
def send_command(command):
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(MPV_SOCKET)
        # Build the JSON command
        if command[0] == 'keypress':
            # Simulate keypress
            key_name = command[1]
            cmd = {"command": ["keypress", key_name]}
        else:
            cmd = {"command": command}
        sock.send(json.dumps(cmd).encode() + b'\n')
        response = sock.recv(1024).decode()
        sock.close()
        return response
    except Exception as e:
        return str(e)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Check if USERNAME and PASSWORD are set
        if USERNAME is None or PASSWORD is None:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Server configuration error: USERNAME and PASSWORD not set')
            return

        # Check for Authorization header
        auth_header = self.headers.get('Authorization')
        if not auth_header:
            # Send 401 Unauthorized response with WWW-Authenticate header
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="MPV Control"')
            self.end_headers()
            return

        # Decode the credentials
        auth_method, auth_info = auth_header.split(' ', 1)
        if auth_method.lower() != 'basic':
            # If not using Basic Auth, reject the request
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="MPV Control"')
            self.end_headers()
            return

        try:
            credentials = base64.b64decode(auth_info.strip()).decode('utf-8')
            req_username, req_password = credentials.split(':', 1)
        except Exception:
            # If decoding fails, reject the request
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="MPV Control"')
            self.end_headers()
            return

        if req_username != USERNAME or req_password != PASSWORD:
            # If credentials don't match, send 403 Forbidden
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'Forbidden')
            return

        # If authentication succeeds, process the command
        command = self.path[1:].split('/')  # Remove leading slash and split
        response = send_command(command)
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(response.encode())

if __name__ == "__main__":
    httpd = HTTPServer(('0.0.0.0', 8000), Handler)

    # Wrap the socket with SSL
    # You need to generate 'cert.pem' and 'key.pem' files beforehand
    # Example command to generate them:
    # openssl req -new -x509 -keyout key.pem -out cert.pem -days 365 -nodes

    httpd.socket = ssl.wrap_socket(httpd.socket,
                                   server_side=True,
                                   certfile='cert.pem',
                                   keyfile='key.pem',
                                   ssl_version=ssl.PROTOCOL_TLS_SERVER)

    print("Server started on port 8000 with SSL")
    httpd.serve_forever()
