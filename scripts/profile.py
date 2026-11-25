#!/usr/bin/env python3
"""Profiler. Usage: profile.py OUT_PREFIX [hpa]
Writes OUT_PREFIX_host.csv  (host CPU %, every 1 s)
       OUT_PREFIX_pods.csv  (kubectl top pods, every 15 s)
       OUT_PREFIX_hpa.csv / _hpa_raw.txt  (only with 'hpa', every 15 s)
Stop it with kill (SIGTERM) or Ctrl+C."""
import csv, datetime, signal, subprocess, sys, threading, time

prefix = sys.argv[1]
with_hpa = len(sys.argv) > 2 and sys.argv[2] == "hpa"
NS = "emi"
stop = threading.Event()
signal.signal(signal.SIGTERM, lambda *a: stop.set())
signal.signal(signal.SIGINT, lambda *a: stop.set())

def stamp():
    now = time.time()
    return round(now, 1), datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")

def read_cpu():
    with open("/proc/stat") as f:
        vals = list(map(int, f.readline().split()[1:]))
    return vals[3] + vals[4], sum(vals)  # idle (idle+iowait), total

def host_loop():
    with open(prefix + "_host.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "timestamp", "cpu_percent"])
        idle0, tot0 = read_cpu()
        while not stop.wait(1.0):
            idle1, tot1 = read_cpu()
            dt = tot1 - tot0
            cpu = 100.0 * (1 - (idle1 - idle0) / dt) if dt > 0 else 0.0
            idle0, tot0 = idle1, tot1
            e, t = stamp()
            w.writerow([e, t, round(cpu, 1)])
            f.flush()

def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return ""

def pods_loop():
    with open(prefix + "_pods.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "timestamp", "pod", "cpu_millicores", "memory_mi"])
        while not stop.is_set():
            e, t = stamp()
            for line in run(["kubectl", "top", "pods", "-n", NS, "--no-headers"]).splitlines():
                p = line.split()
                if len(p) >= 3:
                    w.writerow([e, t, p[0], p[1].rstrip("m"), p[2].rstrip("Mi")])
            f.flush()
            stop.wait(15)

def hpa_loop():
    with open(prefix + "_hpa.csv", "w", newline="") as f, open(prefix + "_hpa_raw.txt", "w") as raw:
        w = csv.writer(f)
        w.writerow(["epoch", "timestamp", "current_replicas", "desired_replicas", "cpu_percent"])
        while not stop.is_set():
            e, t = stamp()
            out = run(["kubectl", "get", "hpa", "emi-web", "-n", NS, "-o",
                       "jsonpath={.status.currentReplicas} {.status.desiredReplicas} "
                       "{.status.currentMetrics[0].resource.current.averageUtilization}"]).split()
            out += [""] * (3 - len(out))
            w.writerow([e, t, out[0], out[1], out[2]])
            f.flush()
            raw.write("--- %s\n%s\n" % (t, run(["kubectl", "get", "hpa", "emi-web", "-n", NS])))
            raw.flush()
            stop.wait(15)

threads = [threading.Thread(target=host_loop), threading.Thread(target=pods_loop)]
if with_hpa:
    threads.append(threading.Thread(target=hpa_loop))
for th in threads:
    th.start()
while not stop.is_set():
    time.sleep(0.5)
for th in threads:
    th.join(timeout=25)
