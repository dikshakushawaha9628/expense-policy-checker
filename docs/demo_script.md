# Demo video walkthrough (about 7 minutes)

This is a read-aloud script with screen directions for a terminal-based project.
Replace bracketed directions with your own natural delivery. The default reviewer
is an offline keyword-based heuristic; do not describe it as a live AI model.

## Before you record

1. Open the project folder in VS Code:
   `C:\Users\hkush\Downloads\expense-policy-checker\expense-policy-checker`
2. Open a PowerShell terminal in that folder. Confirm the prompt ends in
   `expense-policy-checker\expense-policy-checker`. Activate `.venv` if needed.
3. Have `README.md`, `docs/architecture.md`, `docs/policy.md`,
   `docs/design_note.md`, and `sql/schema.sql` ready in editor tabs.
4. Make the VS Code terminal large enough to read. Close unrelated windows and
   avoid showing personal files, notifications, or credentials in the recording.
5. If recording with OBS, select the VS Code window, check that the preview is
   readable, select your microphone if narrating, and make a short test recording.
6. Use a new database filename below so the sample counts start from a clean DB.
   The command creates `output` if it does not already exist.

## Full script and recording cues

### 0:00–0:40 — Introduce the problem

**Show:** The title and opening summary in `README.md`.

**Say:**

> “Hi, this is my expense policy checker. The problem it addresses is turning
> expense CSVs into structured data and checking claims against a written
> policy. Some checks are deterministic—for example, whether a meal exceeds a
> fixed limit. Other observations depend on text, such as a vague description.
> The important design principle is that those two kinds of results are kept
> separate.”

**Do:** Briefly point to the README summary. Avoid reading the whole README.

### 0:40–1:25 — Explain the architecture

**Show:** `docs/architecture.md`; point out the Mermaid diagram and its flow.

**Say:**

> “The data flow starts with CSV files. Ingestion stores the source values in a
> raw table, then validates and cleans them into a typed expenses table. Rows
> that fail validation are recorded with reasons rather than silently dropped.
> The curated expenses then go to two separate review paths: deterministic
> policy rules and advisory text review. Each path writes to its own result
> table. The report can display them together for convenience, but advisory
> output never decides pass or fail.”

**Do:** Trace CSV → raw → curated/rejected → rules and reviewer → report on the
diagram.

### 1:25–2:05 — Show the policy and assumptions

**Show:** `docs/policy.md`.

**Say:**

> “This is a fictional policy created for the exercise. It defines nine
> machine-checkable rules, including meal and lodging limits, receipt
> requirements, duplicate claims, approval, late submission, future dates,
> prohibited categories, and self-approval. Amount limits are compared in USD
> using the project's fixed sample exchange rates. The policy also lists
> judgement areas—like vague descriptions or possible personal purchases—that
> are advisory observations, not rule failures.”

**Do:** Point to the deterministic-rules table and then the judgement-areas
list. Do not try to read every rule aloud.

### 2:05–2:45 — Show the SQL data model

**Show:** `sql/schema.sql`. Scroll from `raw_expenses` through `expenses`,
`rule_violations`, and `ai_observations`.

**Say:**

> “The database is SQLite, so no database server is needed. The raw table keeps
> incoming values as text. The curated table uses typed fields, constraints,
> and a foreign key to the currency reference data. A unique row hash makes
> exact re-sends idempotent. Rule violations and AI observations are stored in
> different tables. This makes the separation part of the data model, not just
> a label in the user interface.”

**Do:** Pause on the two separate results tables to make the distinction clear.

### 2:45–4:10 — Run the end-to-end sample

**Show:** The VS Code integrated PowerShell terminal. Run:

```powershell
$env:PYTHONPATH = "src"
python -m expense_checker --db output\demo-video-2026-10-16.db run --as-of 2026-10-15 --csv output\demo-video-report.csv
```

**Say while it runs:**

> “I’m running the full sample pipeline with a separate database file for this
> recording. The processing date is pinned so the future-date and late-submission
> checks are reproducible. The default reviewer runs locally and does not need
> an API key or network connection.”

**Do:** Once output appears, scroll so the three report sections are visible.
Point to:

* Data load: batch 1 reads 119 rows, with 112 new and 7 rejected; batch 2 reads
  12 rows, with 4 new and 8 exact re-sends skipped.
* Deterministic rules: 13 recorded rule violations and 103 PASS / 13 FAIL
  expenses.
* Advisory observations: 115 `ok` and 1 `low_confidence`; the latter is marked
  for human review. There are eight non-consistent observations shown for
  expenses that passed every rule.
* The final `CSV written to ...` line.

**Say:**

> “The report has separate sections for data loading, deterministic failures,
> and advisory observations. In this sample, 116 claims were curated. The
> policy rules report 13 failures. The text reviewer also flags descriptions
> that may need attention, including some claims that pass every deterministic
> rule. That does not change their rule status. The report is also exported as
> a CSV at the path shown here.”

### 4:10–4:50 — Explain the reviewer boundary

**Show:** `src/expense_checker/ai/base.py`, then `src/expense_checker/ai/validation.py`.

**Say:**

> “The reviewer is behind a small interface, so the pipeline does not depend
> on a particular provider. Its input contains the merchant, category,
> description, amount, and currency, but not employee or approver IDs. The
> output is treated as untrusted: it must be valid JSON with an allowed label,
> a confidence between zero and one, and a rationale. Invalid, failed, or
> low-confidence responses are recorded and sent for human review. The default
> provider is a keyword heuristic; an optional local Ollama provider is also
> available. This design demonstrates the boundary and failure handling, not
> production AI accuracy.”

**Do:** Point at `PolicyReviewer.review`, then briefly at the output validation.

### 4:50–5:50 — Demonstrate failure and edge cases

**Show:** Terminal. Run:

```powershell
python -m expense_checker edge-demo
```

**Say while it runs:**

> “Next I’m running the edge-case demonstration. It uses a temporary
> in-memory database, so it does not depend on or overwrite the sample database
> I just created.”

**Do:** Point out each edge-case heading and its outcome:

1. Schema missing required columns: `SchemaError` before any database write.
2. Bad amount: row is rejected with a reason.
3. Same file re-ingested: all three rows skipped as already seen.
4. Garbage model output and unavailable provider: recorded as
   `invalid_response` and `error`, both requiring human review.
5. Deterministic results remain `X1: FAIL R001` and `X2: PASS`.

**Say:**

> “The invalid file is stopped before it can write to the database. The bad
> amount is retained in the raw layer and appears in the rejection table. The
> second import is skipped as a duplicate. Finally, invalid and unavailable
> reviewer responses are recorded for human attention, and the rule decisions
> remain unchanged. This is the key failure-case guarantee.”

### 5:50–6:25 — Run the test suite

**Show:** Terminal. Run:

```powershell
python -m unittest discover -s tests -t . -v
```

**Say:**

> “The test suite covers the deterministic rule boundaries, cleaning and
> ingestion, invalid data, duplicates, SQL-based checks, reviewer response
> validation, and the guarantee that advisory review cannot alter rule
> results.”

**Do:** Let the final summary appear. The current suite contains 35 tests. Keep
the result visible long enough to read whether it passed.

### 6:25–7:05 — Limitations and close

**Show:** The limitations section in `README.md` or the final section of
`docs/design_note.md`.

**Say:**

> “The main limitation is that the default reviewer is a simple keyword
> heuristic, not a general language model, so its observations are only a
> demonstration and should not be treated as reliable decisions. The sample
> also uses fixed exchange rates, and this small project does not include an
> amendment workflow or a human review interface. For production, I would
> evaluate against labelled examples, add a review queue, version policy
> changes, and move to a database and processing design suited to the expected
> data volume. The project is intentionally small so it can be run and
> reproduced from a clean setup.”

**Do:** End with the README setup instructions or the passing test summary.
Stop recording.

## After recording

1. Play the video once and confirm that narration is audible and terminal text
   is legible.
2. Check that the recording is between 5 and 8 minutes and contains no personal
   data, credentials, or unrelated desktop notifications.
3. Upload the recording to a location reviewers can access, such as an
   unlisted video or a file link with viewer permission.
4. Add the shareable video URL to the README submission checklist. Do not
   include a private or inaccessible link.
