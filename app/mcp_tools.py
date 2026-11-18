"""MCP 風のツールサーバー（デモ用）。JSON-RPC 2.0 over HTTP。tools/list, tools/call のみ。
注意: shell.exec は意図的に汎用シェル。kind などの検証環境でだけ動かすこと。"""
import json, os, subprocess, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.trace import Status, StatusCode
import otel_setup
tracer = otel_setup.init("mcp-tools")
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
            else:
                name = body["params"]["name"]; args = body["params"].get("arguments", {})
                attrs = {"tool.name": name}
                if "cmd" in args: attrs["tool.cmd"] = args["cmd"]
                if "url" in args: attrs["tool.url"] = args["url"]        # body（トークン）は、記録しない
                # ■ extract: リクエストヘッダーの traceparent から、呼び出し元（agent）のスパンを取り出す。
                #   context= に渡すと、このスパンは、その子になる。これで、2つのプロセスが1本のトレースになる。
                # ■ ヘッダー名は、クライアントによって大文字小文字が違う（urllib は "Traceparent"）。
                #   W3C の伝播は小文字で探すので、小文字にそろえて渡す。
                # ■ kind=SERVER は「リクエストを受けた側」の印。Jaeger の画面で、呼ぶ側と受ける側が区別できる。
                with tracer.start_as_current_span("mcp.server." + name, context=extract({k.lower(): v for k, v in self.headers.items()}), kind=trace.SpanKind.SERVER, attributes=attrs) as span:
                    try: text = call(name, args)
                    except Exception as e:
                        # 失敗（例：遮断された外向き通信）を、スパンに残す。Jaeger では赤いエラーとして見える。
                        span.record_exception(e); span.set_status(Status(StatusCode.ERROR, str(e))); raise
                res = {"content": [{"type": "text", "text": text}]}
            out = {"jsonrpc": "2.0", "id": body.get("id"), "result": res}
        except Exception as e:
            out = {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32000, "message": str(e)}}
        data = json.dumps(out).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def log_message(self, *a): pass
if __name__ == "__main__":
    HTTPServer((os.environ.get("BIND", "127.0.0.1"), int(os.environ.get("PORT", "8080"))), H).serve_forever()
