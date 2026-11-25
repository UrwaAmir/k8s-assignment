#!/usr/bin/env python3
"""Print N httperf wsesslog sessions, one POST /api/emi each, with random valid inputs."""
import random, sys

n = int(sys.argv[1])
for _ in range(n):
    P = random.randint(10000, 1000000)
    rate = random.randint(5, 20)
    months = random.randint(6, 60)
    print("/api/emi method=POST contents='{\"P\":%d,\"rate\":%d,\"n\":%d}'" % (P, rate, months))
    print()
