from http.server import BaseHTTPRequestHandler
from pathlib import Path
import mimetypes


PUBLIC_DIR = Path(__file__).resolve().parents[1] / "public"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Expected path: /assets/<file>
            if not self.path.startswith("/assets/"):
                self.send_response(404)
                self.end_headers()
                return

            rel_path = self.path[len("/assets/"):]
            # Prevent path traversal
            safe_path = (PUBLIC_DIR / rel_path).resolve()
            if not str(safe_path).startswith(str(PUBLIC_DIR.resolve())):
                self.send_response(403)
                self.end_headers()
                return

            if not safe_path.exists() or not safe_path.is_file():
                self.send_response(404)
                self.end_headers()
                return

            content_type, _ = mimetypes.guess_type(str(safe_path))
            if not content_type:
                content_type = "application/octet-stream"

            data = safe_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_response(500)
            self.end_headers()
