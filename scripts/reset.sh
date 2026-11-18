#!/usr/bin/env bash
cd "$(dirname "$0")/.."
[ "$(kubectl config current-context)" = "kind-cndw-demo" ] || { echo "中止: context が kind-cndw-demo ではありません（共有クラスタ保護）" >&2; exit 1; }
kubectl -n agents delete pod coding-agent --ignore-not-found
kubectl delete -f k8s/30-networkpolicy.yaml --ignore-not-found
kubectl delete -f k8s/40-vap.yaml --ignore-not-found
