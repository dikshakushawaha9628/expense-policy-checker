# Architecture / data flow

```mermaid
flowchart LR
    A[(Synthetic CSVs<br/>data/sample)] --> B[Ingest<br/>ingest.py]
    B --> C[(raw_expenses<br/>RAW - all TEXT, row_hash UNIQUE)]
    C --> D{Clean + validate}
    D -- ok --> E[(expenses<br/>CURATED - typed, CHECKs)]
    D -- bad --> F[(rejected_records<br/>+ reason)]
    FX[(fx_rates)] --> G
    E --> G[v_expenses_usd view]
    G --> H[Deterministic rules<br/>rules.py + v_duplicate_claims SQL]
    H --> I[(rule_violations<br/>AUTHORITATIVE)]
    G --> J[AI interface<br/>PolicyReviewer]
    J -- raw text --> K[Validate JSON schema<br/>+ confidence threshold]
    K --> L[(ai_observations<br/>ADVISORY)]
    I --> M[v_expense_review]
    L --> M
    M --> N[Console report + CSV]
```

```
  CSV --> raw_expenses --clean--> expenses --> v_expenses_usd --+--> RULES (pure Python + SQL) --> rule_violations --+
                  \--> rejected_records                        |                                                    +--> v_expense_review --> report
                                                               +--> AI (interface -> validate -> store) --> ai_observations --+
```

**The two result tables never merge.** `v_expense_review` shows them side by side
(`rule_status` vs `ai_label`), but no code path derives PASS/FAIL from AI output.

## Module map

| Module | Responsibility |
|---|---|
| `ingest.py` | read CSV, hash rows, load RAW, clean to CURATED, record rejects |
| `rules.py` / `policy.py` | pure deterministic rules + thresholds |
| `ai/base.py` | `PolicyReviewer` interface (the only thing the pipeline sees) |
| `ai/validation.py` | strict parsing of model output |
| `ai/heuristic.py`, `ai/ollama.py` | offline stand-in, local-LLM provider |
| `ai_review.py` | orchestration, failure handling, incremental runs |
| `report.py`, `cli.py`, `pipeline.py` | presentation + wiring |
