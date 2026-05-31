import http.server
import json
import os
import socketserver

PORT = int(os.getenv("PORT", 8080))

class FrontendHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/config":
            payload = json.dumps({
                "API_URL": os.getenv("API_URL", "").rstrip("/")
            }).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        super().do_GET()

with socketserver.TCPServer(("", PORT), FrontendHandler) as httpd:
    print(f"Servindo na porta {PORT}")
    httpd.serve_forever()
