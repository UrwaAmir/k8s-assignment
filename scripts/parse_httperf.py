#!/usr/bin/env python3
"""Usage: parse_httperf.py REPLICAS RATE httperf_output.txt  -> prints one CSV row."""
import re, sys

reps, rate, path = sys.argv[1], sys.argv[2], sys.argv[3]
txt = open(path, errors="ignore").read()

def grab(pattern, default=""):
    m = re.search(pattern, txt)
    return m.group(1) if m else default

requests = grab(r"Total: connections \d+ requests (\d+)", "0")
replies = grab(r"Total: connections \d+ requests \d+ replies (\d+)", "0")
duration = grab(r"test-duration ([\d.]+) s")
avg_ms = grab(r"Reply time \[ms\]: response ([\d.]+)")
errors = grab(r"Errors: total (\d+)", "0")
ok = grab(r"Reply status: 1xx=\d+ 2xx=(\d+)", "0")
s5 = grab(r"Reply status: 1xx=\d+ 2xx=\d+ 3xx=\d+ 4xx=\d+ 5xx=(\d+)", "0")
print(",".join([reps, rate, requests, replies, duration, avg_ms, errors, ok, s5]))
