import http.server
import socketserver
import os

PORT = int(os.getenv("PORT", 8080))

handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), handler) as httpd:
    print(f"Servindo na porta {PORT}")
    httpd.serve_forever()