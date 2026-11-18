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
| `app/` | エージェント（固定スクリプト）、ツールサーバー、攻撃者の受信サーバー |
| `k8s/` | namespace、攻撃者（シミュレーション）、ガードレールなし／ありの Pod、NetworkPolicy、ValidatingAdmissionPolicy |
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
