import json, statistics as st
R = json.load(open("results.json")); PRICE = 0.042 / 1e6; TH = 0.5
ans = [r for r in R if r["type"] == "answerable"]
def hit(r, key, k):
    order = sorted(r["cands"], key=key, reverse=True) if key else r["cands"]
    return any(c["id"] in r["gold"] for c in order[:k])
recall10 = sum(hit(r, None, 10) for r in ans)
out = {"n": {t: sum(r["type"] == t for r in R) for t in ("answerable", "near_miss", "out_of_scope")},
       "gold_in_bm25_top10": recall10}
for name, key in [("bm25", None), ("jev_answers", lambda c: (c["answers"], c["relevant"])), ("jev_relevant", lambda c: c["relevant"])]:
    out[name] = {f"hit@{k}": sum(hit(r, key, k) for r in ans) for k in (1, 3, 5)}
# answerability: query is answerable if any candidate's `answers` >= TH
gate = {}
for r in R:
    top = max(c["answers"] for c in r["cands"]); r["max_answers"] = round(top, 3)
    gate.setdefault(r["type"], []).append(top >= TH)
out["gate_pass"] = {t: f"{sum(v)}/{len(v)}" for t, v in gate.items()}
kept = [sum(c["answers"] >= TH for c in r["cands"]) for r in R]
out["kept_per_query_mean"] = round(st.mean(kept), 2)
out["kept_answerable_mean"] = round(st.mean(k for k, r in zip(kept, R) if r["type"] == "answerable"), 2)
# gold survives filter?
out["gold_kept"] = sum(any(c["id"] in r["gold"] and c["answers"] >= TH for c in r["cands"]) for r in ans)
# BM25 top-1 score as an answerability baseline (best threshold chosen on this data = optimistic)
b = [(r["cands"][0]["bm25"], r["type"] == "answerable") for r in R]
best = max(((sum((s >= t) == y for s, y in b), t) for t in sorted({s for s, _ in b})))
out["bm25_gate_best"] = {"correct": f"{best[0]}/{len(b)}", "threshold": best[1]}
jev_correct = sum((r["max_answers"] >= TH) == (r["type"] == "answerable") for r in R)
out["jev_gate_correct"] = f"{jev_correct}/{len(R)}"
ms = [c["ms"] for r in R for c in r["cands"]]; toks = [c["tokens"] for r in R for c in r["cands"]]
out["requests"] = len(ms); out["ms_p50"] = st.median(ms); out["ms_p90"] = sorted(ms)[int(.9 * len(ms))]
out["tokens_per_request_mean"] = round(st.mean(toks)); out["usd_total"] = round(sum(toks) * PRICE, 5)
out["usd_per_query"] = round(sum(toks) * PRICE / len(R), 6); out["model"] = R[0]["cands"][0]["model"]
json.dump(out, open("summary.json", "w"), indent=1); print(json.dumps(out, indent=1))
print("\nper query: type id max_answers | gold rank bm25 -> jev")
for r in R:
    g = ""
    if r["type"] == "answerable":
        rb = next((i+1 for i, c in enumerate(r["cands"]) if c["id"] in r["gold"]), None)
        o = sorted(r["cands"], key=lambda c: (c["answers"], c["relevant"]), reverse=True)
        rj = next((i+1 for i, c in enumerate(o) if c["id"] in r["gold"]), None); g = f"{rb} -> {rj}"
    print(r["type"][:6], r["id"], r["max_answers"], "|", g, "|", r["q"][:60])
