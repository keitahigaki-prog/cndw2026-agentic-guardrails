"""MCP 風のツールサーバー（デモ用）。JSON-RPC 2.0 over HTTP。tools/list, tools/call のみ。
注意: shell.exec は意図的に汎用シェル。kind などの検証環境でだけ動かすこと。"""
import json, os, subprocess, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
WORKSPACE = os.environ.get("WORKSPACE", "/workspace")
TOOLS = [{"name": "fs.read", "description": "ワークスペースのファイルを読む"},
         {"name": "shell.exec", "description": "シェルコマンドを実行する"},
         {"name": "http.post", "description": "HTTP POST を送る"}]
def call(name, args):
    if name == "fs.read":
        with open(os.path.join(WORKSPACE, args["path"]), encoding="utf-8") as f: return f.read()
    if name == "shell.exec":
        r = subprocess.run(args["cmd"], shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout + r.stderr
    if name == "http.post":
        req = urllib.request.Request(args["url"], data=args["body"].encode(), method="POST")
        with urllib.request.urlopen(req, timeout=5) as r: return "HTTP %s" % r.status
    raise ValueError("unknown tool: " + name)
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        try:
            if body["method"] == "tools/list": res = {"tools": TOOLS}
            else: res = {"content": [{"type": "text", "text": call(body["params"]["name"], body["params"].get("arguments", {}))}]}
            out = {"jsonrpc": "2.0", "id": body.get("id"), "result": res}
        except Exception as e:
            out = {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32000, "message": str(e)}}
        data = json.dumps(out).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def log_message(self, *a): pass
if __name__ == "__main__":
    HTTPServer((os.environ.get("BIND", "127.0.0.1"), int(os.environ.get("PORT", "8080"))), H).serve_forever()
