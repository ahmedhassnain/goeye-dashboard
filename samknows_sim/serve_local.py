# serve_local.py
"""
Local stand-in for the SamKnows archive server, for development.

Serves a directory of generated archives the way the real server does: an
HTTP Basic-auth protected "Index of /" HTML page linking to each
YYYYMMDD-*.tar.gz, plus the archives themselves. Same contract as the
Cloudflare Worker in samknows_sim/worker/.

Usage:
    python samknows_sim/generate_archive.py --days 14
    python samknows_sim/serve_local.py --user demo --password demo --port 8765

Then in .env:
    SAMKNOWS_URL=http://127.0.0.1:8765/
    SAMKNOWS_USER=demo
    SAMKNOWS_PASS=demo
"""
import argparse
import base64
import hmac
import html
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def make_handler(archive_dir, expected_auth):
    class Handler(BaseHTTPRequestHandler):
        def _authorized(self):
            got = self.headers.get("Authorization", "")
            return hmac.compare_digest(got.encode(), expected_auth.encode())

        def do_GET(self):
            if not self._authorized():
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="SamKnows data"')
                self.end_headers()
                return

            name = self.path.split("?")[0].lstrip("/")
            if name == "":
                return self._send_index()

            path = archive_dir / name
            if "/" in name or not name.endswith(".tar.gz") or not path.is_file():
                self.send_error(404)
                return
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/gzip")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_index(self):
            rows = []
            for f in sorted(archive_dir.glob("*.tar.gz")):
                stat = f.stat()
                modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M")
                name = html.escape(f.name)
                rows.append(f'<a href="{name}">{name}</a>  {modified}  {stat.st_size // 1024}K')
            body = ("<html><head><title>Index of /</title></head><body>"
                    "<h1>Index of /</h1><pre>" + "\n".join(rows) + "</pre></body></html>").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Serve generated archives like the SamKnows server")
    parser.add_argument("--dir", default="samknows_sim/archives")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--user", default="demo")
    parser.add_argument("--password", default="demo")
    args = parser.parse_args()

    archive_dir = Path(args.dir).resolve()
    token = base64.b64encode(f"{args.user}:{args.password}".encode()).decode()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(archive_dir, f"Basic {token}"))
    print(f"Serving {archive_dir} on http://127.0.0.1:{args.port}/ (Basic auth user: {args.user})")
    server.serve_forever()


if __name__ == "__main__":
    main()
