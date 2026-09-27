# jev-rag-bench

Small check of Jev (TypeSafe System One, `jev-1.13.0`) as the judging layer of a RAG pipeline, 2026-09-27.

- Corpus: TypeSafe's own docs (42 pages from `docs.typesafe.ai/llms.txt`, SDK/legal/demos excluded), one passage per `##` heading, code blocks stripped → 258 passages. `python3 build_corpus.py` rebuilds it (`raw/` and `corpus.json` are not committed).
- Queries (`queries.json`, written by hand in English): 20 answerable (gold passage ids), 10 near-miss (on-topic, the docs do not say: parameter count, GPU, enterprise price…), 6 out of scope.
- Retrieval: plain BM25, top 10.
- Jev: one request per (query, passage) pair, two Nouls — `relevant` and `answers` ("does this passage state information that directly answers the query?"). Rerank by `answers`; a query counts as answerable if any passage has `answers ≥ 0.5`.

Run: `python3 -m venv .venv && .venv/bin/pip install requests && .venv/bin/python bench.py && .venv/bin/python score.py` (key from `TYPESAFE_API_KEY` or `~/.config/typesafe/api_key`).

## Results (`summary.json`)

| | BM25 order | Jev rerank |
|---|---|---|
| gold passage at #1 (20 answerable) | 7 | 17 |
| gold in top 3 | 11 | 17 |

Gold was inside BM25's top 10 for 17 of 20 queries, so 17 is the ceiling for any reranker here.

Answerability gate (`answers ≥ 0.5` on any of the 10):

| type | passed the gate |
|---|---|
| answerable | 17/20 (the 3 misses are exactly the queries where BM25 did not retrieve the gold passage) |
| near-miss | 0/10 |
| out of scope | 0/6 |

33/36 correct. The best single BM25-score threshold, tuned on these same 36 queries (optimistic), gets 30/36.
Passages kept per answerable query: 2.0 of 10 on average.

Cost/speed: 360 requests, 554 input tokens per request on average, p50 223 ms / p90 303 ms per request (Tokyo, 4 in parallel), $0.0084 in total = $0.00023 per query at $0.042 / Mtok.

## Caveats

- 36 queries, one English corpus, queries and gold labels written by the author. After the first run, three gold sets were widened because Jev's top passage also answered the query (a14 `citation_check#5`, a17 `models#3`, a19 `confidence-routing#0` / `classification_using_confidence#5`); the change is in git history.
- BM25 is a weak first stage on purpose (like the official rerank cookbook). With a good embedding retriever the BM25→Jev gap would shrink.
- Jev writes no answer; generation still needs an LLM.
