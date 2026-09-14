#!/usr/bin/env python3
"""Phase 8 benchmark engine for a vLLM fleet — LLM Manager plan §18.

Presets per plan §18.1/§18.2. Real TTFT via streaming first-chunk timing.
Usage:
    bench_engine.py C10 [--deployment http://10.0.20.161:8000]
Presets: C1 C10 C16 C20 C32 C48 (4096-token pad input, 256 out, thinking-off)
Machine-readable summary on the line starting RESULT_JSON=.
Store results in benchmark_runs (see SKILL.md §Benchmarking) from that line.
"""
import json, time, threading, urllib.request, statistics, sys

RESULTS = []
ERRORS = []

def run_one(base_url, model, pad, out_len):
    t0 = time.time()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": pad + " Summarize the key tradeoffs in one short paragraph."}],
        "temperature": 0,
        "max_tokens": out_len,
        "stream": True,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(base_url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    ttft = None
    out_tokens = 0
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            for line in r:
                if line.startswith(b"data: ") and b"[DONE]" not in line:
                    if ttft is None:
                        ttft = time.time() - t0
                    try:
                        chunk = json.loads(line[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if delta.get("content"):
                            out_tokens += 1
                    except Exception:
                        pass
        lat = time.time() - t0
        RESULTS.append((ttft, lat, out_tokens))
    except Exception as e:
        ERRORS.append(repr(e)[:150])

def run_bench(preset):
    conc_map = {"C1": 1, "C10": 10, "C16": 16, "C20": 20, "C32": 32, "C48": 48}
    conc = conc_map[preset]
    n = 20 if conc == 1 else 100
    return conc, n, 256

def main():
    args = sys.argv[1:]
    preset = args[0] if args else "C10"
    deploy = "http://10.0.20.161:8000"
    model = "qwen3.6-35b-a3b"
    if "--deployment" in args:
        deploy = args[args.index("--deployment") + 1]
    if "--model" in args:
        model = args[args.index("--model") + 1]
    pad = ("The theoretical and practical performance characteristics of mixture-of-experts transformer "
           "models deployed on tensor and expert parallel GPU topologies depend heavily on interconnect "
           "bandwidth, arithmetic intensity, and memory hierarchy. " * 14)
    conc, n, out_len = run_bench(preset)
    base = deploy.rstrip("/") + "/v1/chat/completions"
    print(f"preset={preset} conc={conc} n={n} out={out_len} target={deploy}")
    t_start = time.time()
    workers = []
    for i in range(n):
        while sum(1 for w in workers if w.is_alive()) >= conc:
            time.sleep(0.02)
        w = threading.Thread(target=run_one, args=(base, model, pad, out_len))
        w.start(); workers.append(w)
    for w in workers:
        w.join()
    dt = time.time() - t_start
    ok = RESULTS
    ttfts = [r[0] for r in ok if r[0]]
    lats = [r[1] for r in ok]
    outs = [r[2] for r in ok]
    print("=== BENCH COMPLETE ===")
    print(f"time: {dt:.1f}s ok: {len(ok)}/{n} failed: {len(ERRORS)}")
    print(f"output tok/s: {sum(outs)/dt:.1f}")
    if ttfts:
        print(f"TTFT mean/p50/p95: {statistics.mean(ttfts):.2f}s / "
              f"{statistics.quantiles(ttfts, n=20)[18]:.2f}s / {max(ttfts):.2f}s")
    if lats:
        print(f"latency avg: {statistics.mean(lats):.2f}s")
    print("RESULT_JSON=" + json.dumps({
        "preset": preset, "concurrency": conc, "requests": n, "ok": len(ok), "failed": len(ERRORS),
        "duration_s": round(dt, 1), "output_tok_s": round(sum(outs)/dt, 2),
        "ttft_avg_s": round(statistics.mean(ttfts), 3) if ttfts else None,
        "ttft_max_s": round(max(ttfts), 3) if ttfts else None,
        "latency_avg_s": round(statistics.mean(lats), 2) if lats else None,
        "target": deploy, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }))
    if ERRORS[:3]:
        print("errors:", ERRORS[:3])

if __name__ == "__main__":
    main()
