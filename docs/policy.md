# Acme Corp (fictional) Travel & Expense Policy — v1.0

Synthetic policy created for this exercise. Amounts are compared in **USD**
after conversion with the fixed rates in `data/reference/fx_rates.csv`.

## Deterministic rules (machine-checkable → PASS / FAIL)

| ID   | Name                  | Rule                                                                 | Severity |
|------|-----------------------|----------------------------------------------------------------------|----------|
| R001 | Meal limit            | A single **Meals** expense must not exceed **USD 75**.                | medium   |
| R002 | Lodging limit         | A single **Lodging** expense must not exceed **USD 250** per claim.   | medium   |
| R003 | Receipt required      | Any expense of **USD 25 or more** must have a receipt attached.       | high     |
| R004 | Prohibited category   | **Alcohol** and **Personal** expenses are never reimbursable.         | high     |
| R005 | Duplicate claim       | Same employee + date + merchant + amount + currency may be claimed once. Later copies fail. | high |
| R006 | Approval required     | Expenses **over USD 500** need an approver ID.                        | high     |
| R007 | Late submission       | Claims must be submitted within **60 days** of the expense date.      | medium   |
| R008 | Future-dated expense  | Expense date cannot be after the processing date.                     | high     |
| R009 | Self approval         | An employee cannot be their own approver.                             | high     |

## Judgement areas (NOT rules → AI observations only)

These need reading comprehension, not arithmetic. They are surfaced as
**advisory observations** and never turn a PASS into a FAIL:

* Description is too vague to audit ("misc", "stuff").
* Description suggests a personal / non-business purchase (gift, spa, streaming…).
* Description does not match the chosen category (taxi booked as Meals).
* Entertainment spend with no business purpose stated.

## Data-handling assumptions

* Refunds / credit notes (amount ≤ 0) are out of scope and are rejected at ingestion.
* A blank `receipt_attached` is treated as "no receipt".
* Only these currencies are supported: USD, EUR, GBP, INR.
