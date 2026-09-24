#!/usr/bin/env python3
"""vLLM 0.28 `vllm bench serve` wrapper — Phase 19 §19.3 matrix runner (proven 2026-09-13).

Wraps the built-in vllm bench with the correct flags (the three traps that silently
fail every request otherwise), captures per-GPU NVML snapshots, and writes per-run
JSON + a manifest. Deploy to the vLLM guest (e.g. /root/bench_00112.py) and run with
the guest's vllm venv python.

Usage:
    bench_serve_wrapper.py --concurrency 10 --input-len 4096 --num-prompts 40 --tag c10_4k
    bench_serve_wrapper.py --matrix quick      # C1,4,8,10 x 4K,16K
    bench_serve_wrapper.py --matrix full       # C1..C20 x 4K,16K,25K,32K
    bench_serve_wrapper.py --soak              # C10 x 400 prompts @ 8K

CRITICAL: run bench legs SERIALLY. Two concurrent jobs saturate the engine, the LLM
Manager recovery engine sees a failed health probe and restarts vLLM mid-benchmark
(correct §K2 behavior — don't fight it, serialize instead).

Traps encoded below (all three silently produce 'all requests failed' with exit 0):
  1. --model <served-alias> makes the client do an HF hub lookup for the tokenizer →
     pass --tokenizer <repo-id> (cached locally).
  2. --endpoint takes the PATH only; host goes in --base-url.
  3. export HF_HOME=<cache dir> or tokenizer resolution may hit the network.
Always check completed > 0 after each run.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

VLLM_BIN = "/opt/vllm-venv/bin/vllm"
BACKEND = "http://127.0.0.1:8000"
MODEL = "qwen3.6-35b-a3b"                      # served alias
TOKENIZER = "QuantTrio/Qwen3.6-35B-A3B-AWQ"    # repo id for tokenizer resolution
RESULTS_DIR = "/root/v011-bench"


def gpu_snapshot():
    out = {}
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,power.draw,utilization.gpu",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
        gpus = []
        for line in r.stdout.strip().splitlines():
            i, mem, pw, util = [x.strip() for x in line.split(",")]
            gpus.append({"index": int(i), "mem_mib": int(mem),
                         "watts": float(pw), "util_pct": int(util)})
        out["gpus"] = gpus
        out["total_watts"] = sum(g["watts"] for g in gpus)
        out["total_mem_mib"] = sum(g["mem_mib"] for g in gpus)
    except Exception as e:
        out["error"] = str(e)[:120]
    return out


def run_serve_bench(conc, input_len, output_len, num_prompts, tag):
    cmd = [VLLM_BIN, "bench", "serve",
           "--backend", "openai-chat",
           "--base-url", BACKEND,                    # host here...
           "--endpoint", "/v1/chat/completions",     # ...path only here
           "--model", MODEL,
           "--tokenizer", TOKENIZER,                 # NOT the served alias
           "--num-prompts", str(num_prompts),
           "--request-rate", str(conc),
           "--random-input-len", str(input_len),
           "--random-output-len", str(output_len),
           "--percentile-metrics", "ttft,tpot,itl,e2el",
           "--save-result", "--result-dir", RESULTS_DIR,
           "--result-filename", f"{tag}.json"]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    dur = time.time() - t0
    out = {"tag": tag, "concurrency": conc, "input_len": input_len,
           "output_len": output_len, "num_prompts": num_prompts,
           "duration_s": round(dur, 1), "rc": r.returncode,
           "stdout_tail": r.stdout[-2000:], "stderr_tail": r.stderr[-800:]}
    resfile = os.path.join(RESULTS_DIR, f"{tag}.json")
    if os.path.exists(resfile):
        try:
            with open(resfile) as f:
                out["result"] = json.load(f)
        except Exception:
            pass
    out["gpu_after"] = gpu_snapshot()
    return out


def summarize(o):
    res = o.get("result") or {}
    keys = ["request_throughput", "output_throughput", "total_token_throughput",
            "mean_ttft_ms", "median_ttft_ms", "p99_ttft_ms",
            "mean_itl_ms", "p99_itl_ms", "mean_e2el_ms", "p99_e2el_ms", "completed"]
    line = {k: res.get(k) for k in keys if k in res}
    print(json.dumps({"tag": o["tag"], "dur_s": o["duration_s"], **line}, default=str), flush=True)
    if not res.get("completed"):
        print(f"WARNING: {o['tag']} completed 0 requests — check stdout_tail in manifest", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int)
    ap.add_argument("--input-len", type=int, default=4096)
    ap.add_argument("--output-len", type=int, default=256)
    ap.add_argument("--num-prompts", type=int, default=None)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--matrix", choices=["quick", "full"])
    ap.add_argument("--soak", action="store_true")
    args = ap.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    jobs = []
    if args.matrix == "quick":
        for c in (1, 4, 8, 10):
            for il in (4096, 16384):
                jobs.append((c, il, 256, max(c * 4, 32), f"m{c}_{il//1024}k"))
    elif args.matrix == "full":
        for c in (1, 4, 8, 10, 12, 16, 20):
            for il in (4096, 16384, 25600, 32768):
                jobs.append((c, il, 256, max(c * 4, 32), f"f{c}_{il//1024}k"))
    elif args.soak:
        jobs.append((10, 8192, 256, 400, "soak_c10_8k"))
    elif args.concurrency:
        n = args.num_prompts or max(args.concurrency * 4, 32)
        tag = args.tag or f"c{args.concurrency}_{args.input_len//1024}k"
        jobs.append((args.concurrency, args.input_len, args.output_len, n, tag))
    else:
        print("nothing to do")
        return 1

    manifest = []
    for c, il, ol, np_, tag in jobs:
        print(f"=== RUN {tag}: C{c} in={il} out={ol} prompts={np_} ===", flush=True)
        try:
            o = run_serve_bench(c, il, ol, np_, tag)
        except subprocess.TimeoutExpired:
            o = {"tag": tag, "error": "timeout 3600s"}
        manifest.append(o)
        summarize(o)
        time.sleep(5)   # cooldown between legs — health probes must pass

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mf_path = os.path.join(RESULTS_DIR, f"manifest_{stamp}.json")
    with open(mf_path, "w") as f:
        json.dump({"started": stamp, "runs": manifest}, f, indent=1, default=str)
    print(f"manifest: {mf_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
