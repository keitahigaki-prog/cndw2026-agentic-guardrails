"""攻撃者側の受信サーバー（シミュレーション）。受け取った内容を表示する。"""
import os, time
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode(errors="replace")
        print("%s RECEIVED from %s: %s...(%d bytes)" % (time.strftime("%H:%M:%S"), self.client_address[0], body[:48].replace("\n", " "), len(body)), flush=True)
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass
if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "9000"))), H).serve_forever()
