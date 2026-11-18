# CNDW 2026 デモ一式：AI エージェントの暴走と、ガードレール

Cloud Native Days Winter 2026 の登壇「OWASP AI Agentic Top10に準拠するクラウドネイティブなガードレールの実践」の、持ち帰り用の素材です。

**検証用のクラスタ（kind など）だけで動かしてください。** `shell.exec` は、意図的に汎用シェルです。本番や共有のクラスタでは、実行しないでください。

## 何を再現するか

読み込んだ README の隠し指示が、Pod 内の（MCP 風の）ツールを乗っ取り、ServiceAccount のトークンを外へ送ります。ガードレールなし／ありで、同じ攻撃を比べます。

- 判断の部分は、固定スクリプト（`app/agent.py`）です。モデルの代わりで、毎回同じ動きにするためです。ツール呼び出し、Pod、ネットワーク、Falco は本物です。
- ツールは MCP 風です（JSON-RPC の `tools/list`、`tools/call` のみ。完全な MCP 実装ではありません）。
- 攻撃者のサーバーは、クラスタ内のシミュレーション（`attacker-sim`）です。本物のトークンも、外部への送信もありません。

## 構成

| パス | 内容 |
|---|---|
| `app/` | エージェント（固定スクリプト）、ツールサーバー、攻撃者の受信サーバー、OpenTelemetry の初期化（`otel_setup.py`） |
| `k8s/` | namespace、攻撃者（シミュレーション）、ガードレールなし／ありの Pod、NetworkPolicy、ValidatingAdmissionPolicy、Jaeger（トレースの受け皿） |
| `falco/` | Falco のルール、Helm の値、Falco Talon のルール |
| `scripts/` | セットアップ、デモ1、デモ2、リセット |
| `recordings/` | 登壇で使った録画と、最後の画面 |
| `slides/` | 登壇資料 |
| `VERIFICATION.md` | 実機での検証結果（うまくいかなかった点を含む） |
| `RECORDING.md` | 録画の手順 |

## 動作を確認した環境

kind v0.32、Kubernetes v1.36.1、kindnet（NetworkPolicy を enforce できました）、Falco 0.45.2（Helm chart 9.2.2）、Falco Talon（chart 0.5.0）。

## 動かし方

```
scripts/setup.sh                 # kind、イメージ、攻撃者側
# Falco（デモ2のみ）
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco -n falco --create-namespace -f falco/values.yaml
# Falco Talon を入れ、falco/talon-rules.yaml を設定（Talon の公式手順に従う）
scripts/run-demo1.sh             # 暴走：トークンが、外へ出る
scripts/run-demo2.sh             # 停止：検知、隔離、停止
```

## OpenTelemetry：原因のリクエストまで辿る（ガードレール⑤）

エージェントとツールサーバーは、公式の OpenTelemetry SDK でトレースを出します。`scripts/setup.sh` が、Jaeger（v2 の all-in-one、メモリ保存）を `observability` に入れます。

```
kubectl -n observability port-forward svc/jaeger 16686:16686    # http://localhost:16686
```

デモ1またはデモ2を実行したあと、Jaeger の UI で、サービス `coding-agent` を開きます。1回の実行が、1本のトレースになります。

| スパン | 意味 |
|---|---|
| `agent.task` | タスク全体（根） |
| `agent.decide`（`plan`、`hijacked`） | 判断。固定スクリプトなので `agent.scripted=true`。`hijacked` には `agent.injection.detected=false` が付く |
| `mcp.fs.read` / `mcp.shell.exec` / `mcp.http.post` | エージェント側のツール呼び出し |
| `mcp.server.*` | ツールサーバー側。`traceparent` で、上の子スパンになる |

見どころは、README を読んだスパン（`mcp.fs.read`）が、トークンを読み（`mcp.shell.exec`）、外へ送る（`mcp.http.post`）までの、すべての起点になっていることです。デモ2では、`mcp.http.post` が、エラー（遮断）で終わります。

### 検知とトレースを、つなぐ

Falco のアラートには、`k8s.pod.name` と時刻があります。トレースには、リソース属性 `k8s.pod.name` と、スパンの時刻があります。

1. Falco のアラートから、`pod=coding-agent` と時刻を読む。
2. Jaeger で、タグ `k8s.pod.name=coding-agent` と、その時間帯で検索する。
3. 見つけたトレースの、最初の `mcp.fs.read` が、原因の入口。
4. エージェントのログには、`[otel] trace_id=…` が出る。トレースの ID で直接開ける。

### 注意

- `otel_setup.py` は、環境変数 `OTEL_EXPORTER_OTLP_ENDPOINT` が未設定なら、何もしません。計装なしでも、従来どおり動きます。
- スパンは、1つ終わるたびに、すぐ送ります。Talon に Pod を止められても、それまでに終わったスパンは、Jaeger に残ります。根の `agent.task` は、終わる前に Pod が消えるので、デモ2では Jaeger に出ません（子スパンが、親なしで表示されます）。
- ツールの引数のうち、`body`（トークン）は、スパンに記録しません。実運用でも、機密は属性に入れないでください。
- Jaeger への通信は、NetworkPolicy（`k8s/30-networkpolicy.yaml`）と、Falco の許可リスト（`falco/agent_rules.yaml` の `agent_allowed_dest_ips`）に、それぞれ許可を足してあります。Jaeger の ClusterIP（`10.96.60.60`）は、`k8s/60-jaeger.yaml` で固定しています。

## 知っておいてほしいこと

- デモ2は、ServiceAccount トークンを、あえてマウントしたままにしています。Falco のトークン読み取りルールを見せるためです。最小権限（トークンを外す）は、別のガードレールとして示しています。
- Falco の既定の `outbound` マクロは、私設アドレス宛を除外します。このデモの宛先（`10.96.50.50`）を検知するため、専用の `agent_outbound` マクロを使っています。
- Talon は、1つ目のアラート（トークン読み取り）で Pod を終了させます。2つ目のアラートは、直後に出るだけです。
- `grace_period_seconds` は 5 です。0 にしたときに、トークンが外へ出た試行が1回ありました（原因は未特定）。`VERIFICATION.md` を見てください。
- Falco、Talon の Helm の値や書式は、バージョンで変わります。公式の最新に合わせてください。

## トラブルシュート

- Falco が発火しない：ルールが読み込まれているか（`kubectl -n falco logs`）。デフォルトルール（`open_read` マクロ）が有効か。k8s のメタデータ取得が有効か。
- NetworkPolicy が効かない：CNI を、Calico か Cilium に。
- VAP が効かない：Kubernetes 1.30 以降か。`kubectl get validatingadmissionpolicy`。

## ライセンス

Apache License 2.0（`LICENSE`）です。

ただし、`slides/` の登壇資料に含まれる Falco のロゴは、Falco プロジェクトの素材・商標であり、このライセンスの対象ではありません。
