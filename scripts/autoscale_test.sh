#!/bin/bash
# 10-minute HPA test: 2 min @10 req/s, 5 min @100 req/s, 3 min @10 req/s
cd "$(dirname "$0")/.."
OUT=results/autoscale
mkdir -p $OUT
ulimit -n 8192 2>/dev/null

kubectl delete hpa emi-web -n emi --ignore-not-found
kubectl scale deployment emi-web --replicas=1 -n emi
kubectl rollout status deployment/emi-web -n emi --timeout=180s
sleep 30
kubectl apply -f k8s/60-hpa.yaml
sleep 20

echo "phase,rate,planned_seconds,start_epoch,end_epoch" > $OUT/phases.csv
python3 scripts/profile.py $OUT/profile hpa &
PROF=$!
sleep 2

run_phase() {   # name rate seconds
  local N=$1 R=$2 S=$3
  local SESS=$((R*S))
  python3 scripts/gen_sessions.py $SESS > /tmp/sess_$N.txt
  local T0=$(date +%s)
  echo "phase $N: $R req/s for $S s (start $(date +%T))"
  httperf --server emi.local --port 80 --wsesslog=$SESS,0,/tmp/sess_$N.txt \
    --rate=$R --timeout=5 --hog \
    --add-header='Content-Type: application/json\n' > $OUT/httperf_$N.txt 2>&1
  local T1=$(date +%s)
  echo "$N,$R,$S,$T0,$T1" >> $OUT/phases.csv
}

run_phase 1_low 10 120
run_phase 2_high 100 300
run_phase 3_low 10 180

kill -TERM $PROF
wait $PROF 2>/dev/null
echo "AUTOSCALE TEST DONE $(date +%T)"
kubectl get hpa emi-web -n emi
