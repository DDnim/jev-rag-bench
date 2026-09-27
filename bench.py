"""BM25 top-10 over TypeSafe docs -> Jev judges each (query, passage) pair -> rerank + answerability gate."""
import json, math, os, re, time, pathlib, requests
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

P = json.load(open("corpus.json")); Q = json.load(open("queries.json"))
K = 10; MODEL = "jev-1.13.0"; PRICE = 0.042 / 1e6          # USD per input token (docs.typesafe.ai/models)
KEY = os.environ.get("TYPESAFE_API_KEY") or pathlib.Path("~/.config/typesafe/api_key").expanduser().read_text().strip()
CACHE = pathlib.Path("jev_cache.json"); cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

tok = lambda s: re.findall(r"[a-z0-9]+", s.lower())
STOP = set("a an the of to in on for is are do does i my me how what which can should when will with at by be it this that and or from about into all one".split())
docs = [[w for w in tok(p["title"] + " " + p["text"]) if w not in STOP] for p in P]
N = len(docs); avg = sum(map(len, docs)) / N; df = Counter(w for d in docs for w in set(d)); tf = [Counter(d) for d in docs]
def bm25(q, k1=1.5, b=0.75):
    qs = [w for w in tok(q) if w not in STOP]; out = []
    for i, d in enumerate(docs):
        s = sum(math.log(1 + (N - df[w] + .5) / (df[w] + .5)) * tf[i][w] * (k1 + 1) / (tf[i][w] + k1 * (1 - b + b * len(d) / avg)) for w in qs if w in tf[i])
        out.append((s, i))
    return sorted(out, reverse=True)[:K]

QUESTIONS = {
 "relevant": {"type": "noul", "instructions": "Does this passage address the subject of the query?"},
 "answers":  {"type": "noul", "instructions": "Does this passage state information that directly answers the query?"},
}
def jev(query, p):
    key = f"{MODEL}|{query}|{p['id']}"
    if key in cache: return cache[key]
    state = {"query": query, "passage": {"title": p["title"], "text": p["text"]}}
    for attempt in range(6):
        t0 = time.time()
        r = requests.post("https://api.typesafe.ai/v1/systemone", headers={"Authorization": f"Bearer {KEY}"},
                          json={"state": state, "model": MODEL, "questions": QUESTIONS}, timeout=60)
        if r.status_code in (429, 529): time.sleep(2 ** attempt); continue
        r.raise_for_status(); j = r.json(); break
    a = {"relevant": j["answers"]["relevant"]["noul"], "answers": j["answers"]["answers"]["noul"],
         "ms": round((time.time() - t0) * 1000), "tokens": j["usage"]["input_tokens"], "model": j.get("model")}
    cache[key] = a; return a

rows = []
for q in Q:
    hits = bm25(q["q"])
    with ThreadPoolExecutor(4) as ex: js = list(ex.map(lambda h: jev(q["q"], P[h[1]]), hits))
    CACHE.write_text(json.dumps(cache, indent=0))
    cands = [{"id": P[i]["id"], "bm25": round(s, 3), **a} for (s, i), a in zip(hits, js)]
    rows.append({**q, "cands": cands})
json.dump(rows, open("results.json", "w"), ensure_ascii=False, indent=1)
print("saved results.json", len(rows))
