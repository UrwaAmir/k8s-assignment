#!/usr/bin/env python3
"""Makes the three graphs into results/. Needs: pip install pandas matplotlib
Run from the repo root:  python scripts/plot.py"""
import glob, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

R = "results"

# ---- Graph 1: avg response time vs request rate -------------------------------------------
s = pd.read_csv(f"{R}/summary.csv")
plt.figure(figsize=(7, 4.5))
for reps, g in s.groupby("replicas"):
    g = g.sort_values("rate")
    plt.plot(g["rate"], g["avg_response_ms"], marker="o", label=f"{reps} replica(s)")
plt.xlabel("Request rate (req/s)")
plt.ylabel("Average response time (ms)")
plt.title("Graph 1: Response time vs request rate")
plt.grid(alpha=.3); plt.legend(); plt.tight_layout()
plt.savefig(f"{R}/graph1_response_time.png", dpi=150); plt.close()

# ---- Graph 2: per-pod CPU during 100 req/s, 3 replicas ---------------------------------------
p = pd.read_csv(f"{R}/profile/r3_q100_pods.csv")
p = p[p["pod"].str.startswith("emi-web")].copy()
p["t"] = p["epoch"] - p["epoch"].min()
p["cpu_pct"] = p["cpu_millicores"].astype(float) / 100.0 * 100  # % of the 100m CPU request
plt.figure(figsize=(7, 4.5))
for pod, g in p.groupby("pod"):
    plt.plot(g["t"], g["cpu_pct"], marker="o", label=pod[-5:])
plt.axhline(250 / 100 * 100, ls="--", c="gray", lw=.8, label="limit (250m)")
plt.xlabel("Time (s)"); plt.ylabel("CPU utilization (% of 100m request)")
plt.title("Graph 2: Per-pod CPU, 100 req/s, 3 replicas")
plt.grid(alpha=.3); plt.legend(); plt.tight_layout()
plt.savefig(f"{R}/graph2_pod_cpu.png", dpi=150); plt.close()

# ---- Graph 3: autoscaling test on a shared time axis ------------------------------------------
A = f"{R}/autoscale"
ph = pd.read_csv(f"{A}/phases.csv")
hpa = pd.read_csv(f"{A}/profile_hpa.csv")
t0 = ph["start_epoch"].min()
hpa["t"] = (hpa["epoch"] - t0) / 60.0
steps_t, steps_r = [], []
for _, row in ph.iterrows():
    steps_t += [(row["start_epoch"] - t0) / 60.0, (row["end_epoch"] - t0) / 60.0]
    steps_r += [row["rate"], row["rate"]]
fig, ax = plt.subplots(3, 1, figsize=(8, 8), sharex=True)
ax[0].plot(steps_t, steps_r, c="tab:blue"); ax[0].set_ylabel("Request rate (req/s)")
ax[1].plot(hpa["t"], pd.to_numeric(hpa["cpu_percent"], errors="coerce"), marker="o", c="tab:red")
ax[1].axhline(50, ls="--", c="gray", lw=.8); ax[1].set_ylabel("Avg pod CPU (% of request)")
ax[2].step(hpa["t"], pd.to_numeric(hpa["current_replicas"], errors="coerce"), where="post", c="tab:green")
ax[2].set_ylabel("Web replicas"); ax[2].set_xlabel("Time (minutes)"); ax[2].set_yticks(range(0, 7))
for a in ax: a.grid(alpha=.3); a.set_xlim(left=0)
ax[0].set_title("Graph 3: Autoscaling test (10 min)")
plt.tight_layout(); plt.savefig(f"{R}/graph3_autoscaling.png", dpi=150); plt.close()
print("Saved graph1_response_time.png, graph2_pod_cpu.png, graph3_autoscaling.png in results/")
