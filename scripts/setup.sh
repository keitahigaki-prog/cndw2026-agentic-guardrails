#!/usr/bin/env bash
# 一度だけ実行。kind クラスタ作成、イメージのビルドと読み込み、攻撃者側（シミュレーション）の起動。
# NetworkPolicy を enforce する CNI が必要。kind 既定の kindnet が対応していない版では、Calico か Cilium を入れる。
set -euo pipefail
cd "$(dirname "$0")/.."
kind get clusters | grep -qx cndw-demo || kind create cluster --name cndw-demo
docker build -t cndw-demo:0.1 app
kind load docker-image cndw-demo:0.1 --name cndw-demo
kubectl apply -f k8s/00-namespaces.yaml
kubectl apply -f k8s/10-collector.yaml
kubectl -n attacker-sim rollout status deploy/collector
kubectl apply -f k8s/60-jaeger.yaml                 # OpenTelemetry のトレースの受け皿（任意）
kubectl -n observability rollout status deploy/jaeger --timeout=120s
echo "OK: 次は Falco（README の手順）、または scripts/run-demo1.sh"
