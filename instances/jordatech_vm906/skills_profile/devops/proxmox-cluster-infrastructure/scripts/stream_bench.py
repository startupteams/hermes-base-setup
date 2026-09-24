#!/usr/bin/env python3
"""Streaming OpenAI-compatible benchmark: TTFT + output tok/s at concurrency 1.

Handles the fleet's custom vLLM fork quirk (delta.reasoning instead of
delta.reasoning_content). Usage:
    python3 stream_bench.py http://10.0.20.161:8000/v1/chat/completions qwen3.8-27b [n_reqs]
Exit code 0 = at least one request succeeded.
"""
import json, sys, time, urllib.request

def stream_bench(url, model, prompt_tokens_target=1000, output=128, reqs=3, timeout=180):
    prompt = ("Explain the architecture of a distributed key-value store in detail. " * 45)
    lat, ttfts, tps = [], [], []
    for i in range(reqs):
        body = json.dumps({"model": model, "stream": True, "max_tokens": output,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        t0 = time.time(); ttft = None; ntok = 0
        try:
            r = urllib.request.urlopen(req, timeout=timeout)
            for line in r:
                line = line.decode().strip()
                if not line.startswith("data:") or line == "data: [DONE]":
                    continue
                try:
                    d = json.loads(line[5:])
                    delta = d["choices"][0].get("delta", {})
                    content = delta.get("content") or delta.get("reasoning") or delta.get("reasoning_content")
                    if content and ttft is None:
                        ttft = time.time() - t0
                    if content:
                        ntok += 1
                except Exception:
                    pass
            total = time.time() - t0
            if ttft is not None:
                ttfts.append(ttft)
            lat.append(total)
            if ntok > 0:
                tps.append(ntok / max(total - (ttft or 0), 1e-6))
        except Exception as e:
            lat.append(None)
            print(f"  req{i} ERROR: {str(e)[:120]}", file=sys.stderr)
    ok_lat = [x for x in lat if x]
    ok_ttft = [x for x in ttfts if x]
    return {
        "n_ok": len(ok_lat),
        "latency_s": ok_lat,
        "ttft_s_mean": round(sum(ok_ttft) / len(ok_ttft), 2) if ok_ttft else None,
        "tok_s_mean": round(sum(tps) / len(tps), 1) if tps else None,
    }

if __name__ == "__main__":
    url = sys.argv[1]; model = sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    print(json.dumps(stream_bench(url, model, reqs=n), indent=1))
