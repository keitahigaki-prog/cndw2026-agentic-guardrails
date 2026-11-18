# 録画の手順（デモ1・デモ2）

目安：デモ1 = 約2分、デモ2 = 約2分。スライドは、録画を再生し、最後の画面で止める（フリーズフレーム）。

## 画面構成（3ペイン）

| ペイン | 内容 | コマンド |
|---|---|---|
| 左（大） | エージェントのログ | `scripts/run-demo1.sh` または `run-demo2.sh` |
| 右上 | 攻撃者側の受信 | `kubectl -n attacker-sim logs -f deploy/collector` |
| 右下 | Falco のアラート（デモ2のみ） | `kubectl -n falco logs -f -l app.kubernetes.io/name=falco -c falco` |

端末は、ダークテーマ、文字は大きめ（最後列から読める 20pt 以上）。録画前に、`scripts/reset.sh` で状態を戻す。

## デモ1：暴走（スライド16〜18）

1. （10秒）READMEを見せる：`kubectl -n agents get cm workspace -o jsonpath='{.data.README\.md}'`。人には見えない一文（HTMLコメント）が、あることを一言で。
2. （60秒）`scripts/run-demo1.sh` を実行。左ペインに、`read README.md` → `隠し指示を検出せず、タスクに取り込む` → `shell.exec cat …/token` → `http.post …` → `依存関係を更新しました ✔`。
3. （20秒）右上ペインに、`RECEIVED … eyJ…` が出る（トークンが、外へ出た）。
4. **停止画面：**スライド17「ユーザーに見えるのは、最後の1行だけ」に対応する、左ペインの最終画面。

## デモ2：停止（スライド24）

1. （10秒）VAP の警告を見せる：`run-demo2.sh` の `kubectl apply` の出力に、`Warning: …SA トークンをマウントしない` が出る。
2. （40秒）エージェントが動き出し、`shell.exec cat …/token` の時点で、右下ペインに `CRITICAL Agent Reads Service Account Token`。
3. （20秒）続いて `CRITICAL Agent Unexpected Outbound`。Talon が、Pod にラベルを付け、終了させる。
4. （20秒）右上ペインに、何も届いていないこと。`kubectl -n agents get pod` で、Pod が消えていること。
5. **停止画面：**スライド24「暴走は、2行目で止まる」に対応する、右下ペインの最終画面。

## 録画のコツ

- 実際にかかった時間を、スライドのノートの `[mm:ss]` に反映する。
- 失敗したら `scripts/reset.sh` からやり直し。Falco が発火しない場合は、README の「トラブルシュート」へ。
