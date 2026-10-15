# Demo video script (target ~6:30)

| Time | Show | Say |
|---|---|---|
| 0:00 | README top | Problem: structured expense data + policy checker; rules vs AI kept separate. |
| 0:40 | `docs/architecture.md` (rendered mermaid) | Raw → curated → rules / AI. Two result tables, never merged. |
| 1:30 | `docs/policy.md` | 9 deterministic rules; "judgement areas" go to AI only. |
| 2:00 | `sql/schema.sql` | Raw all-TEXT, curated with CHECKs, `row_hash UNIQUE`, separate result tables. |
| 2:40 | Terminal: `make demo` | Walk the 3 report sections: load (note 7 rejects, 8 skipped re-sends), rule failures, AI observations. |
| 4:00 | `src/expense_checker/ai/base.py` + `validation.py` | One technical decision: AI behind an interface; output is untrusted & validated; swap to Ollama via env var. |
| 4:50 | Terminal: `make edge` | Edge cases: bad schema, bad value, rerun idempotency, garbage/offline AI - rules unaffected. |
| 5:50 | Terminal: `make test` | 34 tests incl. failure cases. |
| 6:10 | README "Limitations" | Heuristic stand-in; production: Postgres/dbt, eval set, review queue. |
