#!/bin/bash
# 15 experiments: replicas 1,2,3 x rates 10,25,50,100,200 (60 s each). Safe to re-run: finished runs are skipped.
cd "$(dirname "$0")/.."
mkdir -p results/raw results/profile
ulimit -n 8192 2>/dev/null
kubectl delete hpa emi-web -n emi --ignore-not-found
if [ ! -f results/summary.csv ]; then
  echo "replicas,rate,requests,replies,test_duration_s,avg_response_ms,errors,status_2xx,status_5xx" > results/summary.csv
fi
for REP in 1 2 3; do
  for RATE in 10 25 50 100 200; do
    if grep -q "^$REP,$RATE," results/summary.csv; then echo "skip r$REP q$RATE"; continue; fi
    echo "=== replicas=$REP rate=$RATE $(date +%T) ==="
    ./scripts/run_one.sh $REP $RATE
    sleep 30   # cool down
  done
done
echo "ALL DONE $(date +%T)"
