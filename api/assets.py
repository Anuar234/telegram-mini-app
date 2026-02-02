from http.server import BaseHTTPRequestHandler
from pathlib import Path
import mimetypes
from urllib.parse import urlparse, parse_qs


_BASE_DIR = Path(__file__).resolve().parents[1]
_PUBLIC_CANDIDATES = [
    _BASE_DIR / "public",
    _BASE_DIR / "src" / "public",
    _BASE_DIR.parents[0] / "public",
]

def _resolve_public_file(rel_path: str) -> Path:
    for base in _PUBLIC_CANDIDATES:
        candidate = (base / rel_path).resolve()
        if candidate.exists() and candidate.is_file():
            return candidate
    return (_PUBLIC_CANDIDATES[0] / rel_path).resolve()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Support both:
            # - /api/assets?path=welcome.gif
            # - /assets/welcome.gif (if routed)
            parsed = urlparse(self.path)
            rel_path = ""

            if parsed.path.startswith("/assets/"):
                rel_path = parsed.path[len("/assets/"):]
            else:
                qs = parse_qs(parsed.query or "")
                rel_path = (qs.get("path") or [""])[0]

            if not rel_path:
                self.send_response(404)
                self.end_headers()
                return

            # Prevent path traversal
            safe_path = _resolve_public_file(rel_path)
            base_dir = _PUBLIC_CANDIDATES[0].resolve()
            if not str(safe_path).startswith(str(base_dir)):
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
