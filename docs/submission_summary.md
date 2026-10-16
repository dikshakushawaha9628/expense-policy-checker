# Expense Policy Checker — Submission Summary

## Overview

This project ingests synthetic expense CSVs, validates and cleans them into a
SQLite dataset, and checks claims against a fictional written expense policy.
It separates deterministic policy violations from advisory text observations:
only deterministic rules produce an expense's PASS/FAIL status.

## Architecture and decisions

The Python pipeline loads source rows into a raw table, stores valid normalized
claims in a constrained curated table, and records invalid rows with rejection
reasons. SQLite views support USD conversion and duplicate detection.
Deterministic rule violations and advisory reviewer observations are stored
separately. Reviewer output is validated before storage and cannot change a
rule result. The default reviewer is an offline keyword-based heuristic; an
optional local Ollama provider is available.

SQLite and Python's standard library were chosen to keep setup reproducible
without a database server, API keys, or network access. Fixed sample exchange
rates make results repeatable. A fuller discussion of alternatives and
limitations is in [`design_note.md`](design_note.md).

## Run it on Windows

Requirements: Python 3.10 or later. From the project root in PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m expense_checker run --as-of 2026-10-15
python -m expense_checker edge-demo
python -m unittest discover -s tests -t . -v
```

The full run creates `output/expenses.db` and
`output/review_report.csv`. The default workflow needs no dependency
installation. See the [README](../README.md) for other setup options.

## Sample validation

The supplied synthetic batches produce 116 curated claims, 7 rejected rows,
and 8 exact re-sends skipped. The policy rules record 13 violations (103
expenses pass and 13 fail). The advisory reviewer reports observations
separately, including one low-confidence item requiring human review. The
edge-case demo covers a missing CSV schema, invalid amount, idempotent
re-ingestion, malformed reviewer output, and an unavailable reviewer. The test
suite contains 35 tests.

## Security and limitations

No passwords, API keys, or private data are required. The sample expense data
is synthetic. The heuristic reviewer is a demonstration, not a production-grade
language model. Other limitations include fixed exchange rates, no claim
amendment workflow, and no human-review interface.

## Submission links

* **Repository:** [expense-policy-checker](https://github.com/dikshakushawaha9628/expense-policy-checker)

