#!/usr/bin/env python3
"""
Simple HTTP server that serves static files and proxies API requests to backend
"""
import http.server
import socketserver
import urllib.request
import urllib.parse
import os
import sys

BACKEND_URL = "http://127.0.0.1:8003"
STATIC_DIR = "dist"
PORT = 8080

class ProxyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_PUT(self):
        self.handle_request()

    def do_DELETE(self):
        self.handle_request()

    def do_OPTIONS(self):
        self.handle_request()

    def handle_request(self):
        if self.path.startswith('/api/'):
            self.proxy_to_backend()
        elif self.path.startswith('/ws/'):
            self.send_error(501, "WebSocket not supported in this proxy")
        else:
            # For client-side routing, serve index.html for any route
            if not os.path.exists(os.path.join(STATIC_DIR, self.path.lstrip('/'))) and not '.' in os.path.basename(self.path):
                self.path = '/index.html'
            super().do_GET()

    def proxy_to_backend(self):
        try:
            # Construct backend URL
            backend_url = f"{BACKEND_URL}{self.path}"
            
            # Get request body if present
            content_length = self.headers.get('Content-Length')
            body = None
            if content_length:
                body = self.rfile.read(int(content_length))

            # Create request
            req = urllib.request.Request(backend_url, data=body, method=self.command)
            
            # Copy headers (except Host and Connection)
            for header, value in self.headers.items():
                if header.lower() not in ['host', 'connection', 'content-length']:
                    req.add_header(header, value)
            
            if body:
                req.add_header('Content-Length', str(len(body)))

            # Make request
            try:
                response = urllib.request.urlopen(req)
                
                # Send response
                self.send_response(response.getcode())
                
                # Copy response headers
                for header, value in response.headers.items():
                    if header.lower() not in ['connection', 'content-encoding', 'transfer-encoding']:
                        self.send_header(header, value)
                self.end_headers()
                
                # Copy response body
                self.wfile.write(response.read())
                
            except urllib.error.HTTPError as e:
                self.send_response(e.code)
                for header, value in e.headers.items():
                    if header.lower() not in ['connection', 'content-encoding', 'transfer-encoding']:
                        self.send_header(header, value)
                self.end_headers()
                self.wfile.write(e.read())
                
        except Exception as e:
            self.send_error(502, f"Backend error: {str(e)}")

    def log_message(self, format, *args):
        # Custom log format
        sys.stderr.write(f"{self.address_string()} - [{self.log_date_time_string()}] {format%args}\n")

def run_server():
    with socketserver.TCPServer(("", PORT), ProxyHTTPRequestHandler) as httpd:
        print(f"Server running on http://localhost:{PORT}")
        print(f"Serving static files from: {STATIC_DIR}")
        print(f"Proxying /api/* to: {BACKEND_URL}")
        httpd.serve_forever()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_server()