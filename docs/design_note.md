# Design & Decision Note (1 page)

**Goal.** Turn messy expense CSVs into a structured dataset and check it against a
written policy, keeping *provable* rule failures strictly apart from *advisory* AI observations.

## Key decisions and why

1. **Three-layer SQLite model (raw → curated → results).** Raw rows are stored as TEXT
   exactly as received so a parsing bug can never destroy source data. Curated has real types and
   `CHECK` constraints, so bad data cannot get in even if Python validation is bypassed.
   SQLite keeps setup at zero (no server), yet gives me window functions and views.
2. **Rules are pure functions (+ one SQL window function for duplicates).** Same input → same
   verdict, trivially unit-testable, auditable against `docs/policy.md`. Cross-row logic (R005)
   lives in SQL (`v_duplicate_claims`) because that is what SQL is good at.
3. **Separation of deterministic vs AI is structural, not cosmetic.** Different tables
   (`rule_violations` vs `ai_observations`), different report sections, and no code path lets
   an AI label change PASS/FAIL. A test proves it (AI says "consistent", rules still FAIL).
4. **AI isolated behind `PolicyReviewer.review()`.** The pipeline only knows "send minimal
   fields, get text back". The model's reply is *untrusted*: it is parsed against a strict
   schema (label whitelist, confidence 0-1, rationale). Failures become explicit statuses
   (`error`, `invalid_response`, `low_confidence`) with `needs_human_review=1` — the run never
   crashes and never guesses. Employee/approver IDs are not sent to the model (data minimisation).
5. **Offline default provider.** `heuristic` mimics an LLM's JSON contract so the repo runs
   from a clean checkout with no download or key; `ollama` is a drop-in local model (temperature 0).
6. **Idempotent and incremental.** `row_hash UNIQUE` skips re-sent rows; rules are fully recomputed
   (cheap, always consistent with the current policy); AI only reviews expenses lacking an observation
   for (provider, prompt_version) and retries earlier errors.
7. **Fixed FX table** instead of a live API: reproducible results; rates are a documented assumption.

## Trade-offs & limitations

* Heuristic "AI" is keyword-based - it demonstrates the architecture, not model quality; a real LLM
  will be better on nuance and worse on determinism (hence confidence threshold + human review).
* Rules fully recompute each run: fine for 10^5 rows, wasteful at 10^7.
* A conflicting re-use of an `expense_id` is rejected, not versioned (no amendment workflow).
* Refunds (amount ≤ 0), per-diem logic, and per-person monthly caps are out of scope.

## Alternatives considered

* *Let the LLM decide pass/fail* - rejected: non-deterministic, un-auditable, can't be unit-tested.
* *pandas pipeline* - rejected: SQL constraints + views give stronger guarantees and the data is relational.
* *Postgres / dbt* - better at scale; overkill for a self-contained exercise.

## What I'd do for production

Postgres + incremental SQL models (dbt), rules versioned in config with effective dates, an
eval set to measure the LLM (precision on labelled "suspicious" items) before trusting it, prompt
and model version tracking per observation (already stored), a human-review queue UI, PII controls,
and orchestration/monitoring (Airflow, alerting on rejection-rate spikes).
