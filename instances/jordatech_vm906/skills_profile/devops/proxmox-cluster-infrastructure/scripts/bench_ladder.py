#!/usr/bin/env python3
"""Benchmark ladder for a vLLM endpoint: C1..C8 concurrency legs, streaming, TTFT + tok/s.

Proven 2026-09-24 on Flash-Next V3 (VM102, TP2xPP3). Usage:
    python3 bench_ladder.py <port> <max_conc> <out_prefix>
Writes incremental JSON to /opt/hf-fork/bench_results/<prefix>_ladder.json and prints
per-leg summaries: n_ok, p50/max TTFT, per-agent tok/s, aggregate tok/s.

Notes encoded from session experience:
- Streams SSE and counts BOTH delta.content and delta.reasoning / delta.reasoning_content
  (custom fleet forks use `delta.reasoning`; reasoning models can put everything there).
- Samples nvidia-smi VRAM/power + /proc/meminfo (Shmem!) between legs for OOM forensics.
- Prompt is synthetic repeated "x " tokens; replace leg defs for real-prompt runs.
"""
import json, sys, time, os, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
MAX_CONC = int(sys.argv[2]) if len(sys.argv) > 2 else 8
PREFIX = sys.argv[3] if len(sys.argv) > 3 else "stageD"
OUTDIR = "/opt/hf-fork/bench_results"
os.makedirs(OUTDIR, exist_ok=True)

URL = f"http://127.0.0.1:{PORT}/v1/chat/completions"
MODELS_URL = f"http://127.0.0.1:{PORT}/v1/models"

def get_model_name():
    with urllib.request.urlopen(MODELS_URL, timeout=10) as r:
        return json.load(r)["data"][0]["id"]

def one_request(model, prompt_tokens, max_tokens, timeout=600):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "x " * prompt_tokens}],
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(URL, data=payload, headers={"Content-Type": "application/json"})
    t0 = time.time()
    ttft = None
    toks = 0
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for line in r:
                line = line.decode().strip()
                if not line.startswith("data: "):
                    continue
                body = line[6:]
                if body == "[DONE]":
                    break
                try:
                    chunk = json.loads(body)
                except json.JSONDecodeError:
                    continue
                ch = chunk.get("choices", [{}])[0].get("delta", {})
                piece = ch.get("content") or ch.get("reasoning") or ch.get("reasoning_content") or ""
                if piece and ttft is None:
                    ttft = time.time() - t0
                if piece:
                    toks += 1
        return {"ok": True, "ttft": ttft, "tokens": toks, "wall": time.time() - t0}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "wall": time.time() - t0, "ttft": ttft, "tokens": toks}

def sample_host(res):
    try:
        import subprocess
        res["vram"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,power.draw", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as f:
            mi = {k: line.split()[1] for line in f
                  for k in [line.split(":")[0]] if k in ("MemTotal", "MemAvailable", "Shmem", "Cached")}
        res["meminfo"] = mi
    except Exception:
        pass

def leg(conc, prompt_tokens, gen_tokens):
    model = get_model_name()
    results = []
    with ThreadPoolExecutor(max_workers=conc) as ex:
        futs = [ex.submit(one_request, model, prompt_tokens, gen_tokens) for _ in range(conc)]
        for f in futs:
            results.append(f.result())
    ok = [r for r in results if r.get("ok")]
    ttfts = sorted([r["ttft"] for r in ok if r["ttft"]])
    toks = sum(r["tokens"] for r in ok)
    wall = max((r["wall"] for r in ok), default=0)
    per_agent = (sum(r["tokens"] / r["wall"] for r in ok) / len(ok)) if ok else 0
    return {
        "conc": conc, "prompt_tokens": prompt_tokens, "gen_tokens": gen_tokens,
        "n_ok": len(ok), "n_total": len(results),
        "p50_ttft": ttfts[len(ttfts)//2] if ttfts else None,
        "max_ttft": ttfts[-1] if ttfts else None,
        "total_tokens": toks, "wall": wall,
        "aggregate_tok_s": toks / wall if wall else 0,
        "per_agent_tok_s": per_agent,
        "errors": [r.get("error") for r in results if not r.get("ok")][:3],
    }

def main():
    legs = [(1, 8192, 256), (2, 8192, 256), (4, 8192, 256), (6, 8192, 256), (8, 8192, 256)]
    legs = [l for l in legs if l[0] <= MAX_CONC]
    all_results = []
    for (c, p, g) in legs:
        print(f"=== leg C{c} @{p}tok ===", flush=True)
        res = leg(c, p, g)
        sample_host(res)
        print(json.dumps({k: res[k] for k in ("conc", "n_ok", "n_total", "p50_ttft",
                                              "per_agent_tok_s", "aggregate_tok_s")}, indent=1), flush=True)
        all_results.append(res)
        out = f"{OUTDIR}/{PREFIX}_ladder.json"
        with open(out, "w") as f:
            json.dump(all_results, f, indent=1)
    print(f"\n=== SAVED {out} ===")

if __name__ == "__main__":
    main()
