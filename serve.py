"""Local server for the APPLEX AI static export.

python serve.py
then open http://127.0.0.1:8091/
"""
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ORIGIN = "https://applexai.com"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.should_proxy():
            self.proxy()
            return
        self.map_route()
        super().do_GET()

    def do_POST(self):
        if self.should_proxy():
            self.proxy()
            return
        self.send_error(404)

    def should_proxy(self):
        path = urllib.parse.urlparse(self.path).path
        return path.startswith("/_serverFn") or path.startswith("/api/")

    def map_route(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        if path in ("/", ""):
            self.path = "/index.html"
            return
        rel = path.lstrip("/")
        if (ROOT / rel).is_file():
            return
        if (ROOT / f"{rel}.html").is_file():
            self.path = f"/{rel}.html"
            return
        if path.startswith(("/assets/", "/__l5e/", "/external/", "/favicon")):
            return
        self.path = "/index.html"

    def proxy(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "content-length", "connection", "accept-encoding"}
        }
        request = urllib.request.Request(
            ORIGIN + self.path,
            data=body,
            headers=headers,
            method=self.command,
        )
        try:
            response = urllib.request.urlopen(request, timeout=60)
            status = response.status
            payload = response.read()
            header_items = response.headers.items()
        except urllib.error.HTTPError as error:
            status = error.code
            payload = error.read()
            header_items = error.headers.items()
        self.send_response(status)
        for key, value in header_items:
            if key.lower() in {"transfer-encoding", "content-encoding", "content-length", "connection"}:
                continue
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8091), Handler)
    print("http://127.0.0.1:8091/")
    server.serve_forever()
