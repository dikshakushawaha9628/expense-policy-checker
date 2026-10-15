-- Reporting views. Re-created on every init so they always match the schema.

DROP VIEW IF EXISTS v_expenses_usd;
CREATE VIEW v_expenses_usd AS
SELECT e.*, ROUND(e.amount * f.rate_to_usd, 2) AS amount_usd
FROM expenses e
JOIN fx_rates f ON f.currency = e.currency;

-- Business duplicates (R005): the first claim wins, later copies are flagged.
DROP VIEW IF EXISTS v_duplicate_claims;
CREATE VIEW v_duplicate_claims AS
SELECT expense_id, first_expense_id
FROM (
    SELECT expense_id,
           FIRST_VALUE(expense_id) OVER w AS first_expense_id,
           ROW_NUMBER()            OVER w AS rn
    FROM expenses
    WINDOW w AS (
        PARTITION BY employee_id, expense_date, LOWER(merchant), amount, currency
        ORDER BY expense_id
    )
)
WHERE rn > 1;

-- One row per expense: deterministic status and AI advice side by side but NEVER merged.
DROP VIEW IF EXISTS v_expense_review;
CREATE VIEW v_expense_review AS
SELECT
    x.expense_id, x.employee_id, x.category, x.merchant, x.amount_usd, x.description,
    COUNT(v.rule_id)                                  AS rule_failure_count,
    CASE WHEN COUNT(v.rule_id) > 0 THEN 'FAIL' ELSE 'PASS' END AS rule_status,
    COALESCE(GROUP_CONCAT(v.rule_id, ','), '')        AS failed_rules,
    o.status                                          AS ai_status,
    o.label                                           AS ai_label,
    o.confidence                                      AS ai_confidence,
    o.rationale                                       AS ai_rationale,
    COALESCE(o.needs_human_review, 0)                 AS ai_needs_human_review
FROM v_expenses_usd x
LEFT JOIN rule_violations v ON v.expense_id = x.expense_id
LEFT JOIN ai_observations o ON o.obs_id = (
    SELECT MAX(obs_id) FROM ai_observations WHERE expense_id = x.expense_id)
GROUP BY x.expense_id;

DROP VIEW IF EXISTS v_violations_by_rule;
CREATE VIEW v_violations_by_rule AS
SELECT rule_id, severity, COUNT(*) AS violations, ROUND(SUM(x.amount_usd), 2) AS usd_exposed
FROM rule_violations v JOIN v_expenses_usd x USING (expense_id)
GROUP BY rule_id, severity
ORDER BY rule_id;

DROP VIEW IF EXISTS v_spend_by_category;
CREATE VIEW v_spend_by_category AS
SELECT category, COUNT(*) AS claims, ROUND(SUM(amount_usd), 2) AS total_usd
FROM v_expenses_usd GROUP BY category ORDER BY total_usd DESC;
