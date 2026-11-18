#!/usr/bin/env bash
# デモ2：同じ攻撃を、ガードレールあり（NetworkPolicy・Falco・Talon）で。別ペインで Falco のログを見ておく：
#   kubectl -n falco logs -f -l app.kubernetes.io/name=falco -c falco
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(kubectl config current-context)" = "kind-cndw-demo" ] || { echo "中止: context が kind-cndw-demo ではありません（共有クラスタ保護）" >&2; exit 1; }
kubectl -n agents delete pod coding-agent --ignore-not-found --wait=true
kubectl -n falco scale deploy/falco-talon --replicas=1 2>/dev/null || true
kubectl -n falco rollout status deploy/falco-talon --timeout=90s
kubectl apply -f k8s/30-networkpolicy.yaml
kubectl apply -f k8s/40-vap.yaml
kubectl apply -f k8s/50-agent-protected.yaml     # VAP が Warn を出す（違反の可視化）
kubectl -n agents wait --for=condition=Ready pod/coding-agent --timeout=60s || true
kubectl -n agents logs -f coding-agent -c agent || true
echo "--- Pod の状態 ---"
kubectl -n agents get pod coding-agent --show-labels || echo "Pod は Talon により終了済み"
