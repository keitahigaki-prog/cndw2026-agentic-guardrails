# 検証報告（2026-11-18、実機：kind v0.32 / k8s v1.36.1 / kindnet v20260528 / Falco 0.45.2 / falco chart 9.2.2 / falco-talon chart 0.5.0）

| # | 項目 | 結果 | メモ |
|---|---|---|---|
| 1 | setup.sh | OK | collector Ready。kindnet が NetworkPolicy を enforce（Calico/Cilium 不要） |
| 2 | デモ1 トークン到達 | OK | collector に `RECEIVED … eyJ…(1174 bytes)`。ただし初回は他の kind クラスタとの CPU 競合でタイムアウト（回避：他を docker stop） |
| 3 | NetworkPolicy enforce | OK（条件付き） | 起動直後（約1秒）は素通り。プローブで delay 0 = 到達、delay 3/8 = 遮断。デモの Pod は約4秒後に接続するため、無Talon 5/5 遮断 |
| 4 | VAP | OK | `Warning: … エージェント Pod は SA トークンをマウントしない`（Warn）。2つ目の検証（readOnlyRootFilesystem）は保護版 Pod が満たすため出ない |
| 5 | Falco ルール読込 | NG→修正して OK | `k8s.pod.label.app` は構文エラー（`k8s.pod.label requires an argument`）。`k8s.pod.label[app]` に修正 |
| 6 | SA トークン読取で発火 | OK | `Critical Agent Reads Service Account Token`（表示は `Critical`、大文字ではない） |
| 7 | 想定外の外向き通信で発火 | NG→修正して OK | 既定 macro `outbound` は RFC1918 宛を除外するため、10.96.50.50 は検知されない。専用 macro `agent_outbound` を追加。NetworkPolicy で遮断されても connect 試行は検知された（dest=10.96.50.50:80） |
| 8 | Talon の隔離・停止 | NG→修正して OK | chart 9.2.2 は `responseActions.enabled` だけでは sidekick→Talon が配線されない。`falcosidekick.config.talon.address` を追加。ラベル付与→終了まで成功 |
| 9 | 部分OK | `PAUSE` を調整（デモ1=12秒、デモ2=4秒＋`PAUSE_ATTACK`=2秒）。実測：デモ1 の run-demo1.sh は約74秒（エージェント出力は約60秒＝ショットリストの 0:20〜1:20 に一致）、デモ2 はトークン読取アラートが約16秒、Pod 消滅まで約25秒。残りの時間（README 提示・右上ペイン・最終画面で5秒止める）は、操作とナレーションで埋める。録画自体は未実施 |

## うまくいかなかった点と回避策
- **Talon の grace_period_seconds: 0 で、1/1 回、トークンが外へ出た**（collector に RECEIVED。原因は未特定。Pod 削除で egress が素通りした可能性を疑い、削除後の追加プローブでは再現せず）。`grace_period_seconds: 5` に変更後は 5/5 回遮断、Pod は約7秒で消滅。サンプル数は少ない。
- Talon は1つ目のアラート（トークン読取）で Pod を終了させる。2つ目（Unexpected Outbound）は約1秒後に発火し、Talon は「Pod が存在しない」とエラー（ERR）を出す。画面上の流れ（スライド18）は「トークン読取→停止」で1段目で止まる、に合わせる必要あり。
- 同じマシンで動いている他の kind クラスタが Docker VM（7.6GB）を圧迫し API が TLS timeout。検証中は docker stop で停止（復旧：`docker start $(cat /tmp/cndw-stopped-containers.txt)`）。
- 既定の kubectl context が EKS だった。スクリプトに `kind-cndw-demo` 以外では中止するガードを追加。

## スライドの修正一覧（YAML）
- スライド23：`k8s.pod.label.app` → `k8s.pod.label[app]`、`outbound` → `agent_outbound`（macro を追加）、パスは引用符付き。
- スライド23/21：Falco の dest 表示は `10.96.50.50:80`（スライドの 203.0.113.50 ではない）。
- Falco の出力の重大度表記は `Critical`。
- Talon：`grace_period_seconds: 5`、Helm 値に `falcosidekick.config.talon.address`。
- スライド18：Talon は1つ目のアラートで停止。Outbound は直後に発火するが、Pod は終了済みの場合がある。

## 追記：PAUSE 調整で分かったこと
- デモ2 の `PAUSE_ATTACK`（トークン読取→送信の間）は、Talon の grace（5秒）より短くする。長いと、送信前に Pod が消えて Unexpected Outbound が出ない。
- Talon が稼働していると、デモ1 の Pod も止められる。run-demo1.sh は Talon を 0 に、run-demo2.sh は 1 に戻す（VAP も demo1 では外す）。

## 録画（2026-11-18）
- demo1.mp4（109秒）、demo2.mp4（60秒）、各フリーズフレーム PNG を recordings/ に保存。1920×1080・30fps・音声なし（元は 1920×1044・60fps。上下に #0F2530 の帯を付加）。
- 仕様との差：文字は約12pt（20pt 未満）、背景は灰色（#0F2530 ではない）、ログインバナーが映る。時間はデモ2が約60秒（目標2分30秒）。撮り直しの時間がなく、このまま採用。
- デモ2の録画では VAP の `Warning:` が出なかった。VAP を作った直後の Pod 作成では、ポリシーが効く前（反映待ち）に通ってしまう競合。事前に VAP を適用しておくか、run-demo2.sh に待ちを入れる必要あり。

## OpenTelemetry の追加（2026-11-18、登壇後）
- **ローカルで確認済み（Python 3.10、opentelemetry-sdk 1.45.2）**：簡易の OTLP 受信サーバーに送り、(1) 1回の実行が1本のトレースになる、(2) `mcp.server.*` が、`mcp.*` の子になる（`traceparent` の引き継ぎ）、(3) 外へ送れないときは、`mcp.http.post` が ERROR で終わる、(4) トークンが、スパンに入らない、(5) `OTEL_EXPORTER_OTLP_ENDPOINT` を外すと、従来どおり動く。
- **kind では未検証**：`k8s/60-jaeger.yaml`（Jaeger v2.23.0）、Pod の環境変数、Jaeger への NetworkPolicy の許可、Falco の許可リスト、`app/Dockerfile` の `pip install`、Jaeger UI でのトレース表示。YAML の構文は、パースで確認済み。
- 特に、デモ2で、(a) NetworkPolicy が、Jaeger への送信を通すか、(b) Falco の `Agent Unexpected Outbound` が、Jaeger への接続で発火しないか（`10.96.60.60` を許可リストに入れた）、(c) Jaeger への接続が、Talon の猶予（5秒）に影響しないか、を確認してください。
- 登壇のスライド（27・28枚目）のスパン名は、`llm.call` など、概念図の名前です。キットの実際のスパン名は、`agent.decide`、`mcp.*` です。
