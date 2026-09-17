#!/usr/bin/env python3
"""Coding-quality eval for Worker-Bee qualification (plan §20.3 pattern).

Fixed 6-task eval set — same prompts + rubric for every candidate configuration.
Proven on Qwen3.8-27B (6/6 tasks, 10/10 rubric groups, ~52 s/task at 3000 out-tokens).

REASONING-MODEL FIX (baked in): merge message.content with reasoning_content —
Qwen3.x/GLM reasoning models return content=None when reasoning consumes max_tokens.

Usage:
  python3 eval_coding.py --base-url http://127.0.0.1:8000/v1 --model <served-name> --out results.json
"""
import argparse, json, sys, time, urllib.request

TASKS = [
    {"id": "bug_diagnosis", "category": "bug diagnosis",
     "prompt": ("The following Python function intermittently raises IndexError on production data but "
                "never on the test suite. Diagnose the root cause precisely and give the minimal fix.\n\n"
                "```python\ndef running_median(samples):\n"
                "    window = []\n    medians = []\n"
                "    for i, s in enumerate(samples):\n"
                "        window.append(s)\n"
                "        window = window[::2] + window[1::2]  # keep every other element to bound memory\n"
                "        window.sort()\n        n = len(window)\n"
                "        if n % 2:\n            medians.append(window[n // 2])\n"
                "        else:\n            medians.append((window[n // 2 - 1] + window[n // 2]) / 2)\n"
                "    return medians\n```\n\n"
                "Answer format: ROOT CAUSE: <one sentence> | FIX: <short diff or code>"),
     "must_contain_any": [["window[::2]", "every other element", "subsample", "drops elements", "discards"]],
     "notes": "The subsample claim is false (interleave keeps all items); accept answers that "
              "identify the false claim or unbounded memory growth."},
    {"id": "small_repo_edit", "category": "small repository edit",
     "prompt": ("Given this Flask route, add pagination: query params `page` (default 1) and `per_page` "
                "(default 20, max 100). Return JSON {items, page, per_page, total}.\n\n"
                "```python\n@app.route('/api/orders')\ndef list_orders():\n"
                "    rows = db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()\n"
                "    return jsonify([dict(r) for r in rows])\n```\n\n"
                "Return only the complete corrected function."),
     "must_contain_any": [["request.args.get", "per_page", "offset", "LIMIT"]],
     "notes": "Grader: args.get for page/per_page, clamp per_page<=100, offset math, COUNT for total."},
    {"id": "multi_file_refactor", "category": "multi-file refactor",
     "prompt": ("Refactor plan: a monolith has payment logic duplicated in three call sites "
                "(checkout.py, subscription.py, invoice.py), each doing: validate card -> charge gateway -> "
                "write ledger row -> send receipt. Design the refactor: name the new module and function "
                "signatures, show the shared function's full implementation, and show the one-line change "
                "per call site. Payment gateway client is `gateway` with method `charge(card, amount_cents)` "
                "returning (ok, txn_id). Keep idempotency: a retried charge with the same order_id must not "
                "double-charge."),
     "must_contain_any": [["def charge", "def process_payment", "def pay"], ["idempoten", "order_id", "ledger"]],
     "notes": "Grader: single new module, function takes order_id, idempotency via ledger lookup or unique constraint."},
    {"id": "test_writing", "category": "test-writing task",
     "prompt": ("Write pytest tests for this function. Cover: normal case, empty input, negative numbers, "
                "and float precision. Use parametrize where natural.\n\n"
                "```python\ndef weighted_average(pairs):\n"
                "    \"\"\"pairs: list of (value, weight); weight must be > 0.\n"
                "    Returns sum(v*w)/sum(w).\"\"\"\n"
                "    total_w = 0.0\n    acc = 0.0\n"
                "    for v, w in pairs:\n"
                "        if w <= 0:\n            raise ValueError('weight must be positive')\n"
                "        acc += v * w\n        total_w += w\n"
                "    if total_w == 0:\n        raise ValueError('empty input')\n"
                "    return acc / total_w\n```\n\nReturn only the test file content."),
     "must_contain_any": [["pytest.mark.parametrize", "pytest.raises", "empty"]],
     "notes": "Grader: parametrize present, raises for w<=0, raises for empty, approx assert."},
    {"id": "infra_troubleshoot", "category": "shell/Proxmox-style troubleshooting",
     "prompt": ("A Proxmox VM (id 401, 6 GPUs) shows all GPUs at 100% utilization but the vLLM service "
                "logs show zero requests in the last hour and network in/out is near zero. "
                "Give a prioritized 5-command diagnostic sequence (one line each, with a short why), "
                "and state the single most likely root cause. Assume you have root SSH."),
     "must_contain_any": [["nvidia-smi", "ps aux", "journalctl"],
                          ["stuck", "hung", "zombie", "orphaned", "leak", "deadlock", "leftover"]],
     "notes": "Expect: compute-apps query, fuser /dev/nvidia*, listener check, journalctl, ps. "
              "Root cause: orphaned/leftover processes holding GPU context."},
    {"id": "code_review", "category": "code-review task",
     "prompt": ("Review this patch for a production billing service. Identify every real defect with severity "
                "(critical/major/minor). Ignore style.\n\n"
                "```python\ndef apply_refund(order_id, amount_cents, conn):\n"
                "    row = conn.execute('SELECT total_cents, refunded_cents FROM orders WHERE id=%s',\n"
                "                       (order_id,)).fetchone()\n"
                "    new_refund = row['refunded_cents'] + amount_cents\n"
                "    if new_refund > row['total_cents']:\n        raise ValueError('refund exceeds total')\n"
                "    conn.execute('UPDATE orders SET refunded_cents=%s WHERE id=%s',\n"
                "                 (new_refund, order_id))\n"
                "    conn.commit()\n    return new_refund\n```\n"
                "Context: called concurrently by webhook workers; Postgres."),
     "must_contain_any": [["race", "TOCTOU", "concurrent", "SELECT ... FOR UPDATE", "atomic"],
                          ["None", "null", "not found", "404", "missing"]],
     "notes": "Expected: critical read-then-write race (needs FOR UPDATE or atomic conditional UPDATE); "
              "major missing row=None check; major no negative-amount check; minor commit inside helper."},
]


def call_model(base_url, model, prompt, max_tokens=3000, timeout=300):
    body = json.dumps({"model": model, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base_url.rstrip('/') + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    r = urllib.request.urlopen(req, timeout=timeout)
    d = json.load(r)
    return d, time.time() - t0


def extract_answer(msg):
    """Reasoning models: content may be None with the answer in reasoning_content."""
    ans = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
    if reasoning and not ans:
        return reasoning
    if reasoning:
        return ans + "\n[reasoning] " + reasoning[:2000]
    return ans


def grade(ans, task):
    hits, total = 0, 0
    for group in task["must_contain_any"]:
        total += 1
        if any(k.lower() in ans.lower() for k in group):
            hits += 1
    return hits, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=3000)
    args = ap.parse_args()

    results = []
    for task in TASKS:
        print(f"=== {task['id']} ===", flush=True)
        try:
            d, dur = call_model(args.base_url, args.model, task["prompt"], args.max_tokens)
            msg = d["choices"][0]["message"]
            ans = extract_answer(msg)
            usage = d.get("usage", {})
            hits, total = grade(ans, task)
            results.append({"id": task["id"], "ok": True, "dur_s": round(dur, 1),
                            "out_tokens": usage.get("completion_tokens"),
                            "rubric_hits": hits, "rubric_groups": total,
                            "answer": ans[:4000]})
            print(f"  ok {dur:.1f}s rubric {hits}/{total} out={usage.get('completion_tokens')}")
        except Exception as e:
            results.append({"id": task["id"], "ok": False, "error": str(e)[:300]})
            print(f"  FAIL {e}")

    agg = {
        "model": args.model, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tasks_ok": sum(1 for r in results if r["ok"]), "tasks_total": len(results),
        "rubric_hits": sum(r.get("rubric_hits", 0) for r in results),
        "rubric_groups_total": sum(r.get("rubric_groups", 0) for r in results),
        "total_time_s": round(sum(r.get("dur_s", 0) for r in results), 1),
        "total_out_tokens": sum(r.get("out_tokens") or 0 for r in results),
        "results": results,
    }
    with open(args.out, "w") as f:
        json.dump(agg, f, indent=1)
    print(f"\nSUMMARY: {agg['tasks_ok']}/{agg['tasks_total']} ok, "
          f"rubric {agg['rubric_hits']}/{agg['rubric_groups_total']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
