#!/usr/bin/env python3
"""
Simple HTTP server to serve the Outreach frontend.
This allows the frontend to load CSV files from the backend directory.

Usage: python serve.py
Then open: http://localhost:8080
"""

import http.server
import socketserver
import os
import webbrowser

PORT = 8080

# Change to the project root directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with CORS headers and correct MIME types."""
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def guess_type(self, path):
        """Override to return correct MIME types."""
        mimetype = super().guess_type(path)
        if path.endswith('.js'):
            return 'application/javascript'
        if path.endswith('.css'):
            return 'text/css'
        if path.endswith('.json'):
            return 'application/json'
        return mimetype

def main():
    with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
        url = f"http://localhost:{PORT}/frontend/"
        print(f"\n🌿 Outreach Server Running")
        print(f"=" * 40)
        print(f"📂 Serving from: {os.getcwd()}")
        print(f"🌐 Open in browser: {url}")
        print(f"=" * 40)
        print(f"\nPress Ctrl+C to stop the server\n")
        
        # Open browser automatically
        webbrowser.open(url)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped.")

if __name__ == "__main__":
    main()
