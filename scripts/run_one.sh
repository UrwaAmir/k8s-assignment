#!/bin/bash
# Usage: ./scripts/run_one.sh REPLICAS RATE [DURATION_SECONDS]
cd "$(dirname "$0")/.."
REP=$1; RATE=$2; DUR=${3:-60}
TAG=r${REP}_q${RATE}
SESS=$((RATE*DUR))
mkdir -p results/raw results/profile

kubectl scale deployment emi-web --replicas=$REP -n emi
kubectl rollout status deployment/emi-web -n emi --timeout=180s
sleep 20   # let pods settle and old pods terminate

python3 scripts/gen_sessions.py $SESS > /tmp/sessions_$TAG.txt
python3 scripts/profile.py results/profile/$TAG &
PROF=$!
sleep 2

httperf --server emi.local --port 80 --wsesslog=$SESS,0,/tmp/sessions_$TAG.txt \
  --rate=$RATE --timeout=5 --hog \
  --add-header='Content-Type: application/json\n' > results/raw/$TAG.txt 2>&1

sleep 5
kill -TERM $PROF
wait $PROF 2>/dev/null
python3 scripts/parse_httperf.py $REP $RATE results/raw/$TAG.txt >> results/summary.csv
tail -1 results/summary.csv
