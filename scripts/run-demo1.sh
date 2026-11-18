#!/usr/bin/env bash
# デモ1：ガードレールなしで暴走させる。別ペインで collector のログを見ておく：
#   kubectl -n attacker-sim logs -f deploy/collector
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(kubectl config current-context)" = "kind-cndw-demo" ] || { echo "中止: context が kind-cndw-demo ではありません（共有クラスタ保護）" >&2; exit 1; }
kubectl -n agents delete pod coding-agent --ignore-not-found --wait=true
kubectl delete -f k8s/30-networkpolicy.yaml --ignore-not-found
kubectl delete -f k8s/40-vap.yaml --ignore-not-found
# デモ1は「ガードレールなし」。Falco Talon が入っていると Pod を止めてしまうので、止めておく
kubectl -n falco scale deploy/falco-talon --replicas=0 2>/dev/null || true
kubectl apply -f k8s/20-agent-unprotected.yaml
kubectl -n agents wait --for=condition=Ready pod/coding-agent --timeout=60s || true
kubectl -n agents logs -f coding-agent -c agent
