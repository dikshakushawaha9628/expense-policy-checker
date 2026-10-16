# Expense Policy Checker — demo video script (about 6 minutes)

Use this as speaking notes, not a word-for-word presentation. Keep the terminal
output visible and readable. Show only the README's opening summary; do not read
the README or slides from beginning to end.

## Before recording

1. Open this project folder in VS Code:
   `C:\Users\hkush\Downloads\expense-policy-checker\expense-policy-checker`
2. Open the integrated PowerShell terminal in that folder. If needed, activate
   the project's `.venv`.
3. Have these files ready in editor tabs: `README.md`, `docs/architecture.md`,
   `docs/policy.md`, `sql/schema.sql`,
   `src/expense_checker/ai/validation.py`, and the README limitations section.
4. Enlarge the terminal font and close unrelated windows or notifications.
   Do not show credentials or personal information.
5. Make a short test recording and check that the screen and microphone are
   clear. OBS Studio can record the VS Code window and microphone.

## 0:00–0:35 — Introduce the problem

**Show:** The title and opening summary of `README.md`.

**Say:**

> “Hi. This is an expense policy checker. It takes expense claims from CSV
> files, validates and stores them in SQLite, and checks them against a
> fictional expense policy. The main idea is to keep definite policy failures,
> such as exceeding a meal limit, separate from text-based observations, such
> as a vague description. The text observations can help a reviewer, but they
> never determine whether an expense passes or fails.”

**Do:** Point to the summary, then move on—do not read the rest of the README.

## 0:35–1:15 — Show the architecture

**Show:** `docs/architecture.md` and its diagram.

**Say:**

> “This diagram shows the data flow. CSV rows are first stored in a raw layer.
> Valid rows are cleaned and moved into a typed expenses table; invalid rows
> are retained with rejection reasons. Curated expenses then go through two
> independent paths: deterministic policy rules and advisory text review.
> Those results are stored separately and shown in separate report sections.
> That prevents an advisory observation from changing a policy decision.”

**Do:** Trace CSV → raw → curated or rejected → rules and text review → report.

## 1:15–1:50 — Briefly introduce the policy and data model

**Show:** The rules table in `docs/policy.md`, then the relevant tables in
`sql/schema.sql`.

**Say:**

> “The sample policy has nine deterministic rules. Examples include a 75-dollar
> meal limit, a 250-dollar lodging limit, receipt and approval requirements,
> duplicate detection, and checks for late or future-dated expenses. Amounts
> are compared in USD using fixed sample exchange rates. Other concerns, like
> a possible personal purchase, are observations for a person to review.”
>
> “In SQL, the raw table keeps source values as text, while the curated table
> uses typed fields and constraints. Rule violations and advisory observations
> have different tables.”

**Do:** Point out `raw_expenses`, `expenses`, `rule_violations`, and
`ai_observations`. Do not read every column.

## 1:50–3:15 — Run the sample and explain the output

**Show:** The VS Code PowerShell terminal. From the project root, run:

```powershell
$env:PYTHONPATH = "src"
python -m expense_checker --db output\demo-video-2026-10-17.db run --as-of 2026-10-15 --csv output\demo-video-report.csv
```

**Say while it runs:**

> “I’m running the full pipeline on the supplied synthetic CSV data. I’m using
> a separate database filename so this recording starts with a clean dataset.
> The processing date is fixed, which makes date-related results reproducible.
> The default reviewer works offline and does not need an API key or network
> connection.”

**Do:** Let the report finish. Scroll to show the load counts, rule summary,
advisory observations, and the final CSV path.

**Say:**

> “The first batch has 119 rows: 112 new valid claims and 7 rejected rows. The
> second batch has 12 rows: 4 new claims and 8 exact re-sends skipped. There
> are 116 curated expenses altogether.”
>
> “Here, the deterministic rules report 13 violations: 103 expenses pass and
> 13 fail. This section is authoritative for the sample policy. The advisory
> section is separate. It flags eight non-consistent descriptions on expenses
> that passed every rule, and one low-confidence observation needs human
> review. None of these observations changes the rule status. The report is
> also exported to the CSV path shown at the bottom.”

## 3:15–4:05 — Explain one technical decision

**Show:** `src/expense_checker/ai/validation.py`. Point to `parse_observation`,
the allowed-label check, confidence check, and rationale check.

**Say:**

> “One technical decision is to treat reviewer output as untrusted input.
> Before an observation is saved, this function checks that the response is
> valid JSON, that its label is supported, that its confidence is between zero
> and one, and that it contains a rationale. Invalid responses are recorded as
> failures and flagged for human review, instead of being allowed to affect
> deterministic results.”
>
> “The default reviewer is a keyword-based heuristic, not a general-purpose
> language model. The project also has an optional local Ollama provider
> behind the same interface.”

**Do:** Show the checks briefly; there is no need to read the function line by
line.

## 4:05–5:05 — Demonstrate an edge case

**Show:** Terminal. Run:

```powershell
python -m expense_checker edge-demo
```

**Say:**

> “This command runs several failure cases using a temporary in-memory
> database. First, it tries a CSV that is missing required columns. Ingestion
> stops before writing any expenses. Then a row with an invalid amount is
> rejected with a reason. When the same file is loaded again, all three rows
> are skipped as already seen.”
>
> “Finally, the demo simulates a reviewer returning non-JSON text and a
> reviewer that is unavailable. Both outcomes are recorded for human review.
> Notice that X1 still fails the meal-limit rule and X2 still passes. The
> reviewer errors did not change either deterministic decision.”

**Do:** Point to the schema error, rejected row, idempotency result, AI statuses,
and unchanged `X1`/`X2` results. Leave the relevant output visible.

## 5:05–5:35 — Show test validation

**Show:** Terminal. Run:

```powershell
python -m unittest discover -s tests -t . -v
```

**Say:**

> “The test suite checks the rule boundaries, input cleaning, rejected rows,
> duplicate handling, SQL checks, reviewer response validation, and the
> separation between advisory and deterministic results. The current suite
> contains 35 tests.”

**Do:** Show the final test summary. If any test fails, do not claim the suite
passed; show the failure and explain it accurately.

## 5:35–6:15 — Limitations and improvements

**Show:** The limitations section of `README.md` or `docs/design_note.md`.

**Say:**

> “The main limitation is that the default reviewer is keyword-based, so it
> demonstrates the review workflow but does not have the nuance or accuracy
> of a model evaluated for real expense decisions. The exchange rates are
> fixed sample data, and there is no review-queue interface or claim-amendment
> workflow. For a production version, I would evaluate the reviewer against
> labelled examples, add a human review queue, version policy changes, and
> select storage and processing tools based on expected scale. I kept this
> solution small and reproducible so it can run locally with Python and
> SQLite.”

**Do:** End on the limitations or the passing test summary. Stop the recording.

## After recording

1. Play the recording once. Check that narration is audible and code/output can
   be read.
2. Confirm the final video is 5–8 minutes long and contains no private data or
   credentials.
3. Upload it somewhere reviewers can access, such as an unlisted video or a
   share-enabled drive link.
4. Put the shareable video URL in the README submission checklist. Do not add
   a link that reviewers cannot open.
