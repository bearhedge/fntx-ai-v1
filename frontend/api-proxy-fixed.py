#!/usr/bin/env python3
import http.server
import http.client
import urllib.parse
import json
import os
from http.server import SimpleHTTPRequestHandler

class ProxyHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Set the directory to serve static files from
        super().__init__(*args, directory='dist', **kwargs)
    
    def do_GET(self):
        if self.path.startswith('/api/'):
            self.proxy_request()
        else:
            # Serve static files from dist directory
            super().do_GET()
    
    def do_POST(self):
        if self.path.startswith('/api/'):
            self.proxy_request()
        else:
            self.send_error(404)
    
    def do_PUT(self):
        if self.path.startswith('/api/'):
            self.proxy_request()
        else:
            self.send_error(404)
    
    def do_DELETE(self):
        if self.path.startswith('/api/'):
            self.proxy_request()
        else:
            self.send_error(404)
    
    def proxy_request(self):
        # Backend is running on port 8003
        backend_host = '127.0.0.1'
        backend_port = 8003
        
        # Parse the URL
        parsed_path = urllib.parse.urlparse(self.path)
        
        # Read request body if present
        content_length = self.headers.get('Content-Length')
        body = None
        if content_length:
            body = self.rfile.read(int(content_length))
        
        try:
            # Create connection to backend
            conn = http.client.HTTPConnection(backend_host, backend_port)
            
            # Forward headers
            headers = {}
            for header, value in self.headers.items():
                if header.lower() not in ['host', 'connection']:
                    headers[header] = value
            
            # Make request to backend
            conn.request(
                method=self.command,
                url=self.path,
                body=body,
                headers=headers
            )
            
            # Get response from backend
            response = conn.getresponse()
            
            # Send response status
            self.send_response(response.status)
            
            # Forward response headers
            for header, value in response.getheaders():
                if header.lower() not in ['connection', 'transfer-encoding']:
                    self.send_header(header, value)
            self.end_headers()
            
            # Forward response body
            self.wfile.write(response.read())
            
            conn.close()
            
        except Exception as e:
            self.send_error(502, f"Bad Gateway: {str(e)}")

def run_server(port=8080):
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, ProxyHTTPRequestHandler)
    print(f"Proxy server running on port {port}")
    print(f"Proxying /api/* requests to http://127.0.0.1:8003")
    print(f"Serving static files from ./dist directory")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()