#!/bin/bash
N=${1:-30}
for i in $(seq 1 $N); do
  P=$((100000 + RANDOM % 900000)); R=$((5 + RANDOM % 15)); M=$((12 + RANDOM % 48))
  curl -s -m 5 -X POST http://emi.local/api/emi -H 'Content-Type: application/json' \
    -d "{\"P\":$P,\"rate\":$R,\"n\":$M}" | grep -o '"servedBy":"[^"]*"' || echo FAILED
done | sort | uniq -c
